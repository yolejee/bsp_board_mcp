# Android Suspend 软件层分析参考

> 本文件专注于 Android 系统的 suspend 分析方法论，包括分层架构、睡眠占比判断、Partial Wakelock 排查等。

---

## 1. Android Suspend 分层架构

```
┌─────────────────────────────────────────────────┐
│  Application Layer (APP)                         │
│    └─ 各 APP 可通过 PowerManager 获取 wakelock   │
├─────────────────────────────────────────────────┤
│  Framework Layer                                 │
│    └─ PowerManagerService                        │
│       ├─ 管理 Partial Wakelock                   │
│       ├─ 判断所有锁释放后 → 触发 kernel suspend   │
│       └─ AlarmManager / JobScheduler 等定时服务   │
├─────────────────────────────────────────────────┤
│  Kernel Layer                                    │
│    ├─ wakeup_sources 框架                        │
│    ├─ suspend flow (freeze → device → enter)     │
│    └─ 各驱动的 suspend/resume callback            │
├─────────────────────────────────────────────────┤
│  Firmware Layer (ATF/TEE)                        │
│    └─ 平台 firmware 接管最终休眠操作              │
└─────────────────────────────────────────────────┘
```

### 关键推理规则

- **能触发 suspend entry = 上层（Framework）已经没人持锁**
  - 因为 PowerManagerService 只有在所有 partial wakelock 都释放后才会发起 kernel suspend
- 如果 active 时长很长（如 10s），**不要在底层找原因**
  - resume 通常只需 20-100ms
  - resume 完成后系统回到上层
  - 很久没有下一次 suspend entry → **上层有人重新获取了 wakelock**

---

## 2. 报告优先级门槛

**在报告问题之前，必须先检查睡眠占比。** 这是最重要的判断前提。

| 睡眠占比 | 处理方式 |
|---------|---------|
| > 80% | **禁止报告** Freezing Task 失败 / Device Suspend 失败为 P0 问题，这是正常背景噪声 |
| 50-80% | 可选报告，标注为**低优先级**（P1） |
| < 50% | **应该报告为 P0**，这是真正阻塞休眠的问题 |

### 示例判断

| 场景 | 睡眠占比 | Freezing Task 失败 | 正确处理 |
|------|---------|-------------------|---------|
| 案例 1 | 98.7% | 13 次 | ❌ 不报告（系统休眠正常） |
| 案例 2 | 81.9% | 3 次 | ❌ 不报告（仍属正常范围） |
| 案例 3 | 45% | 5 次 | ✅ 报告为 P0（系统无法正常休眠） |
| 案例 4 | 10% | 20 次 | ✅ 报告为 P0（严重问题） |

---

## 3. IRQ 唤醒优先级规则

`pm_system_irq_wakeup` 是 **oneshot 事件**：IRQ 触发 → 系统醒一下 → 快速再入睡。不会导致底电「持续抬升」。

| 睡眠占比 | pm_system_irq_wakeup | 处理方式 |
|---------|----------------------|---------|
| ≥ 80% | 任意次数 | **不报告为问题**，oneshot 唤醒属正常现象 |
| 50-80% | 频繁 | 可列为 P1 低优先级参考 |
| < 50% | 任意次数 | P0，系统无法正常休眠 |

---

## 4. Pending Wakeup Sources 的正确理解

- suspend/resume 过程中 kernel **一定会检测** pending wakeup sources，这是正常流程
- resume 时日志出现 `Pending Wakeup Sources: [timerfd]` **不代表这是持续问题**
- 只有当 wakeup source **持续持锁、阻止多次 suspend entry** 时，才是真正的问题

```
❌ 错误: 看到 resume 时有 pending wakeup source → 报告为问题根因
✅ 正确: 确认该 wakeup source 是否在整个 active 期间持续持锁
```

---

## 5. Active 时长分析（强制流程）

当分析某次唤醒的 active 时长异常（>1s）时，**必须严格按以下步骤**：

### Step 1: 确认 resume 完成时间

从日志中找到 resume callback 完成的最后一条（如 `Restarting tasks`、`OOM killer enabled`、device resume 完成等），确认 resume 耗时。

> ⚠️ `OOM killer enabled` 只是 resume 后 kernel 恢复的某个步骤，**不是 resume 完成的标志**

### Step 2: 确认下一次 suspend entry 时间

从日志中找到下一次 `Suspend entry` 的时间戳。

### Step 3: 计算真正的 active 时长

```
active = Step 2 时间 - Step 1 时间（扣除 resume 本身的几十 ms）
```

### Step 4: 判断问题在哪一层

这是**最关键的一步**。

```
if resume 本身耗时 >500ms:
    → 底层问题：driver callback 卡住，排查具体哪个 driver

if resume 正常（<100ms），但 active 很长（如 10s）:
    → 100% 是上层持锁问题

    ⛔ 禁止把 rcs_irq、timerfd、充电模块 I2C、pending wakeup source 列为根因
    ⛔ 禁止说 "resume 流程走完需要 10s"（resume 只要几十 ms）
    ⛔ 禁止说 "rcs_irq 业务处理需要 10s"（IRQ handler 是 us~ms 级）
    ⛔ 禁止说 "timerfd 积压需要逐个处理所以 10s"（timerfd 处理是 ms 级）

    ✅ 必须结论: resume 后上层某组件获取了 partial wakelock，持锁约 Xs 后释放
    ✅ 必须给出上层持锁的排查方向
```

### Step 5: 输出排查建议

根据 Step 4 结论给出对应排查方向（见下方排查方法）。

---

## 6. 上层持锁（Partial Wakelock）排查方法

当 active 时长异常长（>1s）且底层 resume 正常完成时，问题在上层。

> ⚠️ 上层持锁是瞬态事件（持锁几秒后释放，系统重新 suspend）。`dumpsys power` 只能看**当前瞬间**的持锁状态，等手动敲命令时锁早已释放，**抓不到**。必须用**事后分析**或**提前录制**。

### 方法 1（推荐）: bugreport 事后分析

```bash
# 复现问题后立刻抓 bugreport
adb bugreport > bugreport.zip
# 解压后搜索 "All partial wake locks." → 按 total_time 排序
# 搜索 "Wake lock" + 时间戳 → 追踪具体时间点谁 acquire/release 了锁
```

### 方法 2: wakeup_sources 累计统计

```bash
adb shell cat /sys/kernel/debug/wakeup_sources > ws_before.log
# 复现问题
adb shell cat /sys/kernel/debug/wakeup_sources > ws_after.log
# 对比两次 dump 的差值，找出 total_time 增长最多的 source
```

### 方法 3（最精确）: perfetto 提前录制

```bash
# 在复现前开始录制，复现后停止，回放时间线
# 可以精确看到 PowerManagerService 的 wakelock acquire/release 时序
# 定位哪个 APP/Service 在 resume 后获取了 wakelock、持有多久
```

### 常见上层持锁来源

| 来源 | 说明 |
|------|------|
| `alarm` / AlarmManager | 定时任务触发 |
| `job` / JobScheduler | 后台任务调度 |
| `sync` | 账户同步 |
| `connectivity` / `wifi` | 网络状态变化处理 |
| `audio` / `media` | 音频/媒体播放 |
| 第三方 APP | 需结合包名判断 |

---

## 7. alarmtimer 持锁专项排查

### 问题特征

```
alarmtimer alarmtimer.1.auto: PM: dpm_run_callback(): platform_pm_suspend returns -16
Pending Wakeup Sources: alarmtimer.1.auto
```

- Device Suspend 失败率高，错误码 -16 (EBUSY)
- 原生 kernel log **无法定位是哪个 APP 设置了该 alarm**

### 推荐方案: MTK Alarm 定位 Patch

- **fw_alarm.diff**：上层 alarm framework 定位，可看到哪个 APP 通过 AlarmManager 设置了 alarm（包名、触发间隔、alarm 类型）
- **kernel_alarm.diff**：底层 kernel alarmtimer 定位，可看到 alarmtimer 的具体设定 user 和回调函数

### 排查建议模板

> 原生 kernel log 无法直接定位 alarm 来源，建议 apply MTK 提供的 alarm 定位 patch（fw_alarm.diff + kernel_alarm.diff）后复现抓 LOG，可直接看到是哪个 APP/Service 设置了高频 alarm。

---

## 8. 底电持续抬升的正确排查逻辑

当客户反馈「底电持续抬升」时：

```
检查清单:
1. 睡眠占比 ≥ 80%？ → AP 侧休眠正常
2. 26M 关闭率 ≥ 95%？ → 时钟管理正常
3. Vcore ≥ 95%？ → 核心电压管理正常

如果以上均正常 → 不是 AP 侧导致持续抬升
  → 正确方向: 结合硬件功耗分解（PMIC 分路测量）定位具体硬件域

常见错误:
❌ "26M 关闭率低 → 导致 suspend 失败"（两个独立问题）
❌ "wakelock 阻塞导致 26M 无法关闭"（wakelock 影响 suspend flow）
❌ "rcs_irq 唤醒 13 次 → P0 底电抬升根因"（oneshot ≠ 持续抬升）
```

---

## 9. 排查命令汇总

```bash
# === 上层锁（Android Framework 层）===
adb shell dumpsys power | grep "PARTIAL_WAKE_LOCK"

# === 底层锁（Kernel 层）===
adb shell cat /sys/kernel/debug/wakeup_sources > wakeup_sources.log
# 用 excel 打开，按 total_time 排序

# === bugreport 中搜索 ===
# 底层锁: 搜索 "All kernel wake locks."
# 上层锁: 搜索 "All partial wake locks."

# === suspend 统计 ===
adb shell cat /sys/kernel/debug/suspend_stats
```

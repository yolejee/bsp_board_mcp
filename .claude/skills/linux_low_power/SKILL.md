---
name: linux_low_power
description: "通用 Linux 低功耗与休眠唤醒调试技能，不限于任何特定 SoC 平台。覆盖 Linux 系统休眠状态（S2Idle/Standby/S2RAM/Hibernate）、Suspend/Resume 全流程分析、wakeup sources 唤醒源排查、Runtime PM 设备级电源管理、功耗测量与优化、Power Domain/PD 管理、驱动 suspend/resume 回调调试。触发关键词：低功耗、low power、休眠、suspend、resume、待机、standby、睡眠、sleep、唤醒、wakeup、wakeup source、wakelock、功耗、power consumption、Runtime PM、autosuspend、电源域、power domain、pm_genpd、hibernate、冬眠、STR、S2RAM、S2Idle、freeze、底电流、漏电、静态功耗、动态功耗、regulator-state-mem、sleep-mode-config、pm_test、suspend_stats、no_console_suspend、initcall_debug、pm_debug_messages、wakeup_count。当用户描述 Linux 系统无法休眠、休眠后无法唤醒、休眠功耗过高、待机电流大、唤醒源定位、驱动 suspend 失败、resume 耗时过长等低功耗相关问题时触发。即使用户未明确说'低功耗'，只要问题涉及系统睡不下去、醒不过来、待机电流异常、wakeup source 持锁等，都应触发本技能。如果用户明确提到 Rockchip/RK 芯片的低功耗问题，本技能仍然适用，并会提供 RK 平台特化参考。"
---

# Linux 低功耗与休眠唤醒调试技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| 不知道从哪入手 | §1 快速诊断决策树 |
| 系统睡不下去 / suspend 失败 | §2 |
| 系统醒不过来 / resume 挂死 | §3 |
| 唤醒源定位与管理 | §4 |
| 待机功耗过高 | §5 |
| 驱动 suspend/resume 回调问题 | §6 |
| Runtime PM 设备级电源管理 | §7 |
| Power Domain 管理 | §8 |
| 功耗测量方法 | §9 |
| 常见陷阱与错误认知 | §10 |
| Rockchip 平台特化 | `references/rockchip_suspend.md` |
| Android Suspend 软件层分析 | `references/android_suspend.md` |
| 调试命令速查 | `references/debug_commands.md` |

---

## 1. 快速诊断决策树

遇到低功耗问题时，按此决策树逐步排查：

```
系统低功耗问题？
  │
  ├─ 系统能进入休眠吗？
  │    │
  │    ├─ 否 → Step A: 检查 suspend 流程
  │    │   ├─ echo mem > /sys/power/state 有报错？ → §2
  │    │   ├─ 有进程无法冻结 (Freezing tasks)？ → §2.2
  │    │   ├─ 有驱动 suspend 回调失败？ → §2.3 + §6
  │    │   └─ wakeup source 持锁阻塞？ → §2.4 + §4
  │    │
  │    └─ 是 → Step B: 检查休眠质量
  │         ├─ 能唤醒吗？
  │         │   ├─ 否 → §3 (resume 挂死)
  │         │   └─ 是 → 检查功耗
  │         │        ├─ 待机功耗过高？ → §5
  │         │        ├─ 被意外唤醒？ → §4
  │         │        └─ active 时间过长？ → §5.3
  │         │
  │         └─ 部分场景失败？
  │              ├─ 特定外设插入后失败？ → §6
  │              └─ 随机失败？ → §2.5
  │
  └─ Runtime PM 问题？
       ├─ 设备不进入低功耗 → §7.3
       └─ autosuspend 配置 → §7.4
```

---

## 2. Suspend 流程与失败排查

### 2.1 Linux Suspend 全景流程

```
用户触发 (echo mem > /sys/power/state)
  │
  ▼
Phase 1: Prepare (通知所有设备即将休眠)
  │  → dev->pm->prepare() 回调
  ▼
Phase 2: Freeze Tasks (冻结所有用户态进程和内核线程)
  │  → try_to_freeze_tasks()
  │  → 失败则 abort，报 "Freezing of tasks failed"
  ▼
Phase 3: Suspend Devices (逐层调用设备 suspend 回调)
  │  → suspend → suspend_late → suspend_noirq
  │  → 任一驱动返回错误则 abort
  ▼
Phase 4: Disable Non-Boot CPUs (关闭非引导 CPU)
  │
  ▼
Phase 5: Suspend Enter (平台相关，CPU 进入低功耗)
  │  → 此刻 AP 真正休眠，功耗降至最低
  │  → ⚠️ Suspend Entry ≠ Suspend Enter
  │
  === 唤醒事件 (中断/GPIO/RTC...) ===
  │
  ▼
Phase 6: Resume (反向执行)
  resume_noirq → resume_early → resume → complete
  → 解冻进程 → 恢复用户态
```

> **关键区分**：`Suspend Entry` 是开始执行 suspend flow，可能中途失败退出；`Suspend Enter` 是 AP 真正进入休眠状态。日志中 `suspended for Xs` 才表示真正休眠成功。

### 2.2 冻结任务失败

```bash
# 典型日志
"Freezing of tasks failed after X.XXX seconds (Y tasks refusing to freeze)"

# 排查步骤
# 1. 找到拒绝冻结的进程
dmesg | grep "refusing to freeze"

# 2. 检查该进程状态
cat /proc/<pid>/status
cat /proc/<pid>/wchan    # 看卡在哪个内核函数

# 3. 常见原因
# - 进程正在执行不可中断的 I/O（D 状态）
# - 内核线程未正确响应 freezer 信号
# - 用户态进程忽略了 SIGSTOP（通常是 bug）
```

### 2.3 设备 Suspend 回调失败

```bash
# 典型日志
"dpm_run_callback(): xxx_suspend returns -16"    # -16 = EBUSY
"PM: Device <name> failed to suspend: error -16"

# 排查步骤
# 1. 确认是哪个驱动失败
dmesg | grep -E "failed to suspend|suspend returns"

# 2. 打开详细 PM 调试日志
echo 1 > /sys/power/pm_debug_messages

# 3. 使用 pm_test 逐步定位
echo devices > /sys/power/pm_test
echo mem > /sys/power/state    # 只测试 freeze + device suspend，不真正休眠

# 4. initcall_debug 查看每个回调耗时
echo 1 > /sys/module/kernel/parameters/initcall_debug
# 日志会显示每个 suspend 回调的函数名和耗时
```

### 2.4 Wakeup Source 持锁阻塞

```bash
# 典型日志
"Pending Wakeup Sources: <source_name>"
"PM: Some devices failed to suspend, or early wake event detected"

# 查看当前活跃的 wakeup sources
cat /sys/kernel/debug/wakeup_sources
# 关注 active_count、event_count、active_since 列
# active_since > 0 表示当前正在持锁

# 监控 wakeup_count 变化
cat /sys/power/wakeup_count
# 如果持续变化，说明有唤醒事件不断产生
```

### 2.5 利用 pm_test 分级测试

5 个测试级别（需 CONFIG_PM_DEBUG），从轻到重：`freezer` → `devices` → `platform` → `processors` → `core`。依次设置 `echo <level> > /sys/power/pm_test` 后触发休眠，定位失败层级。

> 详细命令见 `references/debug_commands.md` §3

---

## 3. Resume 失败排查

### 3.1 Resume 挂死

```bash
# 串口是 resume 调试的生命线！
# 必须使用 no_console_suspend 参数
# bootargs 添加: no_console_suspend

# 打开 PM 调试
echo 1 > /sys/power/pm_debug_messages

# initcall_debug 可以看到每个 resume 回调
echo 1 > /sys/module/kernel/parameters/initcall_debug

# 如果 resume 完全卡死无输出：
# 1. 怀疑卡在 resume_noirq 阶段（中断关闭前）
# 2. 使用 earlyprintk/earlycon 确保最早的输出可见
# 3. 检查串口本身是否 resume 正常（UART 驱动问题）
```

### 3.2 Resume 耗时分析

```bash
# 正常 resume 耗时: 20-200ms（因设备数量和驱动质量而异）
# resume 过程可拆解为:

# resume_noirq (中断关闭) → 通常最快
# resume_early → 关键硬件先恢复
# resume → 主体驱动恢复
# complete → 清理收尾

# 用 initcall_debug 找到最慢的回调
dmesg | grep -E "call .+_resume" | sort -k4 -t'=' -n

# 或用 suspend_stats 查看统计
cat /sys/kernel/debug/suspend_stats
```

### 3.3 Resume 后系统异常

```
resume 成功但设备不工作？排查方向：

1. 检查 regulator 是否正确恢复供电
   cat /sys/kernel/debug/regulator/regulator_summary

2. 检查时钟是否正确恢复
   cat /sys/kernel/debug/clk/clk_summary

3. 检查 pinctrl 状态（IO 复用可能被改变）

4. 检查 Power Domain 状态
   cat /sys/kernel/debug/pm_genpd/pm_genpd_summary
```

---

## 4. 唤醒源管理

### 4.1 Linux 唤醒源体系

```
唤醒源层次结构：

Hardware Layer（硬件）
  └─ GPIO / IRQ / RTC / USB / UART / PCIe 等外部信号
      │
Platform Layer（平台固件）
  └─ PMU 状态机筛选哪些信号可以唤醒
      │
Kernel Layer（内核）
  └─ wakeup_source 框架 (drivers/base/power/wakeup.c)
      ├─ device_set_wakeup_capable() — 标记设备有唤醒能力
      ├─ device_set_wakeup_enable()  — 使能/禁用设备唤醒
      ├─ enable_irq_wake()           — 注册中断为唤醒源
      └─ __pm_stay_awake()           — 持锁阻止系统休眠
          __pm_relax()               — 释放锁
```

### 4.2 查看和管理唤醒源

```bash
cat /sys/kernel/debug/wakeup_sources       # 查看所有唤醒源
# 关注: active_since > 0 = 当前持锁, total_time = 累计持锁时长

echo disabled > /sys/devices/.../power/wakeup  # 禁用某设备唤醒
echo enabled > /sys/devices/.../power/wakeup   # 启用某设备唤醒
```

> 各字段详细说明见 `references/debug_commands.md` §5

### 4.3 定位意外唤醒

```bash
# 1. 查看上次唤醒原因
dmesg | grep -i "wake"
dmesg | grep -i "resume"

# 2. 对比休眠前后的 wakeup_sources
#    休眠前 dump 一次，唤醒后 dump 一次，diff 找差异
cat /sys/kernel/debug/wakeup_sources > /tmp/ws_before.txt
# (执行休眠/唤醒)
cat /sys/kernel/debug/wakeup_sources > /tmp/ws_after.txt
diff /tmp/ws_before.txt /tmp/ws_after.txt

# 3. 用 /sys/power/wakeup_count 进行精确控制
#    写入当前 count → 只有新的唤醒事件才能唤醒系统
count=$(cat /sys/power/wakeup_count)
echo $count > /sys/power/wakeup_count && echo mem > /sys/power/state
# 如果 echo wakeup_count 失败，说明在写入时已有新的唤醒事件
```

---

## 5. 功耗分析

### 5.1 功耗基础知识

```
芯片功耗 = 动态功耗 + 静态功耗(漏电)

动态功耗: P(d) = C × V² × F
  C = 负载电容（由电路设计决定）
  V = 工作电压
  F = 工作频率
  → 降频降压是最有效的降功耗手段

静态功耗(漏电): P(s) ∝ e^(T/常数)
  → 温度越高，漏电越大（指数关系！）
  → 高温环境下静态功耗可能远超动态功耗

休眠态功耗主要来源：
  1. 必须保持供电的域（DDR 自刷新、PMU、RTC）
  2. 未正确断电的外设
  3. IO 漏电（浮空引脚、电平不匹配）
  4. 外部器件（PHY、Wi-Fi 模组、传感器等）
```

### 5.2 睡眠占比分析

这是判断系统低功耗是否正常的**最核心指标**。

```bash
# 睡眠占比 = 实际休眠时间 / 总测试时间

# 从内核日志统计
dmesg | grep "suspended for"
# 每次成功休眠会打印: "PM: suspend of devices complete after X.XXX msecs"
# 以及唤醒时: "suspended for X.XXX seconds"

# 判断标准（参考门槛）
# > 80% —— 系统休眠正常，偶发 suspend 失败是背景噪声
# 50-80% —— 有问题但非紧急
# < 50% —— 严重问题，系统无法有效休眠，必须排查
```

### 5.3 Active 时长异常分析

当系统能休眠但 active 时间过长时：

```
分析步骤（强制流程）：

Step 1: 确认 resume 完成时间
  → resume 通常 20-200ms
  → 找到 resume callback 完成的最后一条日志

Step 2: 确认下一次 suspend entry 时间
  → 找到 "PM: suspend entry" 或等效日志

Step 3: 计算真正的 active 时长
  → active = Step 2 - Step 1

Step 4: 判断问题在哪一层
  → resume 本身 >500ms？→ 底层驱动回调卡住 → §6
  → resume 正常 <200ms，但 active 很长？
    → 上层有进程/服务持锁 → 查 wakelock（§4）
    → 定时器/alarm 唤醒后处理耗时 → 查唤醒源
```

### 5.4 功耗优化策略清单

```
□ CPU: 确认 idle governor 选择最深的 C-state
□ CPU: 休眠时所有非引导 CPU offline
□ DDR: 进入自刷新模式 (self-refresh)
□ PLL: 休眠时关闭所有不需要的 PLL
□ 外设时钟: 确认所有时钟门控正确关闭
  cat /sys/kernel/debug/clk/clk_summary | grep "enable"
□ Power Domain: 不需要的 PD 应该 power off
  cat /sys/kernel/debug/pm_genpd/pm_genpd_summary
□ Regulator: 休眠态电压/开关正确配置
  cat /sys/kernel/debug/regulator/regulator_summary
□ GPIO/IO: 无浮空引脚，休眠态电平正确
□ 外部器件: PHY、WiFi、BT、传感器进入低功耗模式
□ 唤醒源: 只保留必要的唤醒源
```

---

## 6. 驱动 Suspend/Resume 回调

### 6.1 回调层次与优先级

```c
/* 驱动 PM 回调层次（优先级从高到低）：
 * 1. PM Domain  (dev->pm_domain->ops)
 * 2. Device Type (dev->type->pm)
 * 3. Device Class (dev->class->pm)
 * 4. Bus Type (dev->bus->pm)
 * 5. Driver (dev->driver->pm)
 *
 * 高优先级完全覆盖低优先级（不是叠加！）
 */

/* 完整的系统 suspend 回调序列: */
// →  .prepare()         — 准备阶段
// →  .suspend()         — 主 suspend
// →  .suspend_late()    — 晚期 suspend
// →  .suspend_noirq()   — 中断关闭后 suspend

/* 完整的系统 resume 回调序列: */
// →  .resume_noirq()    — 中断关闭时 resume
// →  .resume_early()    — 早期 resume
// →  .resume()          — 主 resume
// →  .complete()        — 完成清理
```

### 6.2 常见驱动 suspend 问题

```
问题 1: 返回 -EBUSY
  原因: 设备正在使用中（DMA 传输中、FIFO 未空等）
  修复: suspend 前确保操作完成或取消

问题 2: suspend 回调耗时过长
  原因: 等待硬件响应超时、执行了阻塞操作
  排查: initcall_debug 查看具体函数和耗时

问题 3: resume 后设备不工作
  原因: resume 时未正确恢复寄存器/时钟/电源状态
  排查: 对比 suspend 前后的寄存器 dump

问题 4: 休眠时 crash
  原因: suspend_noirq 阶段访问了已关闭电源域的设备
  → suspend_noirq 时大部分 PD 可能已断电
```

### 6.3 编写正确的 PM 回调

标准 suspend/resume 回调三步模式：

```
suspend: 停止活动 → 保存寄存器 → 关闭时钟
resume:  恢复时钟 → 恢复寄存器 → 重启活动
```

使用 `DEFINE_SIMPLE_DEV_PM_OPS(xxx_pm_ops, xxx_suspend, xxx_resume)` 注册。

---

## 7. Runtime PM

### 7.1 概念

Runtime PM 是设备级的电源管理，在系统运行时让空闲设备自动进入低功耗状态，无需全系统休眠。

```
与 System Suspend 的区别：
  System Suspend = 整个系统休眠（全局）
  Runtime PM    = 单个设备休眠（局部）

Runtime PM 三个回调:
  runtime_suspend() — 设备空闲，进入低功耗
  runtime_resume()  — 设备需要使用，恢复
  runtime_idle()    — 使用计数归零，检查是否可以 suspend
```

### 7.2 Runtime PM 在驱动中的典型用法

```
probe:  pm_runtime_set_active → enable → set_autosuspend_delay → use_autosuspend
使用:   pm_runtime_resume_and_get → 操作设备 → mark_last_busy → put_autosuspend
remove: pm_runtime_dont_use_autosuspend → disable
```

### 7.3 排查设备未进入 Runtime Suspend

```bash
cat /sys/devices/.../power/runtime_status    # active = 未休眠
cat /sys/devices/.../power/runtime_usage     # >0 = 有代码 get 没有 put
cat /sys/devices/.../power/control           # on = 用户态禁止了 RPM
```

最常见原因: `runtime_usage > 0`，说明有 `pm_runtime_get` 未匹配 `put`。

### 7.4 Runtime PM 与 System Suspend 的交互

系统 suspend 时 PM core 会自动处理 Runtime PM：suspend 前增引用防止 runtime suspend、调用 barrier 等待进行中的 RPM 完成、禁用 RPM；resume 后重新启用 RPM、减引用。驱动不需要在 system suspend 回调中手动管理 RPM。

---

## 8. Power Domain 管理

### 8.1 概念

```
Power Domain (PD) = SoC 内的独立供电区域
  → 一个 PD 包含一组 IP 模块
  → PD 内所有设备都 suspend 后，PD 可以断电
  → PD 断电后漏电流降至接近 0

Linux 中由 genpd (Generic Power Domain) 框架管理:
  drivers/base/power/domain.c
```

### 8.2 查看和调试

```bash
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary
# domain  status  /device  runtime_status
# "on" = 供电中，"off" = 已断电（省电）
```

PD 无法关闭常见原因: PD 下有 active 设备、子 PD 未关、驱动未实现 Runtime PM、always-on 约束。

---

## 9. 功耗测量方法

### 9.1 硬件测量

```
方法 1: 供电路径串联 0.01Ω~0.1Ω 精密电阻，测两端压差，I = V_diff / R
方法 2: 电流探头 + 示波器（动态波形分析）
方法 3: 专业功耗分析仪（Keysight N6705C / Rockchip PowerMeterage）

分路测量：VDD_CPU, VDD_GPU, VDD_LOGIC, VCC_DDR, VCC_IO 等
DCDC 效率 80-90%，LDO 输入电流 ≈ 输出电流
```

### 9.2 软件辅助测量

通过 sysfs/debugfs 定性分析哪些域/时钟/电源未正确关闭：

```bash
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary   # PD 状态
cat /sys/kernel/debug/clk/clk_summary | grep -v " 0 "  # 未关时钟
cat /sys/kernel/debug/regulator/regulator_summary  # Regulator 状态
```

> 完整命令列表见 `references/debug_commands.md` §6-§10

---

## 10. 常见陷阱与错误认知

### 10.1 必须避免的判断错误

```
❌ "Suspend Entry = AP 已休眠"
✅ Suspend Entry 只是开始 suspend flow，可能中途失败退出
   只有 "suspended for Xs" 才表示真正休眠

❌ "resume 时出现 Pending Wakeup Sources = 这是问题根因"
✅ resume 过程中检测 pending wakeup source 是正常流程
   只有持续持锁时才是真正的问题

❌ "active 时长 10s = resume 慢"
✅ resume 通常只要 20-200ms
   如果 active 远大于 resume 时间，说明上层有进程持锁

❌ "睡眠占比 98% + 偶发 suspend 失败 = 严重问题"
✅ 睡眠占比 > 80% 时，偶发 freeze/suspend 失败是背景噪声
   只有睡眠占比 < 50% 才需要紧急排查

❌ "IRQ 唤醒次数多 = 底电流高的根因"
✅ IRQ 唤醒是 oneshot 事件（醒一下就回去睡）
   不会导致持续底电流抬升，只会产生短暂峰值

❌ "所有 wakeup source 都应该禁用以降低功耗"
✅ wakeup source 只在 suspend 时起作用
   禁用必要唤醒源会导致系统无法被唤醒
```

### 10.2 常见坑

```
1. no_console_suspend 忘记开
   → 串口自身 suspend 导致 resume 时无输出，无法调试

2. 浮空 GPIO 导致额外功耗
   → 休眠前应将所有未使用的 GPIO 设为确定状态

3. I2C/SPI 设备未正确 suspend
   → 外部 IC 仍在运行，通过 IO 引脚拉电流

4. DDR 未进入自刷新
   → DDR 是休眠态功耗大户之一

5. PLL 未关闭
   → PLL 本身功耗不低，休眠时应尽量关闭

6. CONFIG_PM_DEBUG 编译选项
   → 发布版本不要开 pm_test，有安全风险

7. enable_irq_wake() 但中断已被 disable
   → 必须在 irq enable 状态下注册唤醒
```

---

## 11. 参考路由表

需要更深入的信息时，按需加载以下参考文件：

| 用户问题 | 加载文件 | 内容 |
|---------|---------|------|
| Rockchip 平台 suspend DTS 配置 | `references/rockchip_suspend.md` | RK3588/RK3399/RK3308 sleep-mode-config, wakeup-config, debug 配置, 打印信息解读 |
| Android 系统 suspend 分析 | `references/android_suspend.md` | Android PM 分层架构, Partial Wakelock, 睡眠占比优先级, alarmtimer 排查 |
| 调试命令速查 | `references/debug_commands.md` | 所有低功耗相关的 sysfs/debugfs/proc 接口和工具命令速查 |

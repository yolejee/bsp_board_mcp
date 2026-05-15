# 低功耗调试命令速查

> 所有 Linux 低功耗相关的 sysfs/debugfs/proc 接口和工具命令速查表。

---

## 1. System Suspend 控制

### 1.1 基本操作

```bash
# 查看支持的休眠状态
cat /sys/power/state
# 常见输出: freeze standby mem disk

# 查看当前 mem 对应的 suspend 变体
cat /sys/power/mem_sleep
# 输出: s2idle [deep]   → deep = S2RAM

# 触发休眠
echo mem > /sys/power/state      # Suspend-to-RAM
echo freeze > /sys/power/state   # Suspend-to-Idle (S2Idle)
echo standby > /sys/power/state  # Standby (如果支持)
echo disk > /sys/power/state     # Hibernate

# 选择 mem_sleep 变体
echo deep > /sys/power/mem_sleep     # S2RAM
echo s2idle > /sys/power/mem_sleep   # S2Idle
echo shallow > /sys/power/mem_sleep  # Standby
```

### 1.2 Wakeup Count 精确控制

```bash
# 读取当前 wakeup_count
count=$(cat /sys/power/wakeup_count)

# 写入 count 后触发 suspend
# 只有写入时 count 未变化才会 suspend，否则直接返回失败
echo $count > /sys/power/wakeup_count && echo mem > /sys/power/state
```

### 1.3 Hibernate 控制

```bash
# Hibernate 操作模式
cat /sys/power/disk
# 输出: [platform] shutdown reboot suspend test_resume

echo platform > /sys/power/disk   # 使用平台低功耗状态
echo shutdown > /sys/power/disk   # 直接关机
echo reboot > /sys/power/disk     # 重启（调试用）
echo test_resume > /sys/power/disk   # 测试 resume
```

---

## 2. PM Debug 工具

### 2.1 Debug 开关

```bash
# 打开 PM 调试消息
echo 1 > /sys/power/pm_debug_messages

# 打开 initcall debug（显示每个回调函数名和耗时）
echo 1 > /sys/module/kernel/parameters/initcall_debug

# bootargs 中添加（用于 resume 调试）
# no_console_suspend          → 串口不休眠
# pm_debug_messages           → PM 调试消息
# initcall_debug              → 各回调耗时
# pm_test_delay=5             → pm_test 延迟秒数
```

### 2.2 pm_test 分级测试

```bash
# 需要 CONFIG_PM_DEBUG=y
cat /sys/power/pm_test
# 输出: [none] freezer devices platform processors core

echo freezer > /sys/power/pm_test     # 只测冻结进程
echo devices > /sys/power/pm_test     # + 设备 suspend
echo platform > /sys/power/pm_test    # + 平台回调
echo processors > /sys/power/pm_test  # + 关闭非引导 CPU
echo core > /sys/power/pm_test        # + 系统核心设备
echo none > /sys/power/pm_test        # 恢复正常休眠

# 每设置一个 level 后执行:
echo mem > /sys/power/state
# 系统会在该 level 停止，等待几秒后自动恢复
```

### 2.3 Suspend 统计

```bash
# 查看 suspend 成功/失败统计
cat /sys/kernel/debug/suspend_stats

# 输出示例:
# success: 20
# fail: 5
# failed_freeze: 0
# failed_prepare: 0
# failed_suspend: 5           ← 设备 suspend 失败
# failed_suspend_noirq: 0
# failed_resume: 0
# failed_resume_noirq: 0
# last_failed_dev: alarm adc  ← 最后失败的设备
# last_failed_errno: -16 -16  ← 错误码 (EBUSY)
# last_failed_step: suspend   ← 失败阶段
```

---

## 3. Wakeup Sources

```bash
# 查看所有 wakeup source 完整状态
cat /sys/kernel/debug/wakeup_sources

# 列说明:
# name            唤醒源名称
# active_count    被激活次数
# event_count     产生唤醒事件次数
# wakeup_count    实际导致系统唤醒次数
# expire_count    超时到期次数
# active_since    当前持锁起始时间 (ktime, 0=未持锁)
# total_time      累计持锁总时间
# max_time        单次最长持锁时间
# last_change     最后状态变化时间
# prevent_suspend_time  阻止 suspend 累计时间

# 查看特定设备的唤醒能力
cat /sys/devices/.../power/wakeup           # enabled/disabled
cat /sys/devices/.../power/wakeup_count
cat /sys/devices/.../power/wakeup_active_count
cat /sys/devices/.../power/wakeup_last_time_ms

# 控制设备唤醒能力
echo disabled > /sys/devices/.../power/wakeup
echo enabled > /sys/devices/.../power/wakeup
```

---

## 4. Runtime PM

```bash
# === 设备 Runtime PM 状态 ===
cat /sys/devices/.../power/runtime_status    # active/suspended/suspending/resuming
cat /sys/devices/.../power/runtime_usage     # 使用计数 (>0 不会 suspend)
cat /sys/devices/.../power/runtime_active_kids  # active 子设备数
cat /sys/devices/.../power/runtime_enabled   # 是否使能

# === Runtime PM 控制 ===
echo auto > /sys/devices/.../power/control   # 允许 runtime PM (默认)
echo on > /sys/devices/.../power/control     # 禁止 runtime PM，强制 active

# === Autosuspend 配置 ===
cat /sys/devices/.../power/autosuspend_delay_ms   # 空闲多久后自动 suspend
echo 1000 > /sys/devices/.../power/autosuspend_delay_ms  # 设为 1s

# === 批量查看所有设备 Runtime PM 状态 ===
find /sys/devices -name runtime_status -exec sh -c \
    'echo "$(cat $1): $(dirname $1)"' _ {} \; 2>/dev/null | grep "suspended"
```

---

## 5. Power Domain (genpd)

```bash
# 查看所有 Power Domain 状态
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary

# 输出说明:
# domain                status    slaves/device   runtime_status
# pd_gpu                off                       ---
# pd_vpu                on          /dev/xxx      active
#   → "on" = 供电中 (消耗功耗)
#   → "off" = 已断电 (省电)
#   → 关注哪些 PD 应该 off 但还 on
```

---

## 6. Regulator (电源)

```bash
# 查看所有 regulator 状态
cat /sys/kernel/debug/regulator/regulator_summary

# 查看特定 regulator
cat /sys/kernel/debug/regulator/<name>/voltage
cat /sys/kernel/debug/regulator/<name>/state      # enabled/disabled
cat /sys/kernel/debug/regulator/<name>/consumers   # 哪些设备在使用
```

---

## 7. Clock (时钟)

```bash
# 查看所有时钟状态
cat /sys/kernel/debug/clk/clk_summary

# 找出仍然使能的时钟 (enable_count > 0)
cat /sys/kernel/debug/clk/clk_summary | awk '$3 > 0'

# 查看特定时钟
cat /sys/kernel/debug/clk/<clk_name>/clk_rate         # 频率
cat /sys/kernel/debug/clk/<clk_name>/clk_enable_count  # 使能计数
cat /sys/kernel/debug/clk/<clk_name>/clk_prepare_count # prepare 计数
```

---

## 8. CPU Idle

```bash
# 查看 CPU idle 各状态统计
for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state*/; do
    name=$(cat ${cpu}name)
    desc=$(cat ${cpu}desc 2>/dev/null)
    usage=$(cat ${cpu}usage)
    time=$(cat ${cpu}time)
    echo "$(dirname $(dirname $cpu))/$(basename $cpu): $name ($desc) usage=$usage time=${time}us"
done

# 查看当前 idle governor
cat /sys/devices/system/cpu/cpuidle/current_governor

# 在线/离线 CPU
echo 0 > /sys/devices/system/cpu/cpu3/online   # 离线
echo 1 > /sys/devices/system/cpu/cpu3/online   # 上线
```

---

## 9. Thermal (温度)

```bash
# 查看温度 (单位 milli-Celsius, 85000 = 85°C)
cat /sys/class/thermal/thermal_zone*/temp
cat /sys/class/thermal/thermal_zone*/type

# 查看 cooling device 状态 (cur_state > 0 = 正在降频)
for cd in /sys/class/thermal/cooling_device*/; do
    echo "$(cat ${cd}type): cur=$(cat ${cd}cur_state)/max=$(cat ${cd}max_state)"
done
```

---

## 10. CPUFreq / Devfreq

```bash
# === CPU 频率 ===
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_available_frequencies

# 定频测试（排除变频干扰）
echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
echo 408000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed

# === GPU/DMC devfreq ===
cat /sys/class/devfreq/<dev>/cur_freq
cat /sys/class/devfreq/<dev>/governor
cat /sys/class/devfreq/<dev>/available_frequencies
cat /sys/class/devfreq/<dev>/load

# 定频
echo userspace > /sys/class/devfreq/<dev>/governor
echo <freq> > /sys/class/devfreq/<dev>/userspace/set_freq
```

---

## 11. dmesg 日志过滤

```bash
# === Suspend/Resume 相关 ===
dmesg | grep -iE "suspend|resume|PM:"
dmesg | grep "suspended for"                    # 成功休眠
dmesg | grep "failed to suspend"                # 设备 suspend 失败
dmesg | grep "Freezing of tasks"                # 冻结任务
dmesg | grep -i "wakeup"                        # 唤醒相关
dmesg | grep "Pending Wakeup Sources"           # 阻塞的唤醒源

# === Resume 耗时分析 ===
dmesg | grep -E "call .+_resume" | sort -t'=' -k4 -n

# === Runtime PM 相关 ===
dmesg | grep "runtime PM"
dmesg | grep "runtime status"

# === 动态调试 (dynamic debug) ===
# 打开电源管理子系统的动态调试
echo 'file drivers/base/power/* +p' > /sys/kernel/debug/dynamic_debug/control
echo 'module pm_domain +p' > /sys/kernel/debug/dynamic_debug/control
```

---

## 12. Android 特有命令

```bash
# 上层 Partial Wakelock
adb shell dumpsys power | grep "PARTIAL_WAKE_LOCK"

# 底层 wakeup sources
adb shell cat /sys/kernel/debug/wakeup_sources

# bugreport (包含完整持锁历史)
adb bugreport > bugreport.zip
# 解压后搜索:
#   "All kernel wake locks."    → 底层锁
#   "All partial wake locks."   → 上层锁

# 强制保持唤醒 (调试用)
adb shell svc power stayon true

# 查看电池信息
adb shell dumpsys battery
```

---

## 13. ftrace 追踪 suspend/resume

```bash
# 使用 ftrace 追踪 suspend/resume 各阶段耗时
cd /sys/kernel/debug/tracing

echo 0 > tracing_on
echo > trace

# 追踪 PM 事件
echo 1 > events/power/suspend_resume/enable
echo 1 > events/power/device_pm_callback_start/enable
echo 1 > events/power/device_pm_callback_end/enable

echo 1 > tracing_on

# 执行 suspend/resume
echo mem > /sys/power/state

# 读取结果
echo 0 > tracing_on
cat trace > /tmp/pm_trace.txt

# 清理
echo 0 > events/power/suspend_resume/enable
echo 0 > events/power/device_pm_callback_start/enable
echo 0 > events/power/device_pm_callback_end/enable
```

---

## 14. 常用一行命令

```bash
# 找出所有 runtime_usage > 0 (阻止 runtime suspend) 的设备
find /sys/devices -name runtime_usage -exec sh -c \
    '[ "$(cat $1)" -gt 0 ] && echo "usage=$(cat $1): $(dirname $1)"' _ {} \; 2>/dev/null

# 找出所有 runtime PM 被禁用的设备
find /sys/devices -name control -path "*/power/*" -exec sh -c \
    '[ "$(cat $1)" = "on" ] && echo "forced-on: $(dirname $(dirname $1))"' _ {} \; 2>/dev/null

# 快速检查功耗相关状态
echo "=== Power Domains ===" && cat /sys/kernel/debug/pm_genpd/pm_genpd_summary
echo "=== Active Clocks ===" && cat /sys/kernel/debug/clk/clk_summary | awk '$3 > 0'
echo "=== Regulators ===" && cat /sys/kernel/debug/regulator/regulator_summary
echo "=== Temperatures ===" && paste /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp
```

---
name: perf_rk
description: "Rockchip 瑞芯微 RK 平台性能问题排查技能。覆盖 RK3588/RK3568/RK3566/RK3399/RK3328/RK3288/PX30 等全系列芯片的 CPU、GPU、DDR、IO、网络、多媒体、显示等子系统性能分析与优化。触发关键词包括但不限于：性能、卡顿、帧率低、延迟高、CPU占用高、发热降频、throughput、bandwidth、perf、systrace、streamline、火焰图、flamegraph、cyclictest、实时性、jitter、latency、OOM、内存泄漏、DDR带宽、IO慢、读写慢、USB传输慢、PCIe性能、网络吞吐、丢包、编解码性能、RGA性能、GPU跑分、glmark2、unixbench、功耗高、温控降频、定频测试、cpufreq、devfreq、thermal、opp-table。当用户描述任何 Rockchip 平台上的性能相关问题（即使没有明确说'性能'二字，只要涉及慢、卡、热、延迟、吞吐量、跑分低等现象），都应触发本技能。"
---

# Rockchip RK 平台性能问题排查技能

> **与 perf_common 的关系**: 本技能覆盖 RK 平台特有信息 (CPU 主频表、Leakage/PVTM、rk-msch-probe DDR 带宽工具、GPU devfreq 路径、芯片跑分/功耗数据)。通用方法论 (fio 详细参数、iperf3 用法、火焰图生成、cyclictest 调优) 见 perf_common 技能。

## 快速导航

```
性能问题类型？
 不知道瓶颈在哪     第 1 节 (快速诊断决策树)
 CPU 相关           第 2 节
 GPU 相关           第 3 节
 DDR/内存           第 4 节
 温控/功耗          第 5 节 + references/dvfs_thermal.md
 IO/存储            第 6 节
 实时性/延迟        第 7 节
 USB/PCIe/网络等    第 8 节 + references/subsystem_perf.md
 需要工具指导       第 9 节 + references/tools.md
 基准跑分参考       第 10 节
```

---

## 1. 快速诊断流程

### Step 1: 是否在降频？

```bash
# 温度
cat /sys/class/thermal/thermal_zone0/temp    # CPU
cat /sys/class/thermal/thermal_zone1/temp    # GPU (部分平台)

# cooling device 是否限频 (cur_state > 0 = 降频中)
cat /sys/class/thermal/thermal_zone0/cdev0/cur_state
cat /sys/class/thermal/thermal_zone0/cdev1/cur_state

# CPU 频率
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq
# RK3399 大核
cat /sys/devices/system/cpu/cpufreq/policy4/scaling_cur_freq
# RK3588 三 cluster
cat /sys/devices/system/cpu/cpufreq/policy6/scaling_cur_freq
```

> 温度 >85C + cdev cur_state >0  **温控限频**  转 [第 5 节](#5-温控与功耗)

### Step 2: 频率策略

```bash
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
cat /sys/class/devfreq/ff400000.gpu/governor        # GPU (路径因芯片异)
cat /sys/class/devfreq/dmc/governor                  # DDR

# 全部切 performance 做基线
echo performance | tee $(find /sys/ -name *governor) /dev/null 2>&1
```

> 切 performance 后性能显著提升  **governor 不合理**  调参

### Step 3: 负载分布

```bash
top -b -n 1 | head -20
mpstat -P ALL 1 3
cat /proc/interrupts
```

> 单核满载  绑核优化 | iowait 高  [第 6 节](#6-io存储性能) | 中断集中  [第 7 节](#7-实时性能排查)

### Step 4: 内存

```bash
free -h
cat /proc/meminfo | grep -E "MemAvailable|SwapFree|CmaFree"
```

> MemAvailable 极低  [第 4 节](#4-ddr内存性能排查)

### 一键状态采集

```bash
#!/bin/sh
echo "===== Temp ====="
for tz in /sys/class/thermal/thermal_zone*/; do
    echo "$(basename $tz): $(cat ${tz}temp) mC, policy=$(cat ${tz}policy)"
done
echo "===== CPU Freq ====="
for p in /sys/devices/system/cpu/cpufreq/policy*/; do
    echo "$(basename $p): cur=$(cat ${p}scaling_cur_freq) max=$(cat ${p}scaling_max_freq) gov=$(cat ${p}scaling_governor)"
done
echo "===== GPU ====="
for d in /sys/class/devfreq/*/; do
    [ -f "${d}load" ] && echo "$(basename $d): freq=$(cat ${d}cur_freq) load=$(cat ${d}load) gov=$(cat ${d}governor)"
done
echo "===== DDR ====="
[ -d /sys/class/devfreq/dmc ] && echo "DDR: freq=$(cat /sys/class/devfreq/dmc/cur_freq) gov=$(cat /sys/class/devfreq/dmc/governor)"
echo "===== Memory =====" && free -h
echo "===== Cooling ====="
for cd in /sys/class/thermal/thermal_zone0/cdev*/; do
    [ -f "${cd}cur_state" ] && echo "$(basename $cd): $(cat ${cd}cur_state)/$(cat ${cd}max_state) [$(cat ${cd}type)]"
done
echo "===== Top 10 =====" && top -b -n 1 | head -17
```

---

## 2. CPU 性能排查

### 2.1 RK 各平台 CPU 最高主频

| 平台 | ARM 核 | 最高主频 |
|------|--------|----------|
| RK3288 | 4A17 | 1608 MHz |
| RK3328 | 4A53 | 1296 MHz |
| RK3399 | 2A72+4A53 | 1800+1416 MHz |
| RK3566 | 4A55 | 1800 MHz |
| RK3568 | 4A55 | 2000 MHz |
| RK3588 | 4A55+2A76+2A76 | 1800+2400+2400 MHz |

### 2.2 定频测试

```bash
# 单 cluster
echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
echo 1800000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed

# RK3399 (双 cluster)
echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
echo 1416000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed    # 小核
echo userspace > /sys/devices/system/cpu/cpufreq/policy4/scaling_governor
echo 1800000 > /sys/devices/system/cpu/cpufreq/policy4/scaling_setspeed    # 大核

# RK3588 (三 cluster)
echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
echo 1800000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed    # 4A55
echo userspace > /sys/devices/system/cpu/cpufreq/policy4/scaling_governor
echo 2400000 > /sys/devices/system/cpu/cpufreq/policy4/scaling_setspeed    # 2A76
echo userspace > /sys/devices/system/cpu/cpufreq/policy6/scaling_governor
echo 2400000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_setspeed    # 2A76

# 验证
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq
cat /sys/kernel/debug/clk/armclk/clk_rate
```

### 2.3 Leakage/PVTM 调压

RK 平台通过芯片 leakage/PVTM 微调电压，同批次芯片可能用不同电压档：

```bash
dmesg | grep leakage
dmesg | grep pvtm
```

> Governor 调参、OPP Table DTS、Leakage/PVTM 配置详见 `references/dvfs_thermal.md`

---

## 3. GPU 性能排查

### 3.1 GPU 频率与负载

```bash
# 路径因芯片而异:
# RK3399: ff400000.gpu  RK3568/RK3566: fde60000.gpu  RK3588: fb000000.gpu

cat /sys/class/devfreq/ff400000.gpu/cur_freq
cat /sys/class/devfreq/ff400000.gpu/load
cat /sys/class/devfreq/ff400000.gpu/available_frequencies

# 定频
echo userspace > /sys/class/devfreq/ff400000.gpu/governor
echo 800000000 > /sys/class/devfreq/ff400000.gpu/userspace/set_freq
```

### 3.2 GPU 调频阈值 (DTS)

```dts
gpu: gpu@ffa30000 {
    upthreshold = <75>;       /* 默认 90，减小更快升频 */
    downdifferential = <10>;
};
```

---

## 4. DDR/内存性能排查

### 4.1 DDR 频率

```bash
cat /sys/class/devfreq/dmc/cur_freq
cat /sys/class/devfreq/dmc/governor
cat /sys/class/devfreq/dmc/available_frequencies

# 定频
echo userspace > /sys/class/devfreq/dmc/governor
echo 780000000 > /sys/class/devfreq/dmc/userspace/set_freq

# 场景状态
cat /sys/class/devfreq/dmc/system_status
```

### 4.2 DDR 带宽测试

```bash
# rk-msch-probe (RK 专用)
# 使用前必须先 DDR 定频
rk-msch-probe -c rk3588 -d 1000 -t 10
```

| 字段 | 含义 | 关注 |
|------|------|------|
| `ddr load` | 总带宽利用率 | 持续 >70% 考虑提频 |
| `RD/WR` | 读/写带宽 | 判断读写比例 |
| `ACT` | access:active | 越大越好 |

### 4.3 DDR 问题速查

| 现象 | 可能原因 | 排查方法 |
|------|---------|---------|
| 死机/重启 | 电源或信号质量 | 降频到 200MHz 看是否稳定 |
| 花屏 | DDR 变频或带宽不足 | `echo performance > governor` |
| 串口报错 | 焊接问题 | 看 "rd addr" / "W FF != R" |
| 高负载异常 | 电源不足 | 固定 CPU/GPU 低频，抬高 logic 电压 |

### 4.4 内存排查

```bash
cat /proc/meminfo | grep -E "MemAvailable|Slab|CmaTotal|CmaFree"
cat /proc/slabinfo | awk 'BEGIN{s=0}{s+=$3*$4}END{print s/1024/1024" MB"}'
cat /sys/kernel/debug/dma_buf/bufinfo
echo 3 > /proc/sys/vm/drop_caches      # 清缓存 (仅测试)
```

---

## 5. 温控与功耗

### 5.1 温控排查

```bash
for tz in /sys/class/thermal/thermal_zone*/; do
    echo "$(cat ${tz}type): $(cat ${tz}temp) mC"
done

cat /sys/class/thermal/thermal_zone0/trip_point_0_temp   # 开始降频温度
cat /sys/class/thermal/thermal_zone0/trip_point_1_temp   # 目标温度

# 是否在限频
for cd in /sys/class/thermal/thermal_zone0/cdev*/; do
    echo "$(cat ${cd}type): state=$(cat ${cd}cur_state)/$(cat ${cd}max_state)"
done
```

### 5.2 临时关闭温控

```bash
echo user_space > /sys/class/thermal/thermal_zone0/policy
echo 0 > /sys/class/thermal/thermal_zone0/cdev0/cur_state
```

⚠ 关闭温控后芯片可能过热损坏，仅用于短时调试。hw-tshut 仍有效。

### 5.3 Thermal Governor

| Governor | 行为 | 适用 |
|----------|------|------|
| `power_allocator` | PID 控制，按功耗预算 | 默认推荐 |
| `step_wise` | 逐级降频 | 简单可靠 |
| `user_space` | 不限制 | 调试用 |

> DTS thermal 配置、`sustainable-power` 调参、Thermal Trace 分析见 `references/dvfs_thermal.md`

---

## 6. IO/存储性能

### 6.1 快速测试

```bash
dd if=/dev/zero of=/tmp/test bs=1M count=1024 oflag=direct
dd if=/tmp/test of=/dev/null bs=1M iflag=direct

fio --name=randread --ioengine=libaio --direct=1 --bs=4k \
    --numjobs=4 --size=256M --runtime=30 --rw=randread
```

### 6.2 ioblame (按进程/文件统计)

```bash
# 需: CONFIG_BLK_DEV_IO_TRACE=y  CONFIG_FUNCTION_TRACER=y
./ioblame.sh -r -w -v
```

---

## 7. 实时性能排查

### 7.1 cyclictest

```bash
cyclictest -m -n -p 99 -t 4 -a -D 60
# 关注 Max 列
```

### 7.2 中断绑核 + RT 线程

```bash
# 查看中断
cat /proc/interrupts | grep <device>
# 绑到 CPU4
echo 10 > /proc/irq/<IRQ>/smp_affinity

# RT 线程扫描
for t in /proc/$PID/task/*/; do
    name=$(cat ${t}comm)
    policy=$(grep ^policy ${t}sched | awk '{print $3}')
    [ "$policy" = "1" ] && echo "RT: $name"
done
```

---

## 8. 子系统性能专项

完整内容见 `references/subsystem_perf.md`。

| 子系统 | 快速检查 | 关注 |
|--------|---------|------|
| **USB** | `lsusb -t` / `cat .../speed` | 确认 USB3 设备走 USB3 口 |
| **PCIe** | `lspci -vvv \| grep LnkSta` | Speed + Width 是否预期 |
| **GMAC** | `ethtool eth0` / `iperf3` |  |
| **MPP** | `cat /proc/mpp_service/dump/capability` | 硬件编解码能力 |
| **RGA** | `cat /sys/kernel/debug/rkrga/driver_version` | RGA2 vs RGA3 |
| **显示** | `cat /sys/kernel/debug/dri/0/summary` | 帧率/VOP 状态 |

---

## 9. 工具速查

| 工具 | 用途 | 关键命令 |
|------|------|---------|
| `perf` | CPU 热点 | `perf record -g -p $PID`  `perf report` |
| `ftrace` | 调度/中断 | 手动或 `trace-cmd record -e sched -e irq` |
| `systrace` | Android | `python systrace.py -b 32768 -t 15 gfx sched freq` |
| `streamline` | DS5 硬件计数器 | 需 gatord + DS5 license |
| `cyclictest` | 实时性 | 见第 7 节 |

> 各工具完整用法、内核配置、火焰图生成见 `references/tools.md`

---

## 10. 基准测试参考

### 10.1 测试前设置

```bash
echo performance | tee $(find /sys/ -name *governor) /dev/null 2>&1
echo user_space > /sys/class/thermal/thermal_zone0/policy
```

### 10.2 Glmark2 参考分数 (800600, Performance)

| 平台 | Score |
|------|-------|
| RK3588 | 4851 |
| RK3399 | 812 |
| RK3568 | 560 |
| RK3566 | 485 |
| PX30 | 369 |
| RK3288 | 57 |

### 10.3 UnixBench 参考分数

| 平台 | 单任务 | 多任务 |
|------|--------|--------|
| RK3588 | 1342.5 | 4036.2 |
| RK3399 | 654.7 | 1402.8 |
| RK3568 | 497.3 | 1146.5 |
| RK3566 | 456.9 | 1039.1 |
| PX30 | 290.6 | 746.4 |
| RK3288 | 421.7 | 989.5 |

### 10.4 RK3399 功耗参考 (Buildroot)

| 场景 | 总功耗 | SoC 端 |
|------|--------|--------|
| 静态桌面 | 10.8W | 1.88W |
| 1080P 视频 | 11.86W | 2.34W |
| Glmark2 | 11.98W | 2.41W |
| 压力测试 | 15.72W | 4.13W |
| 深度休眠 |  | 120.5mW |

### 10.5 RK3588 功耗参考 (Linux, 定频最高)

| 场景 | SoC 端 (典型值) | 说明 |
|------|-----------------|------|
| 待机 (idle) | ~2.5W | 所有核降到最低频 |
| 1080P 硬解 (H.265) | ~3.5W | VPU 硬件解码 |
| 4K@60 硬解 | ~4.5W | 单路 4K |
| Glmark2 全速 | ~6.5W | GPU Mali-G610 MP4 |
| CPU 压力 (8核满载) | ~10W | stress-ng --cpu 8 |
| CPU+GPU+NPU 全满 | ~12-15W | 散热方案关键基准 |
| 深度休眠 | ~150mW | 含 DDR self-refresh |

> 实际功耗因板卡电路、DDR 颗粒、外设配置差异较大，以上为 EVB 板参考值。

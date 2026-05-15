---
name: perf_common
description: "通用 Linux 嵌入式平台性能问题排查技能（不限 SoC 平台）。覆盖 CPU、GPU、内存、IO、网络、多媒体、显示等子系统的性能分析与优化方法论。适用于所有运行 Linux 的嵌入式 SoC 平台：Rockchip、Allwinner、NXP i.MX、TI Sitara、Qualcomm、MediaTek、STM32MP、Xilinx/Zynq、RISC-V 等。触发关键词：性能、卡顿、帧率低、延迟高、CPU占用高、发热降频、perf、ftrace、trace-cmd、火焰图、flamegraph、cyclictest、实时性、latency、DDR带宽、IO慢、fio、iperf3、GPU跑分、glmark2、stress-ng、温控降频、cpufreq、devfreq、thermal、opp-table、cgroup。当用户描述嵌入式 Linux 平台上的性能问题且未指定 SoC 厂商时触发。若明确提到 Rockchip/RK，应优先使用 perf_rk 技能。"
---

# 通用 Linux 嵌入式平台性能问题排查技能

## 快速导航

```
性能问题类型？
 不知道瓶颈在哪     第 1 节 (快速诊断决策树)
 CPU 相关           第 2 节
 GPU 相关           第 3 节
 内存/DDR 相关      第 4 节
 温控/功耗          第 5 节 + references/dvfs_thermal.md
 IO/存储            第 6 节
 实时性/延迟        第 7 节
 USB/PCIe/网络等    第 8 节 + references/subsystem_perf.md
 需要工具指导       第 9 节 + references/tools.md
 基准测试方法       第 10 节
```

---

## 1. 快速诊断流程

遇到性能问题时，按此决策树逐步排查：

### Step 1: 是否在降频？

温控降频是最常见的性能下降原因。

```bash
# 查看温度 (单位 milli-Celsius, 85000 = 85C)
cat /sys/class/thermal/thermal_zone*/temp
cat /sys/class/thermal/thermal_zone*/type   # 区分 CPU/GPU/SoC

# cooling device 是否限频 (cur_state > 0 = 正在降频)
for cd in /sys/class/thermal/cooling_device*/; do
    echo "$(cat ${cd}type): state=$(cat ${cd}cur_state)/$(cat ${cd}max_state)"
done

# CPU 当前 vs 最大频率
for p in /sys/devices/system/cpu/cpufreq/policy*/; do
    echo "$(basename $p): cur=$(cat ${p}scaling_cur_freq) max=$(cat ${p}scaling_max_freq)"
done
```

> 温度过高 + cur_state > 0  **温控限频**  转 [第 5 节](#5-温控与功耗)

### Step 2: 频率策略对吗？

```bash
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor
cat /sys/class/devfreq/*/governor 2>/dev/null

# 快速切到性能模式做基线
for f in $(find /sys/devices/system/cpu/cpufreq/ -name scaling_governor); do
    echo performance > $f
done
for f in $(find /sys/class/devfreq/ -name governor 2>/dev/null); do
    echo performance > $f 2>/dev/null
done
```

> 切 performance 后性能显著提升  **governor 策略不合理**  转 [第 2 节](#2-cpu-性能排查)

### Step 3: 负载分布

```bash
top -b -n 1 | head -20          # CPU 整体
mpstat -P ALL 1 3               # 各核利用率 (需 sysstat)
cat /proc/stat | grep cpu       # 关注 iowait 列
```

> - 单核 100% 其余空闲  应用未利用多核  绑核/多线程
> - iowait 高  **IO 瓶颈**  转 [第 6 节](#6-io存储性能)
> - 中断集中某核  中断绑核  转 [第 7 节](#7-实时性能排查)

### Step 4: 内存够吗？

```bash
free -h
cat /proc/meminfo | grep -E "MemAvailable|SwapFree|CmaFree"
cat /proc/pressure/memory 2>/dev/null     # PSI (内核 4.20+)
```

> MemAvailable 极低或 swap 大量使用  **内存不足**  转 [第 4 节](#4-内存性能排查)

### 一键状态采集脚本

```bash
#!/bin/sh
echo "===== System =====" && uname -a
cat /proc/device-tree/model 2>/dev/null
echo "===== Temp ======"
for tz in /sys/class/thermal/thermal_zone*/; do
    echo "$(basename $tz) [$(cat ${tz}type 2>/dev/null)]: $(cat ${tz}temp 2>/dev/null) mC"
done
echo "===== CPU Freq ====="
for p in /sys/devices/system/cpu/cpufreq/policy*/; do
    echo "$(basename $p): cur=$(cat ${p}scaling_cur_freq) max=$(cat ${p}scaling_max_freq) gov=$(cat ${p}scaling_governor)"
done
echo "===== Devfreq ====="
for d in /sys/class/devfreq/*/; do
    echo "$(basename $d): freq=$(cat ${d}cur_freq 2>/dev/null) gov=$(cat ${d}governor 2>/dev/null)"
done
echo "===== Cooling ====="
for cd in /sys/class/thermal/cooling_device*/; do
    echo "$(basename $cd) [$(cat ${cd}type 2>/dev/null)]: $(cat ${cd}cur_state 2>/dev/null)/$(cat ${cd}max_state 2>/dev/null)"
done
echo "===== Memory =====" && free -h
echo "===== Top 10 =====" && top -b -n 1 | head -17
```

---

## 2. CPU 性能排查

### 2.1 CPUFreq 核心接口

路径：`/sys/devices/system/cpu/cpufreq/policy{N}/`

| 接口 | 说明 |
|------|------|
| `scaling_available_frequencies` | OPP 表中可用频率列表 |
| `scaling_available_governors` | 可用 governor |
| `scaling_governor` | 当前 governor |
| `scaling_cur_freq` | 当前频率 |
| `scaling_max_freq` / `scaling_min_freq` | 软件限制范围 |
| `scaling_setspeed` | userspace 模式下手动设频 |
| `stats/time_in_state` | 各频率运行时间统计 |

### 2.2 Governor 速查

| Governor | 行为 | 适用场景 |
|----------|------|----------|
| `performance` | 始终最高频 | 基准测试 |
| `powersave` | 始终最低频 | 省电 |
| `ondemand` | 按负载大幅调频 | 通用 |
| `conservative` | 平滑调频 | 通用 (保守) |
| `interactive` | 响应快，参数丰富 | Android (Linux 4.x) |
| `schedutil` | EAS 调度器驱动 | Linux 5.x+ 推荐 |
| `userspace` | 手动设频 | 定频测试 |

### 2.3 定频测试

定频排除调频策略影响最基本的排查手段：

```bash
# performance 锁最高频
echo performance > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor

# 或 userspace 手动定频
echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
echo <freq_khz> > /sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed

# 多 cluster 平台需对每个 policy 单独操作
ls /sys/devices/system/cpu/cpufreq/    # 查看有多少 policy
```

### 2.4 CPU 绑核

```bash
# taskset
taskset -c 4-5 ./my_app            # 启动时绑核
taskset -pc 4-5 $PID               # 运行中绑核

# cpuset cgroup
mkdir -p /dev/cpuset/critical
echo 4-5 > /dev/cpuset/critical/cpus
echo 0 > /dev/cpuset/critical/mems
echo $PID > /dev/cpuset/critical/tasks

# 内核启动参数隔离 CPU (不参与普通调度)
# bootargs: isolcpus=4,5 nohz_full=4,5 rcu_nocbs=4,5
```

> Governor 详细调参、OPP Table DTS 配置见 `references/dvfs_thermal.md`

---

## 3. GPU 性能排查

### 3.1 GPU 状态 (Devfreq)

```bash
# 找到 GPU devfreq 设备
ls /sys/class/devfreq/     # 常见: *.gpu, mali, panfrost-devfreq

GPU_DEV=$(ls /sys/class/devfreq/ | head -1)
cat /sys/class/devfreq/$GPU_DEV/cur_freq
cat /sys/class/devfreq/$GPU_DEV/available_frequencies
cat /sys/class/devfreq/$GPU_DEV/governor
cat /sys/class/devfreq/$GPU_DEV/load 2>/dev/null

# GPU 定频
echo userspace > /sys/class/devfreq/$GPU_DEV/governor
echo <max_freq> > /sys/class/devfreq/$GPU_DEV/userspace/set_freq
```

### 3.2 GPU 基准

```bash
glmark2-es2-drm --off-screen       # 无显示器
glmark2-es2-wayland                 # Wayland
# 测试前确保 GPU 定频最高 + 关温控
```

---

## 4. 内存性能排查

### 4.1 DDR 频率

```bash
ls /sys/class/devfreq/              # 找 dmc/ddr_devfreq/memory-controller
cat /sys/class/devfreq/dmc/cur_freq 2>/dev/null
cat /sys/class/devfreq/dmc/available_frequencies 2>/dev/null

# 定频
echo userspace > /sys/class/devfreq/dmc/governor
echo <max_freq> > /sys/class/devfreq/dmc/userspace/set_freq
```

### 4.2 内存用量

```bash
free -h
cat /proc/meminfo | grep -E "MemTotal|MemAvailable|Cached|Slab|CmaTotal|CmaFree"

# 按进程排序
ps aux --sort=-%mem | head -20

# 内核 slab
cat /proc/slabinfo | awk 'BEGIN{s=0}{s+=$3*$4}END{print s/1024/1024" MB"}'

# DMA-BUF 泄漏
cat /sys/kernel/debug/dma_buf/bufinfo
```

### 4.3 OOM 排查

```bash
dmesg | grep -i "out of memory\|oom\|killed process"

# 追踪进程内存增长
while true; do grep -E "VmRSS|VmSize" /proc/<PID>/status; sleep 5; done
```

### 4.4 内存带宽

```bash
mbw 256                              # 内存拷贝带宽
stream                               # COPY/SCALE/ADD/TRIAD
lat_mem_rd -P 1 256m 128             # 内存延迟
```

---

## 5. 温控与功耗

### 5.1 Thermal 框架

```bash
# 温度
for tz in /sys/class/thermal/thermal_zone*/; do
    echo "$(basename $tz) [$(cat ${tz}type)]: $(cat ${tz}temp) mC"
done

# trip point (温控阈值)
cat /sys/class/thermal/thermal_zone0/trip_point_0_temp   # 起始限频温度
cat /sys/class/thermal/thermal_zone0/trip_point_0_type   # passive/active/critical
```

### 5.2 临时关闭温控 (调试用)

```bash
echo user_space > /sys/class/thermal/thermal_zone0/policy
# 或
echo disabled > /sys/class/thermal/thermal_zone0/mode
```

 关闭温控后芯片可能过热损坏，仅用于短时调试。

### 5.3 Thermal Governor

| Governor | 行为 | 适用 |
|----------|------|------|
| `power_allocator` | PID 控制，按功耗预算分配 | 推荐，温控精准 |
| `step_wise` | 逐级降频 | 简单可靠 |
| `user_space` | 不限制 | 调试用 |
| `bang_bang` | 开关量 | 风扇控制 |

> DTS thermal 配置、`sustainable-power` 调参、功耗分析见 `references/dvfs_thermal.md`

---

## 6. IO/存储性能

### 6.1 快速检查

```bash
iostat -x 1 5                       # 需 sysstat
# 关注: %util (>90%=饱和), await (ms), rMB/s, wMB/s
cat /proc/pressure/io 2>/dev/null   # PSI
```

### 6.2 IO 基准测试

```bash
# dd 顺序
dd if=/dev/zero of=/tmp/test bs=1M count=512 oflag=direct conv=fsync
dd if=/tmp/test of=/dev/null bs=1M iflag=direct

# fio 随机 4K
fio --name=randread --ioengine=libaio --direct=1 --bs=4k \
    --numjobs=4 --size=256M --runtime=30 --rw=randread --iodepth=32
```

### 6.3 IO 调度器

```bash
cat /sys/block/mmcblk0/queue/scheduler
# mq-deadline: 适合 eMMC/UFS/NVMe (推荐)
# bfq: 低速设备或需要公平性
# none/noop: NVMe 等高速设备

echo mq-deadline > /sys/block/mmcblk0/queue/scheduler
blockdev --setra 2048 /dev/mmcblk0   # 预读 1MB
```

### 6.4 嵌入式存储速度参考

| 存储类型 | 顺序读 | 顺序写 | 4K 随机读 |
|---------|--------|--------|-----------|
| eMMC 5.1 (HS400) | ~300 MB/s | ~150 MB/s | ~10K IOPS |
| UFS 2.1 | ~800 MB/s | ~200 MB/s | ~40K IOPS |
| NVMe (Gen3 x2) | ~1.5 GB/s | ~800 MB/s | ~100K IOPS |
| SD (UHS-I) | ~90 MB/s | ~60 MB/s | ~3K IOPS |

### 6.5 fio 典型测试场景

```bash
# 顺序写吞吐量
fio --name=seqwr --ioengine=libaio --direct=1 --bs=1M \
    --numjobs=1 --size=512M --runtime=30 --rw=write --iodepth=4

# 混合随机读写 (70% 读 30% 写, 模拟数据库)
fio --name=randrw --ioengine=libaio --direct=1 --bs=4k \
    --numjobs=4 --size=256M --runtime=30 --rw=randrw --rwmixread=70 --iodepth=32

# 延迟测试 (关注 clat 的 p99/p99.9)
fio --name=lat --ioengine=libaio --direct=1 --bs=4k \
    --numjobs=1 --size=64M --runtime=30 --rw=randread --iodepth=1 \
    --lat_percentiles=1 --percentile_list=50:90:99:99.9

# 关键输出指标:
# bw= (带宽)  iops= (每秒IO数)  clat percentiles (完成延迟分布)
```

### 6.6 网络性能 (iperf3)

```bash
# 服务端
iperf3 -s

# TCP 吞吐量 (单流)
iperf3 -c <server_ip> -t 30

# TCP 多流 (充分利用带宽)
iperf3 -c <server_ip> -P 4 -t 30

# UDP 测试 (关注丢包率和 jitter)
iperf3 -c <server_ip> -u -b 900M -t 30
# 输出: Jitter, Lost/Total Datagrams, 丢包率

# 反向测试 (server → client, 测上行)
iperf3 -c <server_ip> -R -t 30

# 千兆以太网参考值:
#   TCP 单流: 930~940 Mbps
#   TCP 4 流: 940~945 Mbps
#   低于 800 Mbps: 检查网线/PHY 协商/中断亲和/MTU

# 排查低吞吐
ethtool eth0 | grep -i speed                  # 协商速率
cat /proc/interrupts | grep eth               # 中断是否均衡
echo 2 > /proc/irq/<eth_irq>/smp_affinity     # 绑到 CPU1
ethtool -k eth0 | grep -i offload             # 检查 offload
ifconfig eth0 mtu 9000                        # jumbo frame (需交换机支持)
```

---

## 7. 实时性能排查

### 7.1 关键指标

- **硬实时**：必须在确定时间内完成 (电机控制)
- **软实时**：偶尔超时可接受 (音视频)
- 核心指标：**最大延迟** (worst-case latency)，不是平均

### 7.2 cyclictest

```bash
cyclictest -m -n -p 99 -t 4 -a -D 60
# -m: mlockall  -p 99: 最高 RT 优先级  -t 4: 4 线程  -D 60: 60 秒
# 关注 Max 列: 标准内核 100-500us, PREEMPT_RT 20-50us
```

### 7.3 实时优化要点

```bash
# 中断绑核
echo <cpu_mask> > /proc/irq/<IRQ>/smp_affinity

# RT 线程
chrt -f 99 -p $PID                    # SCHED_FIFO, priority 99

# 内核配置
# CONFIG_PREEMPT=y / CONFIG_PREEMPT_RT=y
# CONFIG_HIGH_RES_TIMERS=y  CONFIG_HZ=1000
# bootargs: isolcpus=4,5 nohz_full=4,5
```

---

## 8. 子系统性能专项

完整内容见 `references/subsystem_perf.md`。

| 子系统 | 关键命令 | 关注点 |
|--------|---------|--------|
| **USB** | `lsusb -t` / `cat .../speed` | 12=1.1, 480=2.0, 5000=3.0 |
| **PCIe** | `lspci -vvv \| grep LnkSta` | Speed + Width 是否符合预期 |
| **网络** | `ethtool eth0 \| grep Speed` / `iperf3` | 千兆 TCP ~940 Mbps |
| **显示** | `cat /sys/class/drm/card0-*/modes` | 分辨率和刷新率 |
| **启动** | `systemd-analyze blame` | 各服务耗时 |

---

## 9. 性能分析工具速查

| 工具 | 用途 | 关键命令 |
|------|------|---------|
| `perf` | CPU 热点/火焰图 | `perf record -g -p $PID`  `perf report` |
| `ftrace` / `trace-cmd` | 调度/中断/时序 | `trace-cmd record -e sched -e irq` |
| `bpftrace` | 动态追踪 (内核4.9+) | `bpftrace -e 'profile:hz:99 { @[kstack]=count(); }'` |
| `stress-ng` | 压力测试 | `stress-ng --cpu 4 --vm 2 --timeout 60s` |
| `cyclictest` | 实时性测试 | 见第 7 节 |
| `htop` / `atop` | 增强 top | `apt install htop` |
| `iotop` | 按进程 IO | `apt install iotop` |
| `pidstat` | 进程级统计 | `pidstat -u -d 1` |

> 各工具详细用法、配置要求、火焰图生成见 `references/tools.md`

---

## 10. 基准测试

### 10.1 测试前设置

⚠ 性能基准测试前必须先定频（CPU/GPU/DDR 全部 performance），否则结果不具参考价值。

```bash
# CPU/GPU/DDR 全部 performance
for f in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
    echo performance > $f
done
for f in /sys/class/devfreq/*/governor; do
    echo performance > $f 2>/dev/null
done
# 关温控 (仅测试)
for tz in /sys/class/thermal/thermal_zone*/; do
    echo user_space > ${tz}policy 2>/dev/null
done
```

### 10.2 常用基准

| 维度 | 工具 | 命令 |
|------|------|------|
| CPU | UnixBench | `./Run` |
| CPU | sysbench | `sysbench cpu --threads=4 run` |
| CPU | CoreMark | `./coremark.exe` |
| 内存 | mbw / stream | `mbw 256` / `stream` |
| 存储 | fio | 见第 6 节 |
| 网络 | iperf3 | `iperf3 -c <ip> -P 4 -t 30` |
| GPU | glmark2 | `glmark2-es2-drm --off-screen` |

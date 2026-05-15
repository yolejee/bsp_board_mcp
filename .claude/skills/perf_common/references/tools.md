# 性能分析工具详细参考（通用 Linux）

本文件包含 perf、ftrace、trace-cmd、BPF、stress-ng 等工具的完整使用指南。

## 目录

1. [Linux perf 完整指南](#1-linux-perf-完整指南)
2. [Ftrace / trace-cmd / KernelShark](#2-ftrace--trace-cmd--kernelshark)
3. [Systrace（Android）](#3-systraceandroid)
4. [BPF / bpftrace / BCC](#4-bpf--bpftrace--bcc)
5. [stress-ng 压力测试](#5-stress-ng-压力测试)
6. [cyclictest 实时性测试](#6-cyclictest-实时性测试)
7. [常用内核配置速查](#7-常用内核配置速查)

---

## 1. Linux perf 完整指南

### 1.1 内核配置

```
CONFIG_PERF_EVENTS=y
CONFIG_HW_PERF_EVENTS=y
CONFIG_PERF_COUNTERS=y       # 部分架构需要
```

### 1.2 安装

```bash
# Debian/Ubuntu
apt install linux-tools-$(uname -r)

# 嵌入式交叉编译
cd <kernel_src>/tools/perf
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)
# 产物: tools/perf/perf → 推送到目标设备

# Android
mmm external/linux-tools-perf    # AOSP 编译
adb push perf /system/bin/
```

### 1.3 内核符号准备

```bash
# 关闭指针保护（否则看不到内核符号地址）
echo 0 > /proc/sys/kernel/kptr_restrict

# 确保 vmlinux 带调试信息
# CONFIG_DEBUG_INFO=y
```

### 1.4 常用命令

```bash
# 查看支持的事件
perf list

# 常见事件类别：
# Hardware:    cpu-cycles, instructions, cache-misses, branch-misses
# Software:    cpu-clock, page-faults, context-switches, task-clock
# HW cache:    L1-dcache-load-misses, dTLB-load-misses, iTLB-load-misses
# Tracepoint:  sched:sched_switch, irq:irq_handler_entry, ...

# ---- 实时热点 ----
perf top -d 2                            # 全系统
perf top -p $PID -d 2                    # 指定进程

# ---- 统计 ----
perf stat -p $PID                        # Ctrl+C 查看 IPC / cache miss
perf stat -e cache-misses,instructions,branch-misses -p $PID
perf stat -a -- sleep 10                 # 全系统统计 10 秒

# ---- 采集 Profile ----
perf record -g -p $PID -o perf.data      # -g: 抓调用栈
perf record -a -g -- sleep 10            # 全系统采样 10 秒
perf record -e cache-misses -p $PID      # 只抓特定事件

# ---- 分析报告 ----
perf report -i perf.data
perf report --vmlinux=/path/to/vmlinux --symfs=$SYMBOLS_DIR
perf annotate -i perf.data               # 源码/汇编级标注

# ---- 火焰图 ----
git clone https://github.com/brendangregg/FlameGraph.git
perf script -i perf.data | \
    FlameGraph/stackcollapse-perf.pl | \
    FlameGraph/flamegraph.pl > flame.svg

# ---- 调度分析 ----
perf sched record -- sleep 5
perf sched latency                       # 调度延迟统计
perf sched map                           # CPU 时间线
```

### 1.5 Perf Event 格式

| 格式 | 示例 | 说明 |
|------|------|------|
| symbolic | `perf stat -e cpu-cycles` | perf list 中的名称 |
| raw | `perf stat -e r11` | rNNN 十六进制 PMU 事件号 |
| 修饰符 | `-e cpu-cycles:k` | `:u` 用户态 `:k` 内核 `:h` hypervisor |
| 格式参数 | `-e PMU/event=0xa/` | 指定 PMU 设备 + 参数 |

### 1.6 Simpleperf（Android）

```bash
# Android 7.0+ 内置
simpleperf record -g -p $PID -o perf.data
simpleperf report -i perf.data

# NDK 预编译版本
# $ANDROID_NDK/simpleperf/
```

---

## 2. Ftrace / trace-cmd / KernelShark

### 2.1 内核配置

```
CONFIG_FTRACE=y
CONFIG_ENABLE_DEFAULT_TRACERS=y
CONFIG_DEBUG_FS=y
CONFIG_FUNCTION_TRACER=y
CONFIG_FUNCTION_GRAPH_TRACER=y
CONFIG_IRQSOFF_TRACER=y
CONFIG_PREEMPT_TRACER=y
CONFIG_SCHED_TRACER=y
```

### 2.2 trace-cmd（推荐方式）

```bash
# 安装
apt install trace-cmd

# 基础录制
trace-cmd record -e sched -e irq -e power -b 65536
trace-cmd report trace.dat > trace.txt

# 指定录制时间
trace-cmd record -e sched -b 65536 sleep 10

# 录制函数调用
trace-cmd record -p function_graph -g do_sys_open

# 指定进程
trace-cmd record -e sched -P $PID

# 可视化
kernelshark trace.dat     # GUI 分析工具
```

### 2.3 手动 Ftrace

```bash
# 挂载点
mount | grep debugfs       # /sys/kernel/debug
mount | grep tracefs       # /sys/kernel/tracing 或 /sys/kernel/debug/tracing

TRACE=/sys/kernel/debug/tracing

# 可用事件
ls $TRACE/events/
# sched/    irq/    power/    block/    mmc/    thermal/    clk/    gpio/    ...

# 标准抓取流程
echo 4096 > $TRACE/buffer_size_kb        # 缓冲区大小
echo global > $TRACE/trace_clock         # 多核时钟同步
echo 0 > $TRACE/options/overwrite        # 缓冲区满则停止
echo 1 > $TRACE/options/print-tgid       # 打印线程 ID（重要！）

# 启用需要的事件
echo 1 > $TRACE/events/sched/sched_switch/enable
echo 1 > $TRACE/events/sched/sched_wakeup/enable
echo 1 > $TRACE/events/sched/sched_waking/enable
echo 1 > $TRACE/events/irq/enable
echo 1 > $TRACE/events/power/cpu_frequency/enable

# 开始抓取
echo 1 > $TRACE/tracing_on
sleep 5
echo 0 > $TRACE/tracing_on

# 保存
cat $TRACE/trace > ftrace_output.txt
```

### 2.4 Catapult HTML 可视化

```bash
git clone https://github.com/catapult-project/catapult.git
./catapult/tracing/bin/trace2html ftrace_output.txt --output ftrace.html

# Chrome 打开 chrome://tracing → Load 文件
```

### 2.5 特殊 Tracer

```bash
# 关中断时长跟踪 — 找最长关中断时间
echo irqsoff > $TRACE/current_tracer
echo 1 > $TRACE/tracing_on
sleep 10
echo 0 > $TRACE/tracing_on
cat $TRACE/tracing_max_latency             # 最大关中断时长 μs

# 关抢占时长跟踪
echo preemptoff > $TRACE/current_tracer

# 唤醒延迟跟踪
echo wakeup > $TRACE/current_tracer

# 函数调用图
echo function_graph > $TRACE/current_tracer
echo do_sys_open > $TRACE/set_graph_function
```

### 2.6 用户态 Trace Marker

```bash
# 在用户程序中写入 trace_marker
echo "MY_EVENT_START" > /sys/kernel/debug/tracing/trace_marker
# ... 被测代码 ...
echo "MY_EVENT_END" > /sys/kernel/debug/tracing/trace_marker
```

C 代码：
```c
int fd = open("/sys/kernel/debug/tracing/trace_marker", O_WRONLY);
write(fd, "event_start\n", 12);
// ... 被测代码 ...
write(fd, "event_end\n", 10);
close(fd);
```

---

## 3. Systrace（Android）

### 3.1 使用方式

```bash
# SDK 工具
python systrace.py [options] [categories...]

# 示例
python systrace.py -b 32768 -t 15 -o output.html gfx input view sched freq
```

### 3.2 选项

| 选项 | 说明 |
|------|------|
| `-o FILE` | 输出文件 |
| `-t N` | 抓取 N 秒 |
| `-b N` | buffer 大小 (KB) |
| `-l` | 列出可用分类 |
| `-a APP` | 启用应用 tracing |
| `--boot` | 抓取开机过程 |

### 3.3 常用分类

```
gfx      - 图形           freq     - CPU 频率
input    - 输入           idle     - CPU 空闲
view     - 视图           load     - CPU 负载
sched    - 调度           disk     - 磁盘 IO
am       - Activity       memreclaim - 内存回收
wm       - 窗口           binder_driver - Binder
```

---

## 4. BPF / bpftrace / BCC

### 4.1 前提条件

```
# 内核 4.9+，推荐 5.x+
CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=y
CONFIG_HAVE_EBPF_JIT=y
```

### 4.2 bpftrace（一行命令式）

```bash
apt install bpftrace

# CPU profile（生成火焰图数据）
bpftrace -e 'profile:hz:99 { @[kstack] = count(); }' -c "sleep 10"

# 跟踪系统调用延迟
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @start[tid] = nsecs; }
              tracepoint:raw_syscalls:sys_exit /@start[tid]/ {
                  @usecs = hist((nsecs - @start[tid]) / 1000);
                  delete(@start[tid]);
              }'

# 跟踪文件打开
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'
```

### 4.3 BCC 工具集

```bash
apt install bpfcc-tools

# 常用工具
biolatency-bpfcc         # 块 IO 延迟直方图
biosnoop-bpfcc            # 每个 IO 请求详情
cachestat-bpfcc           # 页缓存命中率
ext4slower-bpfcc 1        # 超过 1ms 的 ext4 操作
memleak-bpfcc -p $PID     # 内存泄漏检测
offcputime-bpfcc -p $PID  # off-CPU 时间分析
runqlat-bpfcc             # 运行队列延迟
tcplife-bpfcc             # TCP 连接生命周期
funccount-bpfcc 'vfs_*'   # 函数调用计数
```

---

## 5. stress-ng 压力测试

```bash
apt install stress-ng

# CPU 压力（所有核心）
stress-ng --cpu 0 --timeout 60s

# CPU + 指定方法
stress-ng --cpu 4 --cpu-method matrixprod --timeout 60s

# 内存压力
stress-ng --vm 2 --vm-bytes 256M --timeout 60s

# IO 压力
stress-ng --io 4 --hdd 2 --hdd-bytes 1G --timeout 60s

# 综合压力（带指标输出）
stress-ng --cpu 4 --vm 2 --io 2 --timeout 120s --metrics

# 温度压力测试（观察温控行为）
stress-ng --cpu 0 --timeout 300s --thermalstat 5
```

---

## 6. cyclictest 实时性测试

### 6.1 安装

```bash
apt install rt-tests

# 交叉编译
git clone git://git.kernel.org/pub/scm/utils/rt-tests/rt-tests.git
make CROSS_COMPILE=aarch64-linux-gnu-
```

### 6.2 使用

```bash
# 标准测试
cyclictest -m -n -p 99 -t 4 -a -D 60
# -m: 锁定内存   -n: nanosleep   -p 99: RT 优先级
# -t 4: 4 线程   -a: 各核亲和    -D 60: 60 秒

# 单核测试
cyclictest -m -n -p 99 -t 1 -a 4 -D 30    # 只测 CPU4

# 带直方图输出
cyclictest -m -n -p 99 -t 4 -a -D 60 -h 100 > hist.txt
```

### 6.3 参考值

| 内核配置 | 典型最坏延迟 | 适用 |
|---------|-------------|------|
| `PREEMPT_NONE` | 1-10 ms | 服务器 |
| `PREEMPT_VOLUNTARY` | 0.5-2 ms | 桌面 |
| `PREEMPT` | 100-500 μs | 通用嵌入式 |
| `PREEMPT_RT` | 20-50 μs | 硬实时 |

---

## 7. 常用内核配置速查

### 性能分析

```
CONFIG_PERF_EVENTS=y                # perf 工具
CONFIG_HW_PERF_EVENTS=y             # 硬件性能计数器
CONFIG_FTRACE=y                     # ftrace 框架
CONFIG_ENABLE_DEFAULT_TRACERS=y     # 默认 tracer
CONFIG_DEBUG_FS=y                   # debugfs
CONFIG_FUNCTION_TRACER=y            # function tracer
CONFIG_FUNCTION_GRAPH_TRACER=y      # function_graph tracer
CONFIG_BLK_DEV_IO_TRACE=y          # blktrace
CONFIG_BPF=y                       # BPF
CONFIG_BPF_SYSCALL=y               # BPF 系统调用
```

### 实时性

```
CONFIG_PREEMPT=y                    # 完全抢占
CONFIG_PREEMPT_RT=y                 # RT 补丁（二选一）
CONFIG_HIGH_RES_TIMERS=y            # 高精度定时器
CONFIG_HZ=1000                      # 高频心跳
CONFIG_IRQSOFF_TRACER=y            # 关中断跟踪
CONFIG_PREEMPT_TRACER=y            # 关抢占跟踪
CONFIG_SCHED_TRACER=y              # 调度延迟跟踪
```

### 内存调试

```
CONFIG_SLUB_DEBUG=y                 # slab 调试
CONFIG_DEBUG_KMEMLEAK=y            # 内核内存泄漏检测
CONFIG_DEBUG_INFO=y                 # 调试信息
CONFIG_PAGE_OWNER=y                # 页面分配追踪
CONFIG_MEMCG=y                     # 内存 cgroup
# bootargs: page_owner=on          # 启用  页面追踪
```

### DVFS / Thermal

```
CONFIG_CPU_FREQ=y                   # CPUFreq
CONFIG_CPU_FREQ_GOV_PERFORMANCE=y   # performance governor
CONFIG_CPU_FREQ_GOV_USERSPACE=y     # userspace governor
CONFIG_CPU_FREQ_GOV_ONDEMAND=y      # ondemand governor
CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y     # schedutil governor
CONFIG_DEVFREQ_GOV_SIMPLE_ONDEMAND=y
CONFIG_THERMAL=y                    # Thermal 框架
CONFIG_THERMAL_GOV_POWER_ALLOCATOR=y
CONFIG_THERMAL_GOV_STEP_WISE=y
CONFIG_CPU_THERMAL=y                # CPU cooling device
CONFIG_DEVFREQ_THERMAL=y            # Devfreq cooling device
```

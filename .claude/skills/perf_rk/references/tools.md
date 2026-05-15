# 性能分析工具详细参考

本文件包含 perf、ftrace、systrace、streamline 等工具的完整使用指南。

## 目录

1. [Linux perf 完整指南](#1-linux-perf-完整指南)
2. [Ftrace 与 Catapult 图形化分析](#2-ftrace-与-catapult-图形化分析)
3. [Systrace 完整指南](#3-systrace-完整指南)
4. [Streamline (DS5) 指南](#4-streamline-ds5-指南)
5. [cyclictest 实时性测试](#5-cyclictest-实时性测试)
6. [常用内核配置速查](#6-常用内核配置速查)

---

## 1. Linux perf 完整指南

### 1.1 内核配置

```
CONFIG_PERF_EVENTS=y
CONFIG_HW_PERF_EVENTS=y
```

### 1.2 安装与交叉编译

**Android:**
```bash
source build/envsetup.sh && lunch
mmm external/linux-tools-perf
adb push perf /system/bin/
```

**Linux 交叉编译** — 需依次编译 4 个组件：

1. **zlib**: `CC=aarch64-linux-gnu-gcc ./configure --prefix=<dir> && make install`
2. **elfutils**: configure with `--host=aarch64-linux-gnu`，删除 Makefile 中 libcpu、libebl_i386、libebl_x86_64
3. **binutils**: configure with `--target=aarch64-linux-gnu --host=aarch64-linux-gnu`
4. **perf**: 修改 `Makefile.perf` 加入 EXTRA_CFLAGS 指向上述库路径
   ```makefile
   EXTRA_CFLAGS=-I<elfutils>/include -L<elfutils>/lib -I<binutils>/include -L<binutils>/lib
   WERROR=0
   NO_LIBPERL=1
   NO_LIBPYTHON=1
   ```
   编译：`make -f Makefile.perf perf ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8`

### 1.3 内核符号准备

```bash
# 关闭内核指针保护（否则看不到内核符号）
echo 0 > /proc/sys/kernel/kptr_restrict

# Android 准备符号表
bash art/tools/symbolize.sh

# 确保符号表路径与设备一致（关键！）
adb shell showmap <pid>
```

### 1.4 常用命令详解

```bash
# 查看支持的事件
perf list

# 常见事件类别：
# Hardware event:    cpu-cycles, instructions, cache-misses, branch-misses
# Software event:    cpu-clock, page-faults, context-switches
# Hardware cache:    L1-dcache-load-misses, dTLB-load-misses, iTLB-load-misses

# 实时热点
perf top -d 2
perf top -p $PID -d 2                    # 指定进程

# 进程统计
perf stat -p $PID                        # Ctrl+C 查看
perf stat -e cache-misses,instructions -p $PID

# 采集 profile
perf record -g -p $PID -o perf.data      # -g: 抓调用栈
perf record -e cache-misses -p $PID      # 只抓特定事件
perf record -a -g -- sleep 10            # 全系统采样 10 秒

# 分析报告
perf report -i perf.data
perf report --vmlinux=/path/to/vmlinux --symfs=$SYMBOLS_DIR

# 生成火焰图
git clone https://github.com/brendangregg/FlameGraph.git
perf script -i perf.data | \
    FlameGraph/stackcollapse-perf.pl | \
    FlameGraph/flamegraph.pl > flame.svg
```

### 1.5 Perf Event 格式

| 格式 | 示例 | 说明 |
|------|------|------|
| symbolic | `perf stat -e cpu-cycles` | perf list 中的名称 |
| raw | `perf stat -e r11` | rNNN 十六进制 PMU 事件号 |
| 修饰符 | `-e cpu-cycles:k` | `:u` 用户态 `:k` 内核 `:h` hypervisor `:I` 非idle `:p` 精确 |
| 格式参数 | `-e CCI_500/event=0xa,source=0xf/` | 指定 PMU 设备+参数 |

### 1.6 查看 PMU 设备

```bash
ls /sys/bus/event_source/devices/
ls /sys/bus/event_source/devices/CCI_500/format/
```

### 1.7 Simpleperf (Android 7.0+)

```bash
# 编译
mmma system/extras/simpleperf

# 预编译版本
git clone https://aosp.tuna.tsinghua.edu.cn/platform/prebuilts/simpleperf
```

优势：支持 APK 中共享库、`.gnu_debugdata`、纯静态。

---

## 2. Ftrace 与 Catapult 图形化分析

### 2.1 前提条件

内核配置：
```
CONFIG_FTRACE=y
CONFIG_ENABLE_DEFAULT_TRACERS=y
CONFIG_DEBUG_FS=y
```

验证：
```bash
mount | grep debugfs    # /sys/kernel/debug
mount | grep tracefs    # /sys/kernel/tracing 或 /sys/kernel/debug/tracing
```

### 2.2 可用 Events

```bash
ls /sys/kernel/debug/tracing/events/
# 常见分类：
# sched/    - 调度事件 (sched_switch, sched_wakeup, sched_waking)
# irq/      - 中断事件
# power/    - 电源/频率 (cpu_frequency, ddr_frequency, ddr_load)
# block/    - 块设备
# mmc/      - eMMC/SD
# ext4/     - ext4 文件系统
# f2fs/     - f2fs 文件系统
# thermal/  - 温控
# clk/      - 时钟
# gpio/     - GPIO
# workqueue/ - 工作队列
```

### 2.3 标准抓取脚本

```bash
#!/bin/sh
# atrace.sh <output_file> <duration_seconds>

# 配置
echo 4096 > /sys/kernel/debug/tracing/buffer_size_kb
echo global > /sys/kernel/debug/tracing/trace_clock      # 多核时钟同步
echo 0 > /sys/kernel/debug/tracing/options/overwrite      # 缓冲区满则停止
echo 1 > /sys/kernel/debug/tracing/options/print-tgid     # 必须！打印线程 ID

# 启用事件
echo 1 > /sys/kernel/debug/tracing/events/sched/sched_switch/enable
echo 1 > /sys/kernel/debug/tracing/events/sched/sched_wakeup/enable
echo 1 > /sys/kernel/debug/tracing/events/sched/sched_waking/enable
echo 1 > /sys/kernel/debug/tracing/events/sched/sched_blocked_reason/enable
echo 1 > /sys/kernel/debug/tracing/events/irq/enable

# RK 自定义事件（可选）
echo 1 > /sys/kernel/debug/tracing/events/power/ddr_frequency/enable
echo 1 > /sys/kernel/debug/tracing/events/power/ddr_load/enable

# 开始抓取
echo 1 > /sys/kernel/debug/tracing/tracing_on
sleep $2
echo 0 > /sys/kernel/debug/tracing/tracing_on

# 保存
cat /sys/kernel/debug/tracing/trace > $1
```

用法：`./atrace.sh /tmp/my_trace.txt 5`

### 2.4 注意事项

- `buffer_size_kb` 过小会丢事件，根据 event 数量和持续时间调整
- `print-tgid` 必须打开，否则 Catapult 无法按线程分组显示
- `trace_clock=global` 确保多核时间戳一致
- `overwrite=0` 避免缓冲区循环覆盖丢失早期数据

### 2.5 生成 HTML 图形化

```bash
git clone https://github.com/catapult-project/catapult.git
./catapult/tracing/bin/trace2html my_trace.txt --output my_trace.html

# Chrome 打开 chrome://tracing → Load 文件
# 或直接打开 my_trace.html
```

### 2.6 用户态代码插桩

**C++ (RAII):**
```cpp
#include "atrace.h"
void myFunc() {
    ATRACE_NAME("myFunc_processing");    // 自动在作用域结束时关闭
    // ... 代码 ...
}
```

**C:**
```c
#include "trace.h"
void myFunc() {
    atrace_begin_body("myFunc_processing");
    // ... 代码 ...
    atrace_end_body();    // 每个返回路径都必须调用！
}
```

底层通过写 `/sys/kernel/debug/tracing/trace_marker` 实现。

### 2.7 内核自定义 Event（DDR 变频示例）

在 `include/trace/events/power.h` 中声明：
```c
DECLARE_EVENT_CLASS(ddr_freq, ...)
DEFINE_EVENT(ddr_freq, ddr_frequency, TP_PROTO(unsigned int state), TP_ARGS(state));
```

在驱动（如 `drivers/devfreq/rockchip_dmc.c`）中调用：
```c
#include <trace/events/power.h>
trace_ddr_frequency(*freq);
```

---

## 3. Systrace 完整指南

### 3.1 获取 Systrace

```bash
# 方法一：Android SDK
/path/to/sdk/platform-tools/systrace/

# 方法二：Android 源码
/path/to/android/external/chromium-trace/

# 方法三：Android Studio → Profiler
```

### 3.2 命令格式

```bash
python systrace.py [options] [categories...]

# 示例
python systrace.py -b 32768 -t 15 -o output.html gfx input view sched freq
```

### 3.3 选项说明

| 选项 | 说明 |
|------|------|
| `-o FILE` | 输出文件 |
| `-t N` | 抓取 N 秒 |
| `-b N` | trace buffer 大小 (KB) |
| `-l` | 列出可用分类 |
| `-k KFUNCS` | 指定 kernel 函数 (逗号分隔) |
| `-a APP_NAME` | 启用应用级 tracing |
| `--from-file=FILE` | 从文件离线分析 |
| `--boot` | 重启设备并抓取引导过程 |
| `-e SERIAL` | 指定设备序列号 |

### 3.4 可用分类

```
gfx        - 图形
input      - 输入
view       - 视图
webview    - WebView
wm         - 窗口管理
am         - Activity 管理
sm         - 同步管理
audio      - 音频
video      - 视频
camera     - 摄像头
hal        - 硬件抽象层
app        - 应用
res        - 资源加载
dalvik     - Dalvik VM
power      - 电源
sched      - CPU 调度
freq       - CPU 频率
idle       - CPU 空闲
load       - CPU 负载
memreclaim - 内存回收
disk       - 磁盘 IO
binder_driver - Binder 驱动
binder_lock   - Binder 锁
```

### 3.5 分析方法

Chrome 打开 HTML → 四种操作模式：

1. **时间线模式**：拖动查看不同时间段
2. **选择模式**：点击/框选区域查看详情
3. 查看 render 线程和绘制间隔
4. 找 CPU 频率与调度对应关系

---

## 4. Streamline (DS5) 指南

### 4.1 准备

- 下载 DS5 5.26+（需 license，可申请 30 天试用）
- 连接方式：ADB 或网络
- 需要 root 权限
- 需要固件匹配的符号表

### 4.2 启动 gatord

```bash
adb push /path/to/ds5/sw/streamline/bin/arm64/gatord /data/local/
adb shell
cd /data/local/
chmod +x gatord
./gatord &
```

### 4.3 分析视图

| 视图 | 用途 |
|------|------|
| **Heat Map** | 找热点线程，看 CPU 占有率、miss rate |
| **Core Map** | 线程在各时刻跑在哪个 core |
| **Cluster Map** | 线程在大核/小核的分布 |
| **Samples** | 每个时间片内函数 CPU 占比 |
| **Processes** | 进程级 CPU 占比 |
| **Functions** | 全局函数热点排序 |
| **Call Paths** | 函数调用关系 |

优势：丰富的硬件计数器支持（cache、bus、GPU 内部状态），perf 无法涵盖的硬件级分析。

---

## 5. cyclictest 实时性测试

### 5.1 安装

```bash
apt-get install rt-tests

# 或者交叉编译
git clone git://git.kernel.org/pub/scm/utils/rt-tests/rt-tests.git
make CROSS_COMPILE=aarch64-linux-gnu-
```

### 5.2 使用

```bash
# 标准测试
cyclictest -m -n -p 99 -t 4 -a -D 60
# -m: 锁定内存 (mlockall)
# -n: 使用 nanosleep
# -p 99: RT 优先级 99 (最高)
# -t 4: 4 个线程
# -a: 亲和到各 CPU
# -D 60: 运行 60 秒

# 测特定 CPU
cyclictest -m -n -p 99 -t 1 -a 4 -D 30   # 只测 CPU4

# 输出关键指标：Min / Avg / Max (微秒)
# 关注 Max 列 — 即最坏延迟
```

### 5.3 标准内核 vs RT 内核

| 指标 | 标准内核 | PREEMPT_RT |
|------|---------|------------|
| 典型最坏延迟 | 100-500 μs | 20-50 μs |
| 适用场景 | 通用/软实时 | 硬实时 |

---

## 6. 常用内核配置速查

### 性能分析相关

```
CONFIG_PERF_EVENTS=y                # perf 工具
CONFIG_HW_PERF_EVENTS=y             # 硬件性能计数器
CONFIG_FTRACE=y                     # ftrace 框架
CONFIG_ENABLE_DEFAULT_TRACERS=y     # 默认 tracer
CONFIG_DEBUG_FS=y                   # debugfs
CONFIG_FUNCTION_TRACER=y            # function tracer
CONFIG_BLK_DEV_IO_TRACE=y          # blktrace / ioblame
CONFIG_DEVMEM=y                     # /dev/mem (DDR 带宽工具)
```

### 实时性相关

```
CONFIG_PREEMPT=y                    # 完全抢占
CONFIG_HZ=1000                      # 高频心跳
CONFIG_IRQSOFF_TRACER=y            # 关中断时长 tracer
CONFIG_PREEMPT_TRACER=y            # 关抢占时长 tracer
CONFIG_SCHED_TRACER=y              # 调度延迟 tracer
```

### 内存调试相关

```
CONFIG_SLUB_SYSFS=y                # slab sysfs 接口
CONFIG_SLUB_DEBUG=y                # slab 调试
# bootargs: memblock=debug         # memblock 调试信息
```

### DVFS/Thermal 相关

```
CONFIG_CPU_FREQ=y
CONFIG_CPU_FREQ_DEFAULT_GOV_INTERACTIVE=y   # 或 schedutil
CONFIG_CPU_FREQ_GOV_PERFORMANCE=y
CONFIG_CPU_FREQ_GOV_USERSPACE=y
CONFIG_DEVFREQ_GOV_SIMPLE_ONDEMAND=y
CONFIG_ARM_ROCKCHIP_DMC_DEVFREQ=y
CONFIG_THERMAL=y
CONFIG_THERMAL_GOV_POWER_ALLOCATOR=y
CONFIG_ROCKCHIP_THERMAL=y
```

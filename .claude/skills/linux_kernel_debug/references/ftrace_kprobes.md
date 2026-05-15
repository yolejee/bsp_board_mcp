# ftrace / kprobes / 动态追踪详细参考

## 目录

1. [ftrace 框架架构](#1-ftrace-框架架构)
2. [所有 Tracer 类型](#2-所有-tracer-类型)
3. [Trace Events 详解](#3-trace-events-详解)
4. [高级过滤与触发器](#4-高级过滤与触发器)
5. [kprobes 完整参考](#5-kprobes-完整参考)
6. [trace-cmd 与 KernelShark](#6-trace-cmd-与-kernelshark)
7. [BPF / bpftrace](#7-bpf--bpftrace)
8. [实用追踪场景](#8-实用追踪场景)

---

## 1. ftrace 框架架构

### 1.1 核心概念

```
用户空间
    ↓ (通过 tracefs/debugfs)
ftrace 框架
    ├── ring buffer (per-CPU 环形缓冲区)
    ├── tracer 插件 (function, function_graph, 等)
    ├── trace events (内核预定义的追踪点)
    └── kprobes/uprobes (动态探针)
```

### 1.2 关键文件路径

```bash
TRACE=/sys/kernel/debug/tracing
# 或 /sys/kernel/tracing (5.x+ 推荐路径)

$TRACE/
├── current_tracer           # 当前使用的 tracer
├── available_tracers        # 可用的 tracer 列表
├── trace                    # 追踪结果 (人类可读)
├── trace_pipe               # 实时流式读取 (消耗后不保留)
├── tracing_on               # 开关 (1=开, 0=关)
├── buffer_size_kb           # per-CPU 缓冲区大小
├── set_ftrace_filter        # 函数白名单
├── set_ftrace_notrace       # 函数黑名单
├── set_ftrace_pid           # PID 过滤
├── set_graph_function       # function_graph 追踪入口
├── available_filter_functions  # 所有可追踪函数列表
├── available_events         # 所有可用 trace event
├── kprobe_events            # kprobe 事件定义
├── uprobe_events            # uprobe 事件定义
└── events/                  # trace event 子系统目录
    ├── sched/               # 调度事件
    ├── irq/                 # 中断事件
    ├── i2c/                 # I2C 事件
    └── ...
```

---

## 2. 所有 Tracer 类型

| Tracer | 功能 | 适用场景 |
|--------|------|---------|
| `nop` | 无追踪 (只用 trace events) | 只追踪事件时 |
| `function` | 记录函数调用 | 查看函数调用序列 |
| `function_graph` | 记录函数调用和返回 (含耗时) | 查看函数调用层次和耗时 |
| `blk` | 块设备 IO 追踪 | IO 调试 |
| `hwlat` | 硬件延迟检测 | SMI/NMI 延迟检测 |
| `irqsoff` | 最长中断关闭时间 | 实时性调试 |
| `preemptoff` | 最长抢占关闭时间 | 实时性调试 |
| `preemptirqsoff` | irqsoff + preemptoff | 综合实时性 |
| `wakeup` | 最高优先级任务唤醒延迟 | RT 调度延迟 |
| `wakeup_rt` | RT 任务唤醒延迟 | RT 实时性 |

### 2.1 function_graph 详解

```bash
echo function_graph > $TRACE/current_tracer

# 控制追踪深度
echo 5 > $TRACE/max_graph_depth    # 最多深入 5 层

# 指定追踪入口函数
echo i2c_transfer > $TRACE/set_graph_function

# 输出示例:
#  | i2c_transfer() {
#  |   i2c_adapter_lock_bus() {
#  |     rt_mutex_lock() {
#  |       ...
#  |     } /* rt_mutex_lock = 1.234 us */
#  |   } /* i2c_adapter_lock_bus = 2.345 us */
#  | } /* i2c_transfer = 15.678 us */
```

### 2.2 irqsoff tracer

```bash
echo irqsoff > $TRACE/current_tracer
echo 1 > $TRACE/tracing_on
# ... 运行一段时间 ...
echo 0 > $TRACE/tracing_on
cat $TRACE/trace    # 显示最长中断关闭路径

# tracing_max_latency 保存最大延迟
cat $TRACE/tracing_max_latency
echo 0 > $TRACE/tracing_max_latency    # 清零重新测量
```

---

## 3. Trace Events 详解

### 3.1 常用事件子系统

| 子系统 | 典型事件 | 用途 |
|--------|---------|------|
| `sched` | `sched_switch`, `sched_wakeup`, `sched_process_exec` | 调度分析 |
| `irq` | `irq_handler_entry`, `irq_handler_exit`, `softirq_entry` | 中断分析 |
| `block` | `block_rq_issue`, `block_rq_complete` | IO 分析 |
| `i2c` | `i2c_read`, `i2c_write`, `i2c_result` | I2C 调试 |
| `spi` | `spi_transfer_start`, `spi_transfer_stop` | SPI 调试 |
| `gpio` | `gpio_direction`, `gpio_value` | GPIO 调试 |
| `clk` | `clk_enable`, `clk_disable`, `clk_set_rate` | 时钟调试 |
| `regulator` | `regulator_enable`, `regulator_set_voltage` | 电源调试 |
| `workqueue` | `workqueue_execute_start`, `workqueue_execute_end` | 工作队列分析 |
| `timer` | `timer_start`, `timer_cancel` | 定时器调试 |
| `signal` | `signal_generate`, `signal_deliver` | 信号调试 |
| `kmem` | `kmalloc`, `kfree`, `mm_page_alloc` | 内存分配追踪 |

### 3.2 事件过滤

```bash
# 基于事件字段的过滤
echo 'comm == "my_app"' > $TRACE/events/sched/sched_switch/filter
echo 'next_pid == 1234' > $TRACE/events/sched/sched_switch/filter
echo 'bytes_req > 1024' > $TRACE/events/kmem/kmalloc/filter

# 逻辑组合
echo 'pid == 100 && bytes_req >= 4096' > $TRACE/events/kmem/kmalloc/filter

# 清除过滤器
echo 0 > $TRACE/events/sched/sched_switch/filter
```

---

## 4. 高级过滤与触发器

### 4.1 trace_printk

```c
// 在内核代码中直接写入 ftrace 缓冲区 (比 printk 快得多)
trace_printk("value = %d\n", val);

// 注意: 仅用于调试，不要提交到主线
// 编译时会有 "TRACE_PRINTK" 警告提醒你移除
```

### 4.2 Histogram Trigger

```bash
# 按 PID 统计调度次数
echo 'hist:key=next_pid:val=hitcount:sort=hitcount.descending' > \
    $TRACE/events/sched/sched_switch/trigger

# 按函数统计调用延迟
echo 'hist:key=common_pid.execname:vals=lat:sort=lat' > \
    $TRACE/events/sched/sched_wakeup_new/trigger

# 查看 histogram 结果
cat $TRACE/events/sched/sched_switch/hist

# 清除
echo '!hist:key=next_pid' > $TRACE/events/sched/sched_switch/trigger
```

### 4.3 Stacktrace Trigger

```bash
# 当事件发生时自动抓取内核栈
echo 'stacktrace' > $TRACE/events/kmem/kmalloc/trigger
echo 'stacktrace if bytes_req > 65536' > $TRACE/events/kmem/kmalloc/trigger

# 当事件发生时快照
echo 'snapshot' > $TRACE/events/sched/sched_switch/trigger
```

### 4.4 函数追踪的栈信息

```bash
# 每次函数调用都记录栈
echo 1 > $TRACE/options/func_stack_trace
echo my_func > $TRACE/set_ftrace_filter
echo function > $TRACE/current_tracer
```

---

## 5. kprobes 完整参考

### 5.1 kprobe_events 语法

```bash
# 格式:
# p[:[GRP/]EVENT] SYM[+offs]|MEMADDR [FETCHARGS]  # kprobe
# r[:[GRP/]EVENT] SYM[+offs]|MEMADDR [FETCHARGS]  # kretprobe

# FETCHARGS 语法:
# %REG          - 寄存器 (架构相关)
# @SYM          - 全局变量
# $stack        - 栈地址
# $retval       - 返回值 (仅 kretprobe)
# $comm         - 当前进程名
# +|-OFFS(REG)  - 寄存器间接寻址
# +|-OFFS(+|-OFFS(REG))  - 多级间接
# \IMM          - 立即数
```

### 5.2 架构寄存器对照 (函数参数)

| 参数 | ARM64 | x86_64 | ARM32 |
|------|-------|--------|-------|
| arg1 | `%x0` | `%di` | `%r0` |
| arg2 | `%x1` | `%si` | `%r1` |
| arg3 | `%x2` | `%dx` | `%r2` |
| arg4 | `%x3` | `%cx` | `%r3` |
| arg5 | `%x4` | `%r8` | 栈 |
| arg6 | `%x5` | `%r9` | 栈 |
| arg7 | `%x6` | 栈 | 栈 |
| arg8 | `%x7` | 栈 | 栈 |
| 返回值 | `%x0` | `%ax` | `%r0` |

### 5.3 实用示例

```bash
# 追踪 open 系统调用的文件名
echo 'p:my_open do_sys_openat2 filename=+0(%x1):string flags=%x2:u32' > $TRACE/kprobe_events
echo 1 > $TRACE/events/kprobes/my_open/enable

# 追踪 kmalloc 参数和返回值
echo 'p:my_kmalloc __kmalloc size=%x0:u64 flags=%x1:x32' > $TRACE/kprobe_events
echo 'r:my_kret __kmalloc ret=$retval:x64' >> $TRACE/kprobe_events
echo 1 > $TRACE/events/kprobes/enable

# 追踪 i2c_transfer 的 adapter 和消息数量
echo 'p:my_i2c i2c_transfer num=%x2:u32' > $TRACE/kprobe_events

# 追踪结构体成员 (例: i2c_msg->addr)
echo 'p:i2c_msg_addr i2c_transfer addr=+0(%x1):u16' > $TRACE/kprobe_events

# 清理
echo > $TRACE/kprobe_events
```

---

## 6. trace-cmd 与 KernelShark

### 6.1 trace-cmd 基本用法

```bash
# 录制
trace-cmd record -e sched -e irq sleep 5
trace-cmd record -p function -l 'i2c_*' sleep 3
trace-cmd record -p function_graph -g i2c_transfer sleep 2

# 分析
trace-cmd report
trace-cmd report --cpu 0         # 只看 CPU0
trace-cmd report -F 'sched_switch: prev_comm ~ "*my_app*"'

# 拆分
trace-cmd split -o split trace.dat -c 0   # 按 CPU 拆分

# 实时流式
trace-cmd stream -e sched_switch
```

### 6.2 trace-cmd 高级录制

```bash
# 带栈追踪
trace-cmd record -e kmem:kmalloc -T sleep 5    # -T 加栈

# 多个 instance (隔离不同追踪)
trace-cmd record -B irq_trace -e irq &
trace-cmd record -B sched_trace -e sched &

# 远程录制 (嵌入式常用)
# 目标板:
trace-cmd listen -p 6789
# 主机:
trace-cmd record -e sched -N 192.168.1.100:6789
```

### 6.3 KernelShark (图形化分析)

```bash
# 安装
apt install kernelshark

# 打开 trace 文件
kernelshark trace.dat

# 功能:
# - 时间线图形化显示 CPU/进程切换
# - 放大缩小特定时间段
# - 按进程/CPU/事件过滤
# - 搜索特定模式
```

---

## 7. BPF / bpftrace

### 7.1 bpftrace 常用单行命令

```bash
# 追踪系统调用
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# 函数延迟分布
bpftrace -e 'kprobe:vfs_read { @start[tid] = nsecs; }
             kretprobe:vfs_read /@start[tid]/ { @us = hist((nsecs - @start[tid]) / 1000); delete(@start[tid]); }'

# 调度延迟分布
bpftrace -e 'tracepoint:sched:sched_wakeup { @qtime[args->pid] = nsecs; }
             tracepoint:sched:sched_switch /@qtime[args->next_pid]/ { @us = hist((nsecs - @qtime[args->next_pid]) / 1000); delete(@qtime[args->next_pid]); }'

# 每秒中断统计
bpftrace -e 'tracepoint:irq:irq_handler_entry { @[args->name] = count(); } interval:s:1 { print(@); clear(@); }'

# 页面错误栈
bpftrace -e 'tracepoint:exceptions:page_fault_user { @[kstack, ustack, comm] = count(); }'
```

### 7.2 BCC 工具集

```bash
# 常用 BCC 工具
funccount -p $PID 'i2c_*'       # 统计函数调用次数
funclatency -p $PID i2c_transfer # 函数延迟分布
trace 'do_sys_openat2 "%s", arg2@user' # 追踪系统调用
argdist -C 'p::__kmalloc(size_t size):size_t:size' # 参数分布
stackcount -p $PID i2c_transfer  # 调用栈统计
```

---

## 8. 实用追踪场景

### 8.1 追踪设备 probe 过程

```bash
# 方法 1: ftrace
echo function_graph > $TRACE/current_tracer
echo '*_probe' > $TRACE/set_graph_function
echo 1 > $TRACE/tracing_on
# 加载模块
modprobe my_driver
echo 0 > $TRACE/tracing_on

# 方法 2: trace events
echo 1 > $TRACE/events/bus/bus_add_device/enable
echo 1 > $TRACE/events/bus/driver_bound/enable
modprobe my_driver
cat $TRACE/trace
```

### 8.2 追踪中断处理

```bash
trace-cmd record -e irq -e softirq sleep 5
trace-cmd report | grep -A2 'irq_handler_entry'
```

### 8.3 追踪内存分配

```bash
echo 1 > $TRACE/events/kmem/kmalloc/enable
echo 1 > $TRACE/events/kmem/kfree/enable
echo 'bytes_req > 4096' > $TRACE/events/kmem/kmalloc/filter
cat $TRACE/trace
```

### 8.4 追踪文件 IO

```bash
trace-cmd record -e block -e writeback sleep 10
trace-cmd report -F 'block_rq_issue: rwbs ~ "*W*"'    # 只看写操作
```

### 8.5 重置 ftrace 状态

```bash
# 完整重置 ftrace 到干净状态
echo nop > $TRACE/current_tracer
echo > $TRACE/set_ftrace_filter
echo > $TRACE/set_ftrace_notrace
echo > $TRACE/set_ftrace_pid
echo > $TRACE/kprobe_events
echo 0 > $TRACE/events/enable
echo > $TRACE/trace              # 清空缓冲区
echo 1 > $TRACE/tracing_on
```

---
name: linux_kernel_debug
description: "通用 Linux 内核调试技能，不限于任何特定 SoC 平台。用于指导 printk/dmesg/dynamic debug 日志调试、Oops/Panic 崩溃分析、ftrace/kprobes 动态追踪、kgdb/kdb 交互调试、crash/kdump 事后分析、KASAN/KMEMLEAK/SLUB debug 内存调试、lockdep/hung_task 锁调试、/proc 和 /sys 调试接口使用。触发关键词包括但不限于：内核调试、kernel debug、printk、dmesg、oops、panic、call trace、backtrace、stack dump、ftrace、kprobes、trace-cmd、function_graph、kgdb、kdb、crash dump、kdump、ramdump、vmcore、KASAN、KMEMLEAK、SLUB、lockdep、hung task、soft lockup、hard lockup、RCU stall、dynamic debug、dev_dbg、SysRq、magic sysrq、addr2line、decode_stacktrace、内核崩溃、死机分析、内存泄漏、内存越界、死锁检测、调度延迟。当用户描述任何 Linux 内核层面的调试问题（即使没有明确说'内核调试'，只要涉及 dmesg 报错、kernel panic、call trace、内核模块调试、驱动 probe 失败的内核侧分析等），都应触发本技能。"
---

# Linux 内核调试技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| 内核崩溃 (Oops/Panic) | §3 |
| 不知道问题在哪 / 想追踪内核行为 | §4 ftrace |
| 想在内核函数上加断点 | §5 kprobes 或 §6 kgdb |
| 内存越界 / 释放后使用 / 泄漏 | §7 |
| 死锁 / soft lockup / hung task | §8 |
| 崩溃后的 vmcore 分析 | §9 crash |
| 看日志 / 开调试打印 | §2 printk |
| 需要配哪些内核 CONFIG | §11 |

---

## 1. 诊断决策树

```
问题现象
├── 内核直接崩溃 (Oops / Panic / 死机)
│   ├── 有串口日志 → §3 分析 Oops
│   ├── 有 kdump vmcore → §9 crash 分析
│   └── 什么都没有 → §10.3 pstore / last_kmsg
│
├── 系统卡住 (无响应但未崩溃)
│   ├── 能 SysRq → §10.2 SysRq-t/w 抓栈
│   ├── soft lockup / RCU stall → §8
│   └── hung task → §8.2
│
├── 功能异常 (设备不工作 / 行为不对)
│   ├── 先看日志 → §2 dmesg + dynamic debug
│   ├── 追踪内核执行路径 → §4 ftrace
│   └── 在特定函数加断点 → §5 kprobes
│
├── 内存问题 (泄漏 / 越界 / OOM)
│   ├── 越界/use-after-free → §7.1 KASAN
│   ├── 内存泄漏 → §7.2 KMEMLEAK
│   └── slab 异常 → §7.3 SLUB debug
│
└── 性能 / 延迟问题
    └── 参考 perf_common / perf_rk 技能
```

---

## 2. 内核日志 (printk / dmesg / dynamic debug)

### 2.1 dmesg 基础

```bash
dmesg                              # 全部内核日志
dmesg -T                           # 带人类可读时间戳
dmesg -l err,warn                  # 只看 error + warning
dmesg -w                           # 持续监听 (类似 tail -f)
dmesg -c                           # 读取并清空缓冲区
dmesg | grep -i "error\|fail\|warn\|oops\|panic\|bug"
```

### 2.2 printk 日志级别

| 级别 | 宏 | 含义 | 数值 |
|------|-----|------|------|
| KERN_EMERG | `pr_emerg()` | 系统不可用 | 0 |
| KERN_ALERT | `pr_alert()` | 需要立即处理 | 1 |
| KERN_CRIT | `pr_crit()` | 严重错误 | 2 |
| KERN_ERR | `pr_err()` | 错误 | 3 |
| KERN_WARNING | `pr_warn()` | 警告 | 4 |
| KERN_NOTICE | `pr_notice()` | 正常但重要 | 5 |
| KERN_INFO | `pr_info()` | 信息 | 6 |
| KERN_DEBUG | `pr_debug()` | 调试 (需开启) | 7 |

```bash
# 查看/修改控制台日志级别
cat /proc/sys/kernel/printk          # current default minimum boot_default
echo 8 > /proc/sys/kernel/printk     # 显示所有级别
```

### 2.3 Dynamic Debug (动态调试)

无需重编译即可开关 `pr_debug()` / `dev_dbg()` 输出：

```bash
# 查看所有可控制的调试点
cat /sys/kernel/debug/dynamic_debug/control

# 开启某个文件的所有 pr_debug
echo 'file drivers/i2c/i2c-core-base.c +p' > /sys/kernel/debug/dynamic_debug/control

# 开启某个函数
echo 'func i2c_transfer +p' > /sys/kernel/debug/dynamic_debug/control

# 开启某个模块
echo 'module i2c_dev +p' > /sys/kernel/debug/dynamic_debug/control

# 添加函数名+行号到输出
echo 'file xxx.c +fpl' > /sys/kernel/debug/dynamic_debug/control
# +f=函数名 +l=行号 +m=模块名 +t=线程ID +p=开启打印
```

> printk 子系统详细参考（rate limiting、printk_once、日志缓冲区调参等）见 `references/printk_dynamic_debug.md`

---

## 3. Oops / Panic 分析

### 3.1 Oops 信息结构

内核 Oops 消息通常包含以下关键部分：

```
[  123.456789] Unable to handle kernel NULL pointer dereference at virtual address 0000000000000010
[  123.456790] Mem abort info:                        ← 异常类型
[  123.456791]   ESR = 0x96000006
[  123.456792] pc : my_driver_read+0x28/0x100 [my_module]   ← 出错的指令地址
[  123.456793] lr : my_driver_open+0x44/0x80 [my_module]    ← 返回地址
[  123.456794] sp : ffffffc011b83d00
[  123.456795] ...
[  123.456800] Call trace:                            ← 调用栈
[  123.456801]  my_driver_read+0x28/0x100 [my_module]
[  123.456802]  vfs_read+0xc8/0x1e4
[  123.456803]  ksys_read+0x6c/0xdc
[  123.456804]  __arm64_sys_read+0x1c/0x28
```

### 3.2 关键分析步骤

```bash
# 1. 用 addr2line 定位源码行号
aarch64-linux-gnu-addr2line -e vmlinux -fip my_driver_read+0x28

# 2. 用 GDB 反汇编
aarch64-linux-gnu-gdb vmlinux
(gdb) list *(my_driver_read+0x28)
(gdb) disassemble my_driver_read

# 3. 用内核脚本自动解析
./scripts/decode_stacktrace.sh vmlinux < oops.log

# 4. 外部模块地址解析 (需 .ko 文件)
aarch64-linux-gnu-addr2line -e my_module.ko -fip 0x28

# 5. faddr2line (内核内置脚本，更方便)
./scripts/faddr2line vmlinux my_driver_read+0x28
```

### 3.3 常见 Oops 类型速查

| 关键字 | 含义 | 常见原因 |
|--------|------|---------|
| `NULL pointer dereference` | 空指针解引用 | 未检查返回值、未初始化指针 |
| `unable to handle kernel paging` | 非法内存访问 | 越界、use-after-free、野指针 |
| `BUG: unable to handle kernel` | 内核 BUG() 触发 | 代码断言失败 |
| `Kernel panic - not syncing` | 不可恢复错误 | 中断上下文崩溃、init 进程退出 |
| `BUG: scheduling while atomic` | 原子上下文中睡眠 | 自旋锁内调用了可睡眠函数 |
| `Call trace:` 后有 `[<0>]` | 栈帧损坏 | 栈溢出 |

> Oops/Panic 深入分析方法、ARM64 寄存器解读、常见崩溃模式详解见 `references/oops_panic_crash.md`

---

## 4. ftrace 动态追踪

### 4.1 基本用法

```bash
TRACE=/sys/kernel/debug/tracing

# 查看可用 tracer
cat $TRACE/available_tracers

# function tracer：追踪所有内核函数调用
echo function > $TRACE/current_tracer
echo 1 > $TRACE/tracing_on
# ... 复现问题 ...
echo 0 > $TRACE/tracing_on
cat $TRACE/trace

# function_graph：带调用深度的函数图
echo function_graph > $TRACE/current_tracer
echo i2c_transfer > $TRACE/set_graph_function   # 只追踪此函数及其子调用
echo 1 > $TRACE/tracing_on
```

### 4.2 过滤与控制

```bash
# 只追踪特定函数
echo 'i2c_*' > $TRACE/set_ftrace_filter
echo '*spi*' >> $TRACE/set_ftrace_filter        # 追加

# 排除函数
echo 'rcu_*' > $TRACE/set_ftrace_notrace

# 只追踪特定 PID
echo $PID > $TRACE/set_ftrace_pid

# 追踪特定模块的函数
echo ':mod:my_module' > $TRACE/set_ftrace_filter
```

### 4.3 Trace Events (推荐方式)

```bash
# 列出所有可用事件
cat $TRACE/available_events

# 开启调度事件
echo 1 > $TRACE/events/sched/sched_switch/enable
echo 1 > $TRACE/events/sched/sched_wakeup/enable

# 开启中断事件
echo 1 > $TRACE/events/irq/enable

# 开启某个子系统的全部事件
echo 1 > $TRACE/events/i2c/enable

# 使用 trace-cmd (推荐，更方便)
trace-cmd record -e sched -e irq -e i2c sleep 5
trace-cmd report
```

### 4.4 追踪函数参数 (基于 trace event)

```bash
# 启用 kprobe event 追踪函数参数
echo 'p:myprobe i2c_transfer adapter=%x0 msgs=%x1 num=%x2' > $TRACE/kprobe_events
echo 1 > $TRACE/events/kprobes/myprobe/enable
```

> ftrace 完整参考（实例过滤、栈追踪、histogram trigger、trace-cmd 高级用法等）见 `references/ftrace_kprobes.md`

---

## 5. kprobes / kretprobes

### 5.1 使用 kprobe_events 接口

```bash
TRACE=/sys/kernel/debug/tracing

# 在函数入口加探针
echo 'p:my_entry_probe do_sys_open filename=+0(%x1):string flags=%x2' > $TRACE/kprobe_events

# 在函数返回加探针 (kretprobe)
echo 'r:my_ret_probe do_sys_open ret=$retval' >> $TRACE/kprobe_events

# 启用
echo 1 > $TRACE/events/kprobes/my_entry_probe/enable
echo 1 > $TRACE/events/kprobes/my_ret_probe/enable

# 查看结果
cat $TRACE/trace

# 清理
echo '-:my_entry_probe' >> $TRACE/kprobe_events
echo '-:my_ret_probe' >> $TRACE/kprobe_events
```

> kprobes 详细参考（参数寄存器对照、fetch args 语法、bpftrace 用法等）见 `references/ftrace_kprobes.md`

### 5.2 eBPF / bpftrace (现代追踪)

eBPF 是内核内置的沙箱虚拟机，允许用户空间注入安全的追踪/过滤程序，无需编译内核模块。
内核需开启: `CONFIG_BPF=y CONFIG_BPF_SYSCALL=y CONFIG_BPF_JIT=y CONFIG_BPF_EVENTS=y CONFIG_DEBUG_INFO_BTF=y`

**bpftrace 常用单行命令** (需交叉编译 aarch64 版):

```bash
bpftrace -e 'kprobe:i2c_transfer { @[kstack(3)] = count(); }'           # 函数调用计数+栈
bpftrace -e 'tracepoint:block:block_rq_issue { @start[args->dev, args->sector] = nsecs; }
             tracepoint:block:block_rq_complete /@start[args->dev, args->sector]/ {
               @usecs = hist((nsecs - @start[args->dev, args->sector]) / 1000);
               delete(@start[args->dev, args->sector]); }'              # block I/O 延迟直方图
bpftrace -e 'tracepoint:sched:sched_wakeup { @qtime[args->pid] = nsecs; }
             tracepoint:sched:sched_switch /@qtime[args->next_pid]/ {
               @usecs[args->next_comm] = hist((nsecs - @qtime[args->next_pid]) / 1000);
               delete(@qtime[args->next_pid]); }'                       # 调度延迟分布
```

> **嵌入式注意**: bpftrace 依赖 BTF+LLVM，rootfs 较大。轻量替代：`trace-cmd` + kprobe events (§4-5) 或 BCC `funccount`/`funclatency`。

---

## 6. kgdb / kdb 交互调试

```bash
# 内核配置: CONFIG_KGDB=y  CONFIG_KGDB_KDB=y  CONFIG_KGDB_SERIAL_CONSOLE=y

# 目标板激活 kgdb
echo ttyS2 > /sys/module/kgdboc/parameters/kgdboc
echo g > /proc/sysrq-trigger     # 进入 kgdb 等待连接

# 主机端 GDB 连接
aarch64-linux-gnu-gdb vmlinux
(gdb) target remote /dev/ttyUSB0
(gdb) bt / list / break my_func / continue

# kdb 直接在目标板使用 (SysRq-g 进入)
kdb> bt / bta / ps / md <addr> / bp <func> / go
```

---

## 7. 内存调试

### 7.1 KASAN (内核地址消毒器)

检测越界访问、use-after-free、double-free：

```
CONFIG_KASAN=y
CONFIG_KASAN_GENERIC=y    # 通用模式 (显著降低性能)
# 或 CONFIG_KASAN_SW_TAGS=y  (ARM64，性能更好)
```

KASAN 报告示例：

```
BUG: KASAN: slab-out-of-bounds in my_func+0x3c/0x60
Write of size 4 at addr ffff00001234abcd by task test/1234

Call trace:
 my_func+0x3c/0x60
 ...

Allocated by task 1234:
 kmalloc+0x...
 ...
```

### 7.2 KMEMLEAK (内核内存泄漏检测)

```
CONFIG_DEBUG_KMEMLEAK=y
```

```bash
# 触发扫描
echo scan > /sys/kernel/debug/kmemleak

# 查看泄漏报告
cat /sys/kernel/debug/kmemleak

# 清除记录
echo clear > /sys/kernel/debug/kmemleak
```

### 7.3 SLUB Debug

```bash
# 启动参数
slub_debug=UFPZ    # U=user tracking  F=sanity checks  P=poisoning  Z=red zoning

# 运行时查看特定 slab 信息
cat /sys/kernel/slab/kmalloc-128/alloc_calls
cat /sys/kernel/slab/kmalloc-128/free_calls

# slabinfo 概览
slabtop
cat /proc/slabinfo
```

### 7.4 page_owner (页面分配追踪)

```bash
# 启动参数: page_owner=on
# CONFIG_PAGE_OWNER=y

cat /sys/kernel/debug/page_owner    # 查看每个页面的分配调用栈
# 用内核脚本排序
./scripts/page_owner_sort.py /sys/kernel/debug/page_owner
```

> 内存调试工具详解（KASAN 报告解读、KMEMLEAK 误报处理、SLUB debug flags 详解等）见 `references/memory_lock_debug.md`

---

## 8. 锁与并发调试

### 8.1 lockdep (锁依赖检测)

```
CONFIG_PROVE_LOCKING=y
CONFIG_DEBUG_LOCK_ALLOC=y
CONFIG_LOCKDEP=y
```

lockdep 检测到死锁模式时会打印：

```
=============================================
WARNING: possible circular locking dependency detected
...
Chain exists of: &lock_a --> &lock_b --> &lock_c
```

### 8.2 hung_task 检测

```
CONFIG_DETECT_HUNG_TASK=y
CONFIG_DEFAULT_HUNG_TASK_TIMEOUT=120   # 秒
```

```bash
# 运行时调整超时
echo 60 > /proc/sys/kernel/hung_task_timeout_secs
```

### 8.3 soft lockup / hard lockup

```
CONFIG_SOFTLOCKUP_DETECTOR=y
CONFIG_HARDLOCKUP_DETECTOR=y     # 需要 NMI 支持 (x86)
CONFIG_BOOTPARAM_SOFTLOCKUP_PANIC=y   # soft lockup 触发 panic
```

```bash
# 调整检测时间
echo 30 > /proc/sys/kernel/watchdog_thresh    # 默认 10 秒
```

### 8.4 RCU stall 检测

```
RCU stall 信息通常表示某个 CPU 长时间未响应 RCU 回调。

rcu_sched kthread starved for 21023 jiffies!
INFO: rcu_sched self-detected stall on CPU
```

```bash
# 调整 RCU stall 超时
echo 60 > /sys/module/rcupdate/parameters/rcu_cpu_stall_timeout
```

> lockdep 报告解读、死锁模式分类、KCSAN（并发 sanitizer）详解见 `references/memory_lock_debug.md`

---

## 9. crash / kdump 事后分析

### 9.1 kdump 配置

```bash
# 内核: CONFIG_CRASH_DUMP=y  CONFIG_KEXEC=y  CONFIG_PROC_VMCORE=y
# 启动参数: crashkernel=256M
# 加载 dump 内核:
kexec -p /boot/vmlinuz-dump --initrd=/boot/initrd-dump.img \
      --append="root=/dev/sda1 single irqpoll maxcpus=1"
```

### 9.2 crash 工具核心命令

```bash
crash vmlinux vmcore
crash> bt / bt -a            # 当前/所有 CPU 调用栈
crash> log                   # 内核日志
crash> ps / ps -m            # 进程列表 / 按内存排序
crash> kmem -s               # slab 信息
crash> struct task_struct <addr>   # 查看结构体
crash> dis <func> / sym <addr>     # 反汇编 / 地址转符号
crash> foreach bt            # 所有进程的调用栈
```

> kdump 嵌入式配置、ramdump、pstore/last_kmsg、crash 完整命令见 `references/oops_panic_crash.md`

---

## 10. 调试辅助接口

### 10.1 /proc 和 /sys 调试

```bash
# 进程调试
cat /proc/<pid>/stack              # 内核栈
cat /proc/<pid>/wchan              # 等待在哪个函数
cat /proc/<pid>/status             # 进程状态
cat /proc/<pid>/maps               # 内存映射

# 系统全局
cat /proc/interrupts               # 中断统计
cat /proc/softirqs                 # 软中断统计
cat /proc/buddyinfo                # 伙伴系统碎片
cat /proc/vmallocinfo              # vmalloc 区域
```

### 10.2 SysRq (魔术键)

```bash
echo 1 > /proc/sys/kernel/sysrq   # 启用所有 SysRq 功能

echo t > /proc/sysrq-trigger      # 打印所有进程调用栈
echo w > /proc/sysrq-trigger      # 打印 blocked (D state) 进程栈
echo l > /proc/sysrq-trigger      # 打印所有 CPU 调用栈
echo m > /proc/sysrq-trigger      # 打印内存信息
echo p > /proc/sysrq-trigger      # 打印当前 CPU 寄存器
echo c > /proc/sysrq-trigger      # 触发 crash (测试 kdump)
echo b > /proc/sysrq-trigger      # 立即重启 (不同步磁盘)
echo s > /proc/sysrq-trigger      # 同步所有文件系统
echo u > /proc/sysrq-trigger      # 重新挂载所有 FS 为只读
```

⚠ `echo c > /proc/sysrq-trigger` 会立即触发内核崩溃，仅用于测试 kdump 配置。

### 10.3 devmem (直接读写寄存器)

```bash
# 需要: CONFIG_DEVMEM=y, /dev/mem 设备节点
# 读取 32 位寄存器
devmem 0x40200000 32
# 写入
devmem 0x40200000 32 0x12345678
# 适用于快速验证寄存器值, 无需编写驱动的 ioremap 映射
```

### 10.4 dump_stack / BUG_ON / WARN_ON

```c
dump_stack();                 // 打印当前调用栈 (不崩溃)
BUG_ON(condition);            // 条件满足 → panic() (仅严重 bug 使用)
WARN_ON(condition);           // 条件满足 → 打印调用栈 + 警告 (推荐)
WARN_ONCE(condition, "msg");  // 仅打印一次
```

### 10.5 ARM 硬件 Watchpoint (踩内存排查)

```bash
# 使用硬件 watchpoint 监控特定内存地址被修改:
# github.com/Ylarod/hardware-breakpoint
# 当目标地址被意外写入时, CPU 触发 debug exception → 打印调用栈, 定位踩内存元凶
```

### 10.6 pstore / last_kmsg

```bash
# pstore：持久化存储崩溃日志 (需硬件支持或 ramoops)
ls /sys/fs/pstore/
cat /sys/fs/pstore/dmesg-ramoops-0

# 内核启动参数 (ramoops)
ramoops.mem_address=0x110000 ramoops.mem_size=0xf0000 ramoops.console_size=0x80000
```

---

## 11. 调试相关内核配置速查

### 11.1 调试配置速查表

| CONFIG | 分类 | 功能 | 性能影响 |
|--------|------|------|--------|
| `DEBUG_INFO` | 通用 | vmlinux 调试信息 | 编译慢 |
| `FRAME_POINTER` | 通用 | 准确的栈回溯 | 轻微 |
| `DYNAMIC_DEBUG` | 通用 | 运行时开关 pr_debug | 轻微 |
| `MAGIC_SYSRQ` | 通用 | SysRq 支持 | 无 |
| `DEBUG_FS` | 通用 | debugfs 文件系统 | 无 |
| `KASAN` | 内存 | 地址消毒器 | **严重** |
| `KASAN_SW_TAGS` | 内存 | ARM64 标签模式 KASAN | 中等 |
| `DEBUG_KMEMLEAK` | 内存 | 内存泄漏检测 | 中等 |
| `SLUB_DEBUG` | 内存 | SLUB 分配器调试 | 中等 |
| `PAGE_OWNER` | 内存 | 页面分配追踪 | 中等 |
| `PROVE_LOCKING` | 锁 | lockdep 死锁检测 | 中等 |
| `DEBUG_ATOMIC_SLEEP` | 锁 | 原子上下文睡眠检测 | 轻微 |
| `KCSAN` | 锁 | 数据竞争检测 | 中等 |
| `DETECT_HUNG_TASK` | 锁 | hung task 检测 | 无 |
| `FTRACE` | 追踪 | ftrace 框架 | 轻微 |
| `FUNCTION_TRACER` | 追踪 | 函数追踪器 | 轻微 |
| `KPROBES` | 追踪 | kprobes 支持 | 轻微 |
| `DYNAMIC_FTRACE` | 追踪 | 动态 ftrace | 无 |

### 11.2 推荐的调试内核配置组合

```
# 必开 (开发阶段)
CONFIG_DEBUG_INFO=y  CONFIG_FRAME_POINTER=y  CONFIG_DYNAMIC_DEBUG=y
CONFIG_MAGIC_SYSRQ=y  CONFIG_DEBUG_FS=y  CONFIG_FTRACE=y
CONFIG_FUNCTION_TRACER=y  CONFIG_KPROBES=y  CONFIG_DETECT_HUNG_TASK=y
# 推荐开
CONFIG_KASAN=y  CONFIG_DEBUG_KMEMLEAK=y  CONFIG_PROVE_LOCKING=y
CONFIG_DEBUG_ATOMIC_SLEEP=y  CONFIG_SLUB_DEBUG=y
```

---

## 参考资料索引

| 文件 | 内容 | 加载时机 |
|------|------|---------|
| `references/printk_dynamic_debug.md` | printk 子系统详解、日志缓冲区、console 驱动、earlycon、dev_dbg 完整用法 | 用户深入调试日志问题 |
| `references/ftrace_kprobes.md` | ftrace 框架详解、所有 tracer 类型、trace events 完整列表、kprobes 参数语法、trace-cmd/kernelshark、BPF/bpftrace | 用户需要追踪内核行为 |
| `references/oops_panic_crash.md` | Oops 完整解读、ARM64 寄存器分析、常见崩溃模式、kdump 嵌入式配置、crash 高级命令、pstore/ramoops | 用户分析内核崩溃 |
| `references/memory_lock_debug.md` | KASAN 报告解读、KMEMLEAK 高级用法、SLUB debug flags、page_owner 分析、lockdep 报告解读、KCSAN、死锁模式分类 | 用户排查内存或锁问题 |

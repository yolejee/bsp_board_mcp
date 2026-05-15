# Oops / Panic / Crash 分析详细参考

## 目录

1. [Oops 信息完整解读](#1-oops-信息完整解读)
2. [ARM64 Oops 寄存器分析](#2-arm64-oops-寄存器分析)
3. [常见崩溃模式与分析](#3-常见崩溃模式与分析)
4. [kdump 嵌入式平台配置](#4-kdump-嵌入式平台配置)
5. [crash 工具完整命令参考](#5-crash-工具完整命令参考)
6. [ramdump 分析](#6-ramdump-分析)
7. [pstore / ramoops](#7-pstore--ramoops)
8. [GDB 内核调试](#8-gdb-内核调试)

---

## 1. Oops 信息完整解读

### 1.1 完整 Oops 消息结构

```
[  123.456] 异常类型描述行
            (例: Unable to handle kernel NULL pointer dereference at virtual address 0000000000000010)

[  123.456] Mem abort info:
[  123.456]   ESR = 0x96000006      ← ARM64 异常综合寄存器
[  123.456]   EC = 0x25, IL = 32    ← 异常类别和指令长度
[  123.456]   SET = 0, FnV = 0
[  123.456]   EA = 0, S1PTW = 0
[  123.456]   FSC = 0x06: level 2 translation fault  ← 缺页故障码

[  123.456] Data abort info:
[  123.456]   ISV = 0, ISS = 0x00000006
[  123.456]   CM = 0, WnR = 0       ← WnR: 0=读访问  1=写访问

[  123.456] CPU: 2 PID: 1234 Comm: my_app Tainted: G   OE  5.10.110 #1
            ↑CPU  ↑进程           ↑进程名     ↑污染标志  ↑内核版本

[  123.456] pc : my_driver_read+0x28/0x100 [my_module]   ← PC (出错指令)
[  123.456] lr : my_driver_open+0x44/0x80 [my_module]    ← LR (返回地址)
[  123.456] sp : ffffffc011b83d00
[  123.456] x29: ffffffc011b83d10 x28: ffffff8003456000    ← 通用寄存器
[  123.456] ...

[  123.456] Call trace:              ← 调用栈 (最重要)
[  123.456]  my_driver_read+0x28/0x100 [my_module]
[  123.456]  vfs_read+0xc8/0x1e4
[  123.456]  ksys_read+0x6c/0xdc
[  123.456]  __arm64_sys_read+0x1c/0x28
[  123.456]  invoke_syscall.constprop.0+0x54/0xe0
```

### 1.2 Tainted 标志说明

| 标志 | 含义 |
|------|------|
| `G` | 已加载 GPL 许可模块 |
| `P` | 已加载非 GPL 模块 |
| `O` | 已加载外部模块 (out-of-tree) |
| `E` | 之前发生过 Oops |
| `W` | 之前发生过 WARNING |
| `C` | staging 驱动已加载 |
| `I` | 平台固件 bug |
| `D` | 发生过 die() |

### 1.3 地址解析工具链

```bash
# 1. addr2line (最常用)
aarch64-linux-gnu-addr2line -e vmlinux -fip ffffffc0104abcde
# 输出: my_driver_read at drivers/misc/my_driver.c:142

# 2. 外部模块 (需用 .ko 文件 + 偏移量)
# PC = my_driver_read+0x28 → 函数内偏移 0x28
aarch64-linux-gnu-addr2line -e my_module.ko -fip 0x28
# 注意: 需要带调试信息的 .ko

# 3. faddr2line (内核自带脚本)
./scripts/faddr2line vmlinux my_driver_read+0x28

# 4. decode_stacktrace.sh (自动解析整个 Oops)
./scripts/decode_stacktrace.sh vmlinux /path/to/modules < oops.log

# 5. GDB
aarch64-linux-gnu-gdb vmlinux
(gdb) list *(my_driver_read+0x28)
(gdb) info line *(0xffffffc0104abcde)
```

### 1.4 Oops vs Panic

| 特征 | Oops | Panic |
|------|------|-------|
| 严重性 | 错误但可能继续运行 | 不可恢复，系统停止 |
| 进程影响 | 杀死当前进程 | 整个系统停止 |
| 什么时候变 panic | `panic_on_oops=1` 或中断上下文 Oops | 直接就是 panic |
| 可恢复 | 可能（不推荐继续运行） | 不可 |

---

## 2. ARM64 Oops 寄存器分析

### 2.1 ESR (Exception Syndrome Register) 解读

```
ESR = 0x96000006
      ├── EC  = 0x25 (bits[31:26]) → Data Abort from lower EL
      ├── IL  = 1 (bit[25])        → 32-bit instruction
      └── ISS = 0x06 (bits[24:0])  → FSC = 0x06 (level 2 translation fault)
```

| EC 值 | 含义 |
|-------|------|
| 0x21 | Instruction Abort from lower EL |
| 0x24 | Data Abort from current EL |
| 0x25 | Data Abort from lower EL |
| 0x2F | SError interrupt |
| 0x15 | SVC instruction (系统调用) |

### 2.2 FAR (Fault Address Register)

```
FAR = 0x0000000000000010
```

这是触发异常的虚拟地址。如果接近 0，通常是 NULL 指针 + 结构体偏移。

```c
// FAR = 0x10 通常意味着:
struct my_struct *p = NULL;
p->member;    // member 在 struct 中 offset 为 0x10
```

### 2.3 通用寄存器 (x0-x30)

```bash
# 用 GDB 查看函数签名, 对照寄存器推断参数值
(gdb) info args
# x0 = 第一个参数, x1 = 第二个, ...
# x29 = FP (frame pointer)
# x30 = LR (link register) = 返回地址
```

---

## 3. 常见崩溃模式与分析

### 3.1 NULL 指针解引用

```
Unable to handle kernel NULL pointer dereference at virtual address 0000000000000020
pc : my_func+0x3c/0x100 [my_module]
```

**分析步骤：**
1. 看 FAR (0x20) → 大概率是 struct 指针为 NULL，访问 offset 0x20 的成员
2. `addr2line` 定位源码行号
3. 检查该行哪个指针可能为 NULL
4. 回溯 `probe` 函数看获取资源是否失败

### 3.2 Use-After-Free

```
BUG: KASAN: use-after-free in my_func+0x28/0x100
Read of size 8 at addr ffff000012345000 by task test/999

Freed by task 888:
 kfree+0x...
 my_release+0x...

Allocated by task 777:
 kmalloc+0x...
 my_probe+0x...
```

**分析：** KASAN 已给出分配和释放的调用栈，直接定位生命周期管理错误。

### 3.3 scheduling while atomic

```
BUG: scheduling while atomic: my_app/1234/0x00000002
Call trace:
 __schedule+0x...
 schedule+0x...
 mutex_lock+0x...        ← 这里尝试获取 mutex (可睡眠)
 my_irq_handler+0x...    ← 但在中断上下文
```

**原因：** 在不可睡眠的上下文 (中断处理程序、spinlock 内、softirq 内) 调用了可能睡眠的函数。

**修复方向：**
- 改用 `mutex_trylock()` 或 `spin_lock()`
- 将工作推迟到可睡眠上下文 (workqueue)

### 3.4 栈溢出

```
Kernel panic - not syncing: Kernel stack overflow
CPU: 0 PID: 1 Comm: init
Call trace:
 dump_backtrace+0x0/0x178
 ...
 deep_recursive_func+0x.../0x...    ← 递归调用
```

**排查：**
```bash
# 查看栈大小
cat /proc/<pid>/stack        # 内核栈
# 默认内核栈 ARM64: 16KB, x86_64: 16KB (配置 THREAD_SIZE)
# 检查函数内大变量是否分配在栈上
```

### 3.5 BUG() / BUG_ON()

```
kernel BUG at drivers/my_driver.c:256!
Internal error: Oops - BUG: 0 [#1] PREEMPT SMP
```

**原因：** 代码中的 `BUG_ON(condition)` 断言触发，说明条件不应该成立。

---

## 4. kdump 嵌入式平台配置

### 4.1 嵌入式 kdump 要点

```bash
# 嵌入式内存有限，crashkernel 需要精打细算
crashkernel=128M              # 最小推荐
crashkernel=64M               # 极端场景

# 用 kdump-tools
apt install kdump-tools
# 配置 /etc/default/kdump-tools
USE_KDUMP=1
KDUMP_COREDIR="/var/crash"
```

### 4.2 无 kdump 时的替代方案

```bash
# 1. ramoops/pstore (推荐嵌入式)
# 即使没有 kdump，也能保存最后的日志
# 见第 7 节

# 2. panic 自动重启 + 保存 last_kmsg
echo 5 > /proc/sys/kernel/panic   # panic 后 5 秒自动重启

# 3. 串口日志保存
# 主机端: screen -L /dev/ttyUSB0 1500000
```

---

## 5. crash 工具完整命令参考

### 5.1 进程分析

```bash
crash> ps                    # 进程列表
crash> ps -m                 # 按 RSS 排序
crash> ps | grep " D "       # D 状态进程
crash> ps -t <pid>           # 线程
crash> set <pid>             # 切换上下文到指定进程
crash> bt                    # 当前进程栈
crash> bt -a                 # 所有 CPU 的活动进程栈
crash> bt -l                 # 带行号
crash> bt <pid>              # 指定进程的栈
crash> foreach bt            # 所有进程的栈
```

### 5.2 内存分析

```bash
crash> kmem -s               # slab 缓存统计
crash> kmem -i               # 内存信息 (类似 meminfo)
crash> kmem -z               # zone 信息
crash> vm <pid>              # 进程虚拟内存映射
crash> vm <pid> -m           # 更详细的映射
crash> files <pid>           # 进程打开的文件
crash> rd -x <addr> <count>  # 读指定内存地址
crash> struct file <addr>    # 解析结构体
crash> struct -o file        # 显示结构体布局和偏移
crash> p variable            # 打印全局变量值
```

### 5.3 模块和符号

```bash
crash> mod                   # 已加载模块
crash> mod -s my_module /path/my_module.ko  # 加载外部模块符号
crash> sym my_func           # 符号 → 地址
crash> sym <addr>            # 地址 → 符号
crash> dis my_func           # 反汇编函数
crash> dis -l my_func        # 反汇编带源码行号
crash> whatis <symbol>       # 符号类型信息
```

### 5.4 系统信息

```bash
crash> log                   # 内核日志 (dmesg)
crash> log -T                # 带时间戳
crash> mach                  # 机器信息
crash> runq                  # 每个 CPU 的运行队列
crash> irq -s                # 中断统计
crash> timer                 # 活跃定时器
crash> mount                 # 挂载点
crash> net -s                # 网络统计
```

---

## 6. ramdump 分析

### 6.1 获取 ramdump

```bash
# 方法 1: kexec-based (崩溃时自动 dump)
# 配置同 kdump

# 方法 2: JTAG/SWD 读取
# 通过 J-Link 或 FT2232H 直接读取内存
# 参考 DS5/OpenOCD 文档

# 方法 3: /proc/vmcore (kdump 捕获内核中)
cp /proc/vmcore /var/crash/vmcore
```

### 6.2 从 ramdump 提取日志

```bash
# 用 crash 打开 ramdump
crash vmlinux vmcore
crash> log        # 查看日志
crash> bt -a      # 查看所有 CPU 栈

# 不用 crash 提取 dmesg
strings vmcore | grep -A2 "\[.*\].*:" | head -100
```

---

## 7. pstore / ramoops

### 7.1 ramoops 配置

```bash
# 内核命令行
ramoops.mem_address=0x110000 ramoops.mem_size=0xf0000 \
ramoops.console_size=0x80000 ramoops.ecc=1

# 或 DTS 配置 (推荐)
reserved-memory {
    ramoops@110000 {
        compatible = "ramoops";
        reg = <0x0 0x110000 0x0 0xf0000>;
        console-size = <0x80000>;
        record-size = <0x20000>;
        ftrace-size = <0x20000>;
        pmsg-size = <0x10000>;
        ecc-size = <16>;
    };
};
```

### 7.2 使用

```bash
# 崩溃后重启，查看保存的日志
ls /sys/fs/pstore/
# console-ramoops-0   → console 输出
# dmesg-ramoops-0     → Oops/Panic 信息
# ftrace-ramoops-0    → ftrace 数据 (如果开启)
# pmsg-ramoops-0      → 用户态日志

cat /sys/fs/pstore/dmesg-ramoops-0   # 查看崩溃日志
cat /sys/fs/pstore/console-ramoops-0  # 查看最后的 console 输出
```

### 7.3 内核配置

```
CONFIG_PSTORE=y
CONFIG_PSTORE_CONSOLE=y
CONFIG_PSTORE_PMSG=y
CONFIG_PSTORE_FTRACE=y
CONFIG_PSTORE_RAM=y
```

---

## 8. GDB 内核调试

### 8.1 GDB 直接分析 vmlinux

```bash
aarch64-linux-gnu-gdb vmlinux

# 查看函数源码
(gdb) list my_driver_read
(gdb) list *(my_driver_read+0x28)

# 查看结构体定义
(gdb) ptype struct file
(gdb) ptype /o struct task_struct   # 含偏移量

# 反汇编
(gdb) disassemble my_driver_read
(gdb) x/10i my_driver_read+0x20    # 从偏移 0x20 开始看 10 条指令

# 查看全局变量类型
(gdb) whatis jiffies
```

### 8.2 GDB + lx- 辅助脚本

```bash
# 加载内核 GDB 辅助脚本
(gdb) source vmlinux-gdb.py
# 或在 .gdbinit 中添加:
# add-auto-load-safe-path /path/to/kernel/scripts/gdb

# 可用命令
(gdb) lx-dmesg            # 查看内核日志
(gdb) lx-lsmod            # 列出模块
(gdb) lx-ps               # 进程列表
(gdb) lx-symbols           # 加载所有模块符号
(gdb) lx-version           # 内核版本
(gdb) lx-timerlist         # 定时器列表
```

### 8.3 GDB + QEMU 内核调试

```bash
# 启动 QEMU
qemu-system-aarch64 -kernel Image -s -S ...
# -s = 在 1234 端口启动 gdbserver
# -S = 启动后暂停等待 GDB

# GDB 连接
aarch64-linux-gnu-gdb vmlinux
(gdb) target remote :1234
(gdb) break start_kernel
(gdb) continue
```

# printk 与 Dynamic Debug 详细参考

## 目录

1. [printk 子系统架构](#1-printk-子系统架构)
2. [日志缓冲区 (log_buf)](#2-日志缓冲区)
3. [console 驱动与 earlycon](#3-console-驱动与-earlycon)
4. [printk 高级用法](#4-printk-高级用法)
5. [Dynamic Debug 完整参考](#5-dynamic-debug-完整参考)
6. [dev_dbg / dev_err / dev_info](#6-设备模型日志)
7. [调试打印最佳实践](#7-调试打印最佳实践)

---

## 1. printk 子系统架构

### 1.1 消息流转路径

```
printk() / pr_info() / dev_dbg()
    ↓
log_buf (环形缓冲区, 默认 256KB)
    ↓
├── console driver → 串口/VGA/netconsole
├── /dev/kmsg → systemd-journald → journalctl
└── dmesg 命令 → 直接读 log_buf
```

### 1.2 日志级别控制

```bash
# /proc/sys/kernel/printk 有 4 个值:
#   current  default  minimum  boot_default
cat /proc/sys/kernel/printk
# 典型输出: 7    4    1    7

# 含义:
# current=7   → console 只显示级别 < 7 的消息 (即 0~6, 不含 KERN_DEBUG)
# default=4   → printk() 不指定级别时用 KERN_WARNING
# minimum=1   → current 可设的最小值
# boot_default=7 → boot 时的默认 current

# 显示所有消息 (含 KERN_DEBUG)
echo 8 > /proc/sys/kernel/printk

# 只显示 error 及以上
echo 4 > /proc/sys/kernel/printk
```

### 1.3 启动参数控制

```bash
# 内核命令行
loglevel=7              # 设置默认 console 日志级别
quiet                   # 等于 loglevel=4
debug                   # 等于 loglevel=7 + 开启大量 pr_debug
ignore_loglevel         # 忽略级别，打印所有消息
log_buf_len=1M          # 增大日志缓冲区
```

---

## 2. 日志缓冲区

### 2.1 缓冲区大小

```bash
# 查看当前大小
dmesg | head -1    # 看 log_buf_len
cat /proc/sys/kernel/printk_devkmsg

# 启动参数调整
log_buf_len=2M              # 增大缓冲区 (调试时推荐)
log_buf_len=256K            # 默认值

# Kconfig
CONFIG_LOG_BUF_SHIFT=17     # 2^17 = 128KB
CONFIG_LOG_CPU_MAX_BUF_SHIFT=12  # per-CPU 缓冲区
```

### 2.2 /dev/kmsg

```bash
# /dev/kmsg 是 printk 缓冲区的字符设备接口
cat /dev/kmsg                           # 持续读取 (阻塞)
echo "<3>my error message" > /dev/kmsg  # 用户态写入内核日志

# 格式: priority,sequence,timestamp,-;message
# 例: 6,1234,5678901,-;Hello from kernel
```

### 2.3 netconsole (网络日志)

```bash
# 通过网络发送内核日志，适用于串口不可用的场景

# 方法一：内核启动参数
netconsole=6665@192.168.1.100/eth0,6666@192.168.1.200/aa:bb:cc:dd:ee:ff

# 方法二：模块方式
modprobe netconsole netconsole=@/,@192.168.1.200/

# 接收端
nc -u -l 6666
```

---

## 3. console 驱动与 earlycon

### 3.1 earlycon (早期控制台)

earlycon 在 console 驱动注册前提供输出，用于调试启动早期问题：

```bash
# ARM64 常用 earlycon 配置
earlycon=uart8250,mmio32,0xfe660000      # 8250 UART (给物理地址)
earlycon=pl011,0x9000000                  # PL011 UART
earlycon                                  # 自动从 DTS chosen/stdout-path 获取

# DTS 中配置
chosen {
    stdout-path = "serial2:1500000n8";
};
```

### 3.2 console 参数

```bash
# 指定 console 输出设备
console=ttyS2,1500000n8      # 串口2, 波特率 1500000
console=ttyFIQ0              # FIQ debugger (Rockchip)
console=tty0                 # VGA/HDMI 文本控制台

# 多个 console (日志发往所有设备)
console=ttyS2,1500000 console=tty0
```

### 3.3 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 启动无任何输出 | earlycon 未配或地址错 | 检查 earlycon= 参数和 UART 地址 |
| 有 earlycon 但后面中断 | console 驱动未注册 | 检查 console= 与 DTS 匹配 |
| 日志不全/丢失 | 缓冲区太小 | `log_buf_len=2M` |
| 日志级别不够 | loglevel 太低 | `loglevel=8` 或 `debug` |

---

## 4. printk 高级用法

### 4.1 频率限制

```c
// 避免日志刷屏
printk_ratelimited(KERN_WARNING "event happened\n");  // 默认 5 秒 10 条
pr_warn_ratelimited("event happened\n");

// 只打一次
printk_once(KERN_INFO "module loaded\n");
pr_info_once("module loaded\n");

// 自定义限制
static DEFINE_RATELIMIT_STATE(my_rs, 5 * HZ, 10);  // 5秒内最多10条
if (__ratelimit(&my_rs))
    pr_warn("warning\n");
```

### 4.2 条件打印与格式化

```c
// 十六进制 dump
print_hex_dump(KERN_DEBUG, "data: ", DUMP_PREFIX_OFFSET, 16, 1, buf, len, true);

// 打印调用栈
dump_stack();               // 打印当前调用栈
WARN_ON(condition);         // 条件成立时打印栈 + 警告
WARN_ONCE(condition, "msg"); // 只警告一次
BUG_ON(condition);          // 条件成立时 panic (慎用)

// 带设备/驱动前缀
pr_fmt(fmt) KBUILD_MODNAME ": " fmt   // 在文件头 #define
```

### 4.3 内核格式化扩展

```c
// 指针类型智能打印 (printk 格式扩展)
printk("%pS\n", ptr);     // 符号名+偏移: my_func+0x10/0x80
printk("%ps\n", ptr);     // 符号名: my_func
printk("%pB\n", ptr);     // 回溯格式符号名
printk("%pR\n", res);     // struct resource: [mem 0x1000-0x1fff]
printk("%pI4\n", &ip);    // IPv4 地址: 192.168.1.1
printk("%pM\n", mac);     // MAC 地址: 01:02:03:04:05:06
printk("%pOF\n", np);     // OF 节点全路径: /soc/i2c@fe5a0000
printk("%pU\n", uuid);    // UUID
printk("%*ph\n", len, buf); // 十六进制字节序列: 00 01 02 03
```

---

## 5. Dynamic Debug 完整参考

### 5.1 控制语法

```bash
# 基本格式: echo '<match> <flags>' > /sys/kernel/debug/dynamic_debug/control

# 匹配条件
echo 'file drivers/i2c/*.c +p'       > control  # 按文件路径 (支持通配符)
echo 'func i2c_transfer +p'          > control  # 按函数名
echo 'module i2c_core +p'            > control  # 按模块名
echo 'format "timeout" +p'           > control  # 按消息内容
echo 'line 100-200 +p'               > control  # 按行号范围

# 组合条件
echo 'file i2c-core-base.c func i2c_transfer +p' > control

# flags:
# +p  开启打印
# -p  关闭打印
# +f  打印函数名
# +l  打印行号
# +m  打印模块名
# +t  打印线程 ID
# +_  无前缀 (清除所有 flags)
echo 'module spi_master +pflmt' > control   # 开启并加全部前缀
```

### 5.2 启动时开启

```bash
# 内核启动参数
dyndbg="file drivers/i2c/* +p"
# 模块参数
i2c_core.dyndbg="+p"
# 多个规则用分号隔开
dyndbg="file foo.c +p ; func bar +p"
```

### 5.3 查看当前状态

```bash
# 查看所有注册点及状态
cat /sys/kernel/debug/dynamic_debug/control | head -20

# 只看已开启的
grep "=p" /sys/kernel/debug/dynamic_debug/control

# 统计
wc -l /sys/kernel/debug/dynamic_debug/control   # 总调试点数
grep -c "=p" /sys/kernel/debug/dynamic_debug/control  # 已开启数
```

---

## 6. 设备模型日志

### 6.1 dev_*() 系列函数

```c
// 使用 dev_*() 代替 pr_*()，自动带设备名前缀
dev_err(dev, "failed to init: %d\n", ret);     // [ 1.234] my_device my_i2c.0: failed to init: -22
dev_warn(dev, "warning\n");
dev_info(dev, "initialized\n");
dev_dbg(dev, "debug msg\n");          // 需 DEBUG 或 dynamic debug 开启

// 条件版本
dev_err_once(dev, "only once\n");
dev_warn_ratelimited(dev, "rate limited\n");
dev_dbg_ratelimited(dev, "debug rl\n");
```

### 6.2 开启 dev_dbg 的三种方式

```bash
# 方式 1: 在源文件头 #include 前 #define DEBUG
#define DEBUG
#include <linux/device.h>

# 方式 2: Makefile 中
CFLAGS_my_driver.o += -DDEBUG

# 方式 3: dynamic debug (推荐，无需重编译)
echo 'file my_driver.c +p' > /sys/kernel/debug/dynamic_debug/control
```

---

## 7. 调试打印最佳实践

### 7.1 推荐做法

| 做法 | 说明 |
|------|------|
| 用 `dev_*()` 代替 `pr_*()` | 自动带设备名，日志更易筛选 |
| 用 `pr_debug()` / `dev_dbg()` | 生产环境零开销，需要时 dyndbg 开启 |
| 用 `pr_fmt()` 宏 | 统一模块前缀 |
| 用 `%pS` / `%pOF` 等扩展格式 | 比手动格式化更安全、更规范 |
| 错误路径用 `dev_err()` | 方便 `dmesg -l err` 筛选 |

### 7.2 常见错误

| 错误 | 问题 | 正确做法 |
|------|------|---------|
| `printk(ptr)` | 格式串注入风险 | `printk("%s", ptr)` |
| `BUG_ON(可恢复条件)` | 导致不必要的 panic | 用 `WARN_ON` + 错误处理 |
| 大量 `pr_info()` 在热路径 | 性能问题 | 改用 `pr_debug()` + dyndbg |
| 调试完不清理 | 日志污染 | 提交前 grep 清理 |

# 内存调试与锁调试详细参考

## 目录

1. [KASAN 详解](#1-kasan-详解)
2. [KMEMLEAK 详解](#2-kmemleak-详解)
3. [SLUB Debug 详解](#3-slub-debug-详解)
4. [page_owner 与页面分析](#4-page_owner-与页面分析)
5. [其他内存调试工具](#5-其他内存调试工具)
6. [lockdep 报告解读](#6-lockdep-报告解读)
7. [KCSAN 数据竞争检测](#7-kcsan-数据竞争检测)
8. [常见死锁模式分类](#8-常见死锁模式分类)
9. [内核内存布局参考](#9-内核内存布局参考)

---

## 1. KASAN 详解

### 1.1 三种模式

| 模式 | CONFIG | 性能影响 | 支持架构 | 适用 |
|------|--------|---------|---------|------|
| Generic | `KASAN_GENERIC` | 2-3x 减速 | 全部 | 全面检测 |
| SW_TAGS | `KASAN_SW_TAGS` | 1.5-2x | ARM64 | 平衡方案 |
| HW_TAGS | `KASAN_HW_TAGS` | 很小 | ARM64 MTE | 生产接近可用 |

### 1.2 检测能力

| 错误类型 | Generic | SW_TAGS | HW_TAGS |
|---------|---------|---------|---------|
| slab out-of-bounds | ✅ | ✅ | ✅ |
| slab use-after-free | ✅ | ✅ | ✅ |
| stack out-of-bounds | ✅ | ❌ | ❌ |
| global out-of-bounds | ✅ | ❌ | ❌ |
| use-after-scope | ✅ | ❌ | ❌ |
| double-free | ✅ | ✅ | ✅ |
| invalid-free | ✅ | ✅ | ✅ |

### 1.3 KASAN 报告解读

```
==================================================================
BUG: KASAN: slab-out-of-bounds in my_func+0x3c/0x60
Write of size 4 at addr ffff00001234abcd by task test/1234
  ↑写操作  ↑4字节   ↑访问地址              ↑进程名/PID

CPU: 2 PID: 1234 Comm: test Not tainted 5.10.0 #1

Call trace:                            ← 出错位置的调用栈
 kasan_report+0x...
 check_memory_region+0x...
 my_func+0x3c/0x60                     ← 出错函数和偏移
 my_caller+0x...
 ...

Allocated by task 1234:                ← 该内存的分配调用栈
 kasan_save_stack+0x...
 __kasan_kmalloc+0x...
 kmalloc+0x...
 my_init+0x1c/0x40                     ← 在这里分配
 ...

The buggy address belongs to the object at ffff00001234ab00
 which belongs to the cache kmalloc-64 of size 64  ← 分配了 64 字节
The buggy address is located 13 bytes to the right of
 64-byte region [ffff00001234ab00, ffff00001234ab40)  ← 越界了 13 字节
==================================================================
```

### 1.4 启动参数

```bash
# 精细控制
kasan.mode=report      # 只报告不 panic (默认)
kasan.mode=panic       # 检测到错误立即 panic
kasan.stacktrace=on    # 保存分配/释放栈 (消耗内存)
kasan.fault=report     # report|panic

# 禁止特定函数的 KASAN 检查 (代码中)
__attribute__((no_sanitize("kernel-address")))
void my_tricky_func(void) { ... }
```

---

## 2. KMEMLEAK 详解

### 2.1 工作原理

KMEMLEAK 定期扫描内存，查找没有任何指针指向的已分配对象。

```
CONFIG_DEBUG_KMEMLEAK=y
CONFIG_DEBUG_KMEMLEAK_DEFAULT_OFF=n   # 默认开启

# 或启动参数控制
kmemleak=on                           # 开启
kmemleak=off                          # 关闭
```

### 2.2 使用方法

```bash
# 触发扫描
echo scan > /sys/kernel/debug/kmemleak

# 查看结果
cat /sys/kernel/debug/kmemleak

# 清除已知泄漏
echo clear > /sys/kernel/debug/kmemleak

# 设置自动扫描间隔 (秒, 0=关闭自动扫描)
echo 120 > /sys/kernel/debug/kmemleak    # 每 120 秒扫描

# 导出完整报告
echo dump=<file> > /sys/kernel/debug/kmemleak
```

### 2.3 报告解读

```
unreferenced object 0xffff000012345000 (size 128):
  comm "my_driver", pid 500, jiffies 4295123456 (age 1234.567s)
  hex dump (first 32 bytes):
    00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
    ff ff ff ff 00 00 00 00 01 00 00 00 00 00 00 00  ................
  backtrace:
    [<ffffffff80234567>] kmalloc+0x...         ← 分配位置
    [<ffffffff80345678>] my_probe+0x...        ← 调用者
    [<ffffffff80456789>] platform_probe+0x...
    ...
```

### 2.4 处理误报

```c
// 某些场景分配的内存通过非标准方式引用 (如 DMA, 寄存器存地址)
// 使用 kmemleak API 标记:

kmemleak_not_leak(ptr);       // 标记为非泄漏
kmemleak_ignore(ptr);         // 完全忽略此对象
kmemleak_no_scan(ptr);        // 不扫描此对象内部指针
kmemleak_scan_area(ptr, size, offset, length);  // 只扫描部分区域
```

---

## 3. SLUB Debug 详解

### 3.1 启动参数 flags

```bash
slub_debug=FLAGS[,SLAB_NAME]

# FLAGS:
# F  Sanity checks (SLAB_CONSISTENCY_CHECKS)
# Z  Red zoning (在分配前后加哨兵字节)
# P  Poisoning (释放后填充 0x6b, 分配后填充 0x5a)
# U  User tracking (记录分配/释放的调用栈)
# T  Trace (追踪分配/释放)
# A  Failslab (随机分配失败, 测试错误处理)

# 示例
slub_debug=FZPU                      # 全局开启 F+Z+P+U
slub_debug=FZPU,kmalloc-128          # 只对 kmalloc-128 开启
slub_debug=FZ,kmalloc-*              # 对所有 kmalloc 开启 F+Z
```

### 3.2 运行时检查

```bash
# 查看 slab 信息
cat /proc/slabinfo
slabtop

# 查看特定 slab 的分配/释放调用栈 (需 U flag)
cat /sys/kernel/slab/kmalloc-128/alloc_calls
cat /sys/kernel/slab/kmalloc-128/free_calls

# 查看 slab 属性
cat /sys/kernel/slab/kmalloc-128/object_size
cat /sys/kernel/slab/kmalloc-128/objs_per_slab
cat /sys/kernel/slab/kmalloc-128/total_objects

# 验证 slab 完整性
echo 1 > /sys/kernel/slab/kmalloc-128/validate
```

### 3.3 SLUB Debug 报告

```
=============================================================================
BUG kmalloc-64 (Tainted: G    O): Redzone overwritten
-----------------------------------------------------------------------------
INFO: 0xffff00001234ab40-0xffff00001234ab43 @offset=64. First byte 0x78 instead of 0xcc
INFO: Allocated in my_alloc+0x1c/0x40 age=5 cpu=2 pid=1234
INFO: Freed in my_free+0x14/0x30 age=3 cpu=1 pid=1235
```

---

## 4. page_owner 与页面分析

### 4.1 配置

```bash
# 内核配置
CONFIG_PAGE_OWNER=y
CONFIG_STACKTRACE=y

# 启动参数
page_owner=on
```

### 4.2 使用

```bash
# 查看每个已分配页面的信息
cat /sys/kernel/debug/page_owner

# 排序脚本
./scripts/page_owner_sort.py /sys/kernel/debug/page_owner

# 输出格式:
# Page allocated via order N, mask 0x..., pid PID, tgid TGID (comm), ts NNN ns
#  PFN NNNN type ...
#  <stack trace>
```

### 4.3 分析大页分配

```bash
# 按分配大小排序找到大块分配
./scripts/page_owner_sort.py /sys/kernel/debug/page_owner | head -50

# 主要关注:
# - order >= 3 的分配 (连续 8+ 页)
# - 大量相同调用栈的小分配 (可能泄漏)
```

---

## 5. 其他内存调试工具

### 5.1 DEBUG_PAGEALLOC

```
CONFIG_DEBUG_PAGEALLOC=y

# 释放的页面立即从页表中解映射
# use-after-free 会触发页面错误而不是静默损坏
# 性能影响严重，仅调试用
```

### 5.2 PAGE_POISONING

```
CONFIG_PAGE_POISONING=y

# 释放的页面填充 0xAA
# 分配的页面检查是否仍是 0xAA (检测 use-after-free)
```

### 5.3 fault injection (故障注入)

```bash
# 配置
CONFIG_FAULT_INJECTION=y
CONFIG_FAILSLAB=y           # slab 分配失败注入
CONFIG_FAIL_PAGE_ALLOC=y     # 页面分配失败注入
CONFIG_FAIL_MAKE_REQUEST=y   # IO 请求失败注入

# 使用 (通过 debugfs)
echo 10 > /sys/kernel/debug/failslab/probability  # 10% 概率失败
echo 1 > /sys/kernel/debug/failslab/times          # 只失败 1 次
echo N > /sys/kernel/debug/failslab/space           # 限制失败次数

# 按进程注入
echo 1 > /proc/<pid>/make-it-fail
```

### 5.4 内存压力测试

```bash
# 观察 OOM killer 行为
echo 1 > /proc/sys/vm/overcommit_memory    # 允许过度提交
echo 90 > /proc/sys/vm/overcommit_ratio

# 观察 OOM 日志
dmesg | grep -i "out of memory\|oom\|killed process"

# 主动触发 OOM (测试)
echo f > /proc/sysrq-trigger
```

---

## 6. lockdep 报告解读

### 6.1 典型报告

```
=============================================
WARNING: possible circular locking dependency detected
5.10.0 #1 Tainted: G        O
---------------------------------------------
my_app/1234 is trying to acquire lock:
ffff000012345678 (&lock_a){+.+.}-{3:3}, at: func_a+0x20/0x80

but task is already holding lock:
ffff000087654321 (&lock_b){+.+.}-{3:3}, at: func_b+0x18/0x60

which lock already depends on the new lock.

the existing dependency chain (in reverse order) is:

-> #1 (&lock_b){+.+.}-{3:3}:
       lock_acquire+0x...
       mutex_lock+0x...
       func_c+0x30/0x80           ← func_c 先锁 lock_a 再锁 lock_b

-> #0 (&lock_a){+.+.}-{3:3}:
       lock_acquire+0x...
       mutex_lock+0x...
       func_a+0x20/0x80           ← func_a 先锁 lock_b 再锁 lock_a

Chain exists of: &lock_a --> &lock_b --> &lock_a
                 ↑ 环形依赖 = 死锁风险
```

### 6.2 lockdep 标注含义

```
{+.+.}  → {IN-SOFTIRQ, IN-HARDIRQ, IN-RECLAIM, HELD-IN-SOFTIRQ}
           + = 可在该上下文中使用
           - = 不可在该上下文中使用
           . = 未观测到在该上下文中使用

{3:3}   → 锁的嵌套深度: {子类:递归深度}
```

### 6.3 处理 lockdep 警告

```c
// 如果确认是误报: 使用 lockdep 注解
static struct lock_class_key my_lock_key;
lockdep_set_class(&my_lock, &my_lock_key);

// 嵌套锁标注 (同类型不同实例)
mutex_lock_nested(&parent->lock, SINGLE_DEPTH_NESTING);
mutex_lock_nested(&child->lock, SINGLE_DEPTH_NESTING + 1);
```

---

## 7. KCSAN 数据竞争检测

### 7.1 配置

```
CONFIG_KCSAN=y
CONFIG_KCSAN_STRICT=y       # 严格模式
# 需要 GCC 11+ 或 Clang 12+
```

### 7.2 报告示例

```
==================================================================
BUG: KCSAN: data-race in func_reader / func_writer

write to 0xffff000012345000 of 4 bytes by task 1234 on cpu 2:
 func_writer+0x20/0x40
 ...

read to 0xffff000012345000 of 4 bytes by task 5678 on cpu 0:
 func_reader+0x18/0x30
 ...

value changed: 0x00000001 -> 0x00000002
==================================================================
```

### 7.3 标记合法竞争

```c
// 有意的松散访问 (performance counter 等)
data_race(counter++);

// 使用 READ/WRITE_ONCE
WRITE_ONCE(shared_var, new_val);
val = READ_ONCE(shared_var);
```

---

## 8. 常见死锁模式分类

### 8.1 ABBA 死锁

```
线程 1: lock(A) → lock(B)
线程 2: lock(B) → lock(A)

修复: 统一加锁顺序，永远先 A 后 B
```

### 8.2 自死锁

```
irq_handler:   spin_lock(&lock)   ← 中断中获取锁
process_ctx:   spin_lock(&lock)   ← 进程上下文也获取同一锁
               → 中断打断进程上下文时死锁

修复: 进程上下文用 spin_lock_irqsave()
```

### 8.3 递归锁

```
func_a: mutex_lock(&lock) → func_b()
func_b: mutex_lock(&lock)   ← 同一线程再次获取同一 mutex → 死锁

修复: 拆分为两个锁, 或使用 mutex_trylock, 或重构调用关系
```

### 8.4 锁顺序反转 (跨子系统)

```
子系统 A: lock(fs_lock) → lock(dev_lock)
子系统 B: lock(dev_lock) → lock(fs_lock)

修复: 定义全局锁层次(lock hierarchy), 所有代码遵守
```

---

## 9. 内核内存布局参考

### 9.1 ARM64 虚拟地址空间 (48-bit, 4KB 页)

| 地址范围 | 大小 | 用途 |
|---------|------|------|
| `0x0000000000000000 - 0x0000ffffffffffff` | 256TB | 用户空间 |
| *hole* | - | 未映射 |
| `0xffff000000000000 - 0xffff7fffffffffff` | 128TB | 内核线性映射 |
| `0xffff800000000000 - 0xffffffffffffffff` | 128TB | vmalloc/modules/fixmap 等 |

### 9.2 快速判断地址类型

```bash
# 崩溃时看地址前缀
0x0000...  → 用户空间地址 (在内核态访问 = bug)
0xffff0000...  → 内核线性映射 (物理内存直接映射)
0xffff8000...  → vmalloc / 模块 / ioremap
0x00000000...1x → NULL 指针 + 偏移 (struct member offset)
0xdead...  → 内核毒化值 (已释放内存)
0x5a5a...  → SLUB poison (已分配未初始化)
0x6b6b...  → SLUB poison (已释放)
```

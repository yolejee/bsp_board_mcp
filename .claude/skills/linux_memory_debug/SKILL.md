---
name: linux_memory_debug
description: "通用 Linux 内核内存问题调试技能，不限于任何特定 SoC 平台。覆盖 OOM killer 分析与调优、内存泄漏检测 (kmemleak/valgrind/slub_debug)、KASAN/KFENCE 越界与 use-after-free 检测、/proc/meminfo 内存状态分析、slab/slub 分配器调试、vmalloc 追踪、CMA/DMA 内存管理、page allocation failure、内存碎片化分析、memblock 与 early boot 内存分配。触发关键词：内存调试、OOM、oom_kill、kmemleak、KASAN、KFENCE、内存泄漏、memory leak、内存越界、use-after-free、/proc/meminfo、/proc/buddyinfo、/proc/slabinfo、slabtop、kmalloc、vmalloc、page allocation failure、内存碎片、CMA、DMA 内存、dma-buf、memblock、reserved-memory、valgrind、AddressSanitizer、watermark、min_free_kbytes、hugepages、THP、swap、zram、内存回收、reclaim。当用户描述 Linux 内核层面的内存问题（OOM、泄漏、越界、内存不足、系统卡顿因内存引起等），都应触发本技能。"
---
<!-- ===== QUICK NAVIGATION ===== -->
| 快速导航 | 跳转链接 |
|---------|---------|
| OOM 问题 | [§1](#1-oom-killer-分析与调优) |
| 内存泄漏 | [§2](#2-内存泄漏检测) |
| 越界检测 | [§3](#3-内存越界与-use-after-free-检测) |
| 内存状态 | [§4](#4-内存状态分析) |
| Slab 调试 | [§5](#5-slab-分配器调试) |
| CMA/DMA | [§6](#6-cmadma-内存管理) |
| 碎片化 | [§7](#7-内存碎片化) |
| 内存预留 | [§8](#8-reserved-memory-与-memblock) |
| 水位调优 | [§9](#9-内存水位与回收) |
| 用户态工具 | [§10](#10-用户态内存调试工具) |
| 参考索引 | [§REF](#reference-index) |

---

## 诊断决策树
```
内存问题
├── 系统被 OOM 杀进程 → §1 OOM Killer 分析
├── /proc/meminfo 可用内存持续下降 → §2 内存泄漏检测
├── kernel 报 slab corruption / use-after-free → §3 KASAN/KFENCE
├── "page allocation failure" 日志 → §7 内存碎片化
├── 想了解系统内存分布 → §4 内存状态分析 + §5 Slab 调试
├── CMA alloc failed / dma_alloc 失败 → §6 CMA/DMA
├── 预留内存配置问题 → §8 Reserved Memory
├── 想调优 min_free_kbytes / watermark → §9 水位与回收
└── 用户态进程内存问题 → §10 Valgrind / ASan
```

---

## §1 OOM Killer 分析与调优

### 1.1 OOM 日志格式解读
```
OOM 触发时内核输出信息分为 3 部分:

1) 触发者信息:
   "<进程名> invoked oom-killer: gfp_mask=0x..., order=N, oom_score_adj=0"
   → gfp_mask: 分配标记 (GFP_KERNEL / GFP_DMA 等)
   → order: 请求的连续页面 2^N, order-0 = 4KB
   → oom_score_adj: 触发者自身的 OOM 评分调整值

2) 内存统计:
   "Mem-Info:" 显示 zone 信息和 free pages
   "Active / Inactive / Dirty / Writeback" 页面统计
   "Slab / SReclaimable / SUnreclaim" slab 统计
   "Node 0 normal free:..." 各 zone 详细状态

3) 选中被杀进程:
   "Out of memory: Killed process <PID> (<进程名>) total-vm:xxxkB, ..."
   → rss: 实际使用物理内存
   → oom_score_adj: 被选中原因之一
```

### 1.2 OOM 评分机制
```bash
# 查看进程的 OOM 评分:
cat /proc/<PID>/oom_score        # 实际评分 (0-1000)
cat /proc/<PID>/oom_score_adj    # 调整值 (-1000 到 1000)

# 保护关键进程不被 OOM 杀:
echo -1000 > /proc/<PID>/oom_score_adj   # 完全豁免

# 优先杀某进程:
echo 1000 > /proc/<PID>/oom_score_adj    # 最高优先被杀
```

### 1.3 OOM 相关内核参数
```bash
# overcommit 策略:
sysctl -w vm.overcommit_memory=0   # 0=启发式(默认), 1=始终允许, 2=严格
sysctl -w vm.overcommit_ratio=50   # 当 overcommit_memory=2 时的物理内存百分比

# panic_on_oom:
sysctl -w vm.panic_on_oom=0        # 0=杀进程(默认), 1=直接 panic
                                    # 嵌入式看门狗场景可设 1 触发重启

# oom_dump_tasks:
sysctl -w vm.oom_dump_tasks=1      # OOM 时 dump 所有进程内存信息
```

---

## §2 内存泄漏检测

### 2.1 kmemleak (内核态泄漏检测)
```bash
# 内核配置:
CONFIG_DEBUG_KMEMLEAK=y
CONFIG_DEBUG_KMEMLEAK_EARLY_LOG_SIZE=4000

# 使用:
mount -t debugfs nodev /sys/kernel/debug
cat /sys/kernel/debug/kmemleak          # 查看泄漏报告
echo scan > /sys/kernel/debug/kmemleak  # 手动触发扫描
echo clear > /sys/kernel/debug/kmemleak # 清除当前记录

# 报告解读:
# unreferenced object 0xffff... (size 128):
#   comm "xxx", pid 123, jiffies ...
#   backtrace:
#     [<addr>] kmalloc+0x.../0x...
#     [<addr>] my_driver_func+0x.../0x...
# → backtrace 显示分配路径, 从中找到泄漏的分配点
```

### 2.2 slub_debug 检测内存问题
```bash
# 启动参数:
# slub_debug=FZPU                   # 全局开启
# slub_debug=FZ,kmalloc-128         # 仅对特定 cache

# 标记含义:
# F = 检查释放后的 magic pattern (检测 use-after-free)
# Z = 填充 red zone (检测溢出)
# P = 填充 poison pattern (写入 0x5a/0x6b)
# U = 记录用户调用栈 (需要 CONFIG_STACKTRACE)

# 查看 slub 调试信息:
cat /sys/kernel/slab/<cache_name>/alloc_calls  # 分配调用栈统计
cat /sys/kernel/slab/<cache_name>/free_calls   # 释放调用栈统计
```

### 2.3 /proc/meminfo 趋势监控
```bash
# 简单的周期性内存监控脚本:
while true; do
  echo "=== $(date) ==="
  grep -E "MemFree|MemAvail|Slab|SUnreclaim|Committed_AS" /proc/meminfo
  sleep 60
done | tee /tmp/memwatch.log

# 分析: 如果 SUnreclaim 持续增长, 说明内核 slab 泄漏
# 使用 slabtop 定位具体是哪个 cache 在增长
```

---

## §3 内存越界与 Use-After-Free 检测

### 3.1 KASAN (Kernel Address Sanitizer)
```bash
# 内核配置:
CONFIG_KASAN=y
CONFIG_KASAN_GENERIC=y    # 通用模式 (软件, 性能开销 ~2x)
# 或
CONFIG_KASAN_SW_TAGS=y    # ARM64 标签模式 (性能更好, 仅 arm64)
CONFIG_KASAN_HW_TAGS=y    # ARM64 MTE 硬件支持 (最小开销)

# KASAN 报告格式:
# BUG: KASAN: slab-out-of-bounds in my_func+0x.../0x...
# Write of size 4 at addr ffff... by task xxx/123
#   → "slab-out-of-bounds": 越界写
#   → "use-after-free": 释放后使用
#   → "stack-out-of-bounds": 栈溢出
#   → "global-buffer-overflow": 全局变量溢出
#
# Allocated by task xxx/123:  (分配时栈)
# Freed by task yyy/456:      (释放时栈, 仅 UAF)

# KASAN 会在检测到问题时自动 dump 详细诊断并 BUG()
```

### 3.2 KFENCE (Kernel Electric Fence)
```bash
# 内核配置 (轻量级, 适合生产环境):
CONFIG_KFENCE=y
CONFIG_KFENCE_SAMPLE_INTERVAL=100  # 采样间隔 (ms)

# 特点:
# - 极低性能开销 (< 1%), 适合生产环境
# - 采样式检测, 不能保证 100% 捕获
# - 检测 out-of-bounds, use-after-free, invalid-free
# - 无需特殊启动参数
#
# 报告格式与 KASAN 类似:
# BUG: KFENCE: out-of-bounds read in ...
```

---

## §4 内存状态分析

### 4.1 /proc/meminfo 关键字段
```
MemTotal:        内存总量
MemFree:         完全未使用的内存
MemAvailable:    可用内存估值 (含可回收) ★ 最有用的指标
Buffers:         块设备读写缓冲
Cached:          页缓存 (文件数据缓存)
SwapCached:      交换缓存
Active:          最近使用的内存 (不易回收)
Inactive:        较久未用的内存 (优先回收)
Slab:            内核 slab 分配器总量
SReclaimable:    slab 中可回收部分 (dentry/inode 缓存等)
SUnreclaim:      slab 中不可回收部分 ★ 泄漏排查重点
Committed_AS:    已承诺的虚拟内存总量
VmallocUsed:     vmalloc 已用量
CmaTotal:        CMA 区域总量
CmaFree:         CMA 区域空闲量
```

### 4.2 Zone 与 buddyinfo 分析
```bash
# 查看各 zone 内存分布:
cat /proc/buddyinfo
# Node 0, zone   Normal  128  64  32  16   8   4   2   1   0   0   0
#                  ↑ 各 order 可用的连续空闲块数
# order-0=4KB, order-1=8KB, ..., order-10=4MB
# 高 order 全是 0 → 内存碎片严重

# 查看更详细的分页信息:
cat /proc/pagetypeinfo

# 查看 vmstat 统计:
cat /proc/vmstat | grep -E "pgalloc|pgfree|pgfault|pgscan|pgsteal|compact"
```

---

## §5 Slab 分配器调试

### 5.1 slabtop 与 /proc/slabinfo
```bash
# 实时查看 slab 使用状况:
slabtop -s c    # 按 cache 大小排序
slabtop -s a    # 按活跃对象数排序

# /proc/slabinfo 格式:
# name    <active_objs> <num_objs> <objsize> <objperslab> <pagesperslab>
# 重点关注:
# - 持续增长的 cache → 可能泄漏
# - 大对象数的 cache → 内存消耗大户

# 定位泄漏:
# 周期记录 → 对比增长 → 找出持续增长的 slab cache → 用 slub_debug=U 记录调用栈
```

### 5.2 slab 常见问题
```
slab corruption / Redzone overwritten:
→ 对象越界写. 用 slub_debug=FZ 或 KASAN 定位

Poison overwritten:
→ 释放后被改写 (use-after-free). 用 slub_debug=FP 或 KASAN 定位

Object already free:
→ double free. 用 slub_debug=FU 查看 free 调用栈
```

---

## §6 CMA/DMA 内存管理

### 6.1 CMA (Contiguous Memory Allocator)
```bash
# 查看 CMA 状态:
cat /proc/meminfo | grep -i cma
# CmaTotal:      32768 kB   (DTS 或 cmdline 中设定的大小)
# CmaFree:       16384 kB

# DTS 配置:
# reserved-memory {
#     cma: linux,cma {
#         compatible = "shared-dma-pool";
#         reusable;
#         size = <0x0 0x2000000>;  /* 32MB */
#         linux,cma-default;
#     };
# };

# 或 bootargs: cma=32M

# 调试:
cat /sys/kernel/debug/cma/cma-<name>/count   # 总页数
cat /sys/kernel/debug/cma/cma-<name>/used    # 已用页数
echo 1 > /sys/kernel/debug/cma/cma-<name>/alloc  # 测试分配

# CMA 分配失败常见原因:
# 1) CMA 区域过小
# 2) CMA 区域被 movable 页面占用且无法迁移 (碎片化)
# 3) pinned pages 在 CMA 区域内
```

### 6.2 DMA-BUF 与 ION
```bash
# DMA-BUF 调试:
cat /sys/kernel/debug/dma_buf/bufinfo      # 查看所有 dma-buf

# ION (旧的嵌入式分配器, 正在被 DMA-BUF heap 取代):
cat /sys/kernel/debug/ion/heaps/<heap_name>  # 查看 ION heap

# dmabuf 泄漏排查:
# 周期性记录 bufinfo → 找出持续增长的 exporter → 定位未释放的 fd
```

---

## §7 内存碎片化

### 7.1 碎片化诊断
```bash
# buddyinfo 检查:
cat /proc/buddyinfo
# 如果高 order (order-4 及以上) 的空闲块数为 0, 说明碎片严重
# 意味着无法分配大的连续物理内存

# extfrag 指数 (fragmentation index):
cat /sys/kernel/debug/extfrag/extfrag_index
# 接近 1.0 → 碎片化严重, 接近 0 → 内存不足

# vmstat 查看 compact 活动:
cat /proc/vmstat | grep compact
```

### 7.2 碎片化缓解
```bash
# 手动触发内存规整 (compaction):
echo 1 > /proc/sys/vm/compact_memory

# 释放页缓存/slab:
echo 1 > /proc/sys/vm/drop_caches      # 释放 pagecache
echo 2 > /proc/sys/vm/drop_caches      # 释放 slab
echo 3 > /proc/sys/vm/drop_caches      # 都释放

# 碎片化预防:
sysctl -w vm.min_free_kbytes=<值>       # 提高保留水位
sysctl -w vm.extfrag_threshold=500      # compaction 激进度阈值 (默认 500)
```

---

## §8 Reserved Memory 与 Memblock

### 8.1 DTS 中的内存预留
```dts
reserved-memory {
    #address-cells = <2>;
    #size-cells = <2>;
    ranges;

    /* 静态预留 (固定地址, 不可被内核使用) */
    my_reserved: buffer@10000000 {
        reg = <0x0 0x10000000 0x0 0x1000000>;  /* 16MB @ 0x10000000 */
        no-map;  /* 不映射到内核地址空间 */
    };

    /* 动态预留 CMA */
    cma_reserved: linux,cma {
        compatible = "shared-dma-pool";
        reusable;     /* 可被 movable 页面临时借用 */
        size = <0x0 0x4000000>;  /* 64MB */
        linux,cma-default;
    };
};
```

### 8.2 Memblock 调试
```bash
# 查看 early boot 内存分配:
# bootargs 加: memblock=debug
# 会在 dmesg 中打印 memblock 的所有 add/reserve 操作

# 查看最终 memblock 状态:
cat /sys/kernel/debug/memblock/memory    # 所有可用内存区域
cat /sys/kernel/debug/memblock/reserved  # 所有预留区域
```

---

## §9 内存水位与回收

### 9.1 水位 (Watermark) 机制
```
每个 zone 有 3 个水位线:
  min  → 低于此值: 直接回收 (direct reclaim), 可能阻塞进程
  low  → 低于此值: 唤醒 kswapd 后台回收
  high → 高于此值: kswapd 停止回收

调整:
sysctl -w vm.min_free_kbytes=16384     # 设置 min 水位 (影响 low/high)
# min_free_kbytes 越大 → 预留越多 → 高 order 分配更容易成功
# 但过大会浪费内存

嵌入式建议: 内存 512MB 设 8192, 1GB 设 16384, 2GB+ 设 32768
```

### 9.2 kswapd 与直接回收
```bash
# 监控回收活动:
cat /proc/vmstat | grep -E "pgscan|pgsteal|kswapd|direct"
# pgscan_kswapd   → kswapd 扫描页数 (正常后台回收)
# pgscan_direct   → 直接回收扫描页数 (性能影响大, 应尽量减少)
# pgsteal_kswapd  → kswapd 回收成功页数
# pgsteal_direct  → 直接回收成功页数

# 如果 pgscan_direct 很大 → 内存压力大或 min_free_kbytes 太小
```

### 9.3 Swap 与 ZRAM
```bash
# 嵌入式常用 ZRAM 压缩内存:
echo lz4 > /sys/block/zram0/comp_algorithm    # 压缩算法
echo 128M > /sys/block/zram0/disksize         # 压缩磁盘大小
mkswap /dev/zram0
swapon /dev/zram0

# 调整 swappiness:
sysctl -w vm.swappiness=60      # 默认 60, 嵌入式可调 10-30 减少 swap
```

---

## §10 用户态内存调试工具

### 10.1 Valgrind
```bash
# 内存泄漏检测:
valgrind --tool=memcheck --leak-check=full --track-origins=yes ./my_app

# 常见输出:
# "definitely lost"   → 确定泄漏 ★ 必须修复
# "indirectly lost"   → 间接泄漏 (被 definitely lost 引用)
# "possibly lost"     → 可能泄漏 (可能是误报)
# "still reachable"   → 进程结束时仍有引用 (通常不是问题)

# 调用栈分析:
valgrind --tool=memcheck --leak-check=full --num-callers=20 ./my_app

# 注意: arm 嵌入式需交叉编译 valgrind 或使用 qemu user mode
```

### 10.2 AddressSanitizer (ASan)
```bash
# 编译选项:
gcc -fsanitize=address -fno-omit-frame-pointer -g my_app.c -o my_app

# 检测类型: heap-buffer-overflow, stack-buffer-overflow,
#           use-after-free, double-free, memory-leaks

# 环境变量控制:
ASAN_OPTIONS=detect_leaks=1:log_path=/tmp/asan.log ./my_app
```

---

## Reference Index

| 参考文件 | 内容概要 |
|---------|---------|
| [memory_leak_detection.md](references/memory_leak_detection.md) | 内核态/用户态内存泄漏检测完整手册, kmemleak 深入使用, slub_debug 高级用法, valgrind 交叉编译 |
| [oom_analysis.md](references/oom_analysis.md) | OOM Killer 完整分析, oom_score 计算算法, cgroup 内存限制, memcg OOM 处理, OOM 日志完整模板 |
| [memory_subsystem.md](references/memory_subsystem.md) | Linux 内存子系统架构, 页分配器, slab, vmalloc, CMA, DMA mapping, IOMMU, 内存热插拔 |

# Linux 内存子系统架构

## 1. 内存管理总体架构

```
用户态请求 (malloc/mmap)
        ↓
   系统调用 (brk / mmap)
        ↓
┌───────────────────────────────────────────────┐
│              虚拟内存管理 (VMA)                  │
│  vm_area_struct → 描述进程的虚拟地址区间          │
│  page fault → 按需分配物理页                     │
├───────────────────────────────────────────────┤
│              页分配器 (Buddy System)             │
│  管理 order-0 到 order-10 的连续物理页分配        │
│  zone: DMA / DMA32 / Normal / Movable / HighMem │
├───────────────────────────────────────────────┤
│              Slab 分配器 (SLUB)                  │
│  小对象 (< PAGE_SIZE) 分配: kmalloc / kmem_cache │
│  从 buddy 获取整页再细分为小对象                  │
├───────────────────────────────────────────────┤
│              连续内存分配器                       │
│  CMA: 可回收的连续大块分配                       │
│  vmalloc: 虚拟连续但物理不连续                    │
├───────────────────────────────────────────────┤
│              页回收与交换                         │
│  kswapd / direct reclaim / compaction           │
│  LRU 链表: Active/Inactive × Anon/File          │
│  swap / zram                                    │
└───────────────────────────────────────────────┘
```

## 2. Zone 划分

```
ARM/ARM64 典型 zone 划分:

ARM32 (32位, 有 HighMem):
  ZONE_DMA:     0 ~ 16MB (ISA DMA 设备)
  ZONE_NORMAL:  16MB ~ 760MB (内核直接映射)
  ZONE_HIGHMEM: 760MB ~ 物理内存上限 (需要临时映射)

ARM64 (64位, 无 HighMem):
  ZONE_DMA:     0 ~ 1GB 或 4GB (DMA 设备可寻址范围)
  ZONE_DMA32:   0 ~ 4GB (32位 DMA 设备)
  ZONE_NORMAL:  4GB ~ 物理内存上限

嵌入式常见:
  大多数嵌入式 ARM64 SoC 只有 ZONE_DMA32 和 ZONE_NORMAL
  内存 ≤ 4GB 时可能只有 ZONE_DMA32
```

## 3. 页分配器 (Buddy System) 详解

```
Buddy 系统管理空闲页面:
- 用二叉树结构组织空闲页面
- 分配时: 找到满足 order 的最小空闲块, 必要时拆分
- 释放时: 检查伙伴 (buddy) 是否也空闲, 可以合并则升级 order
- 保证分配结果是 2^order 页对齐的连续物理内存

/proc/buddyinfo 解读:
  Node 0, zone   Normal  256  128  64  32  16  8  4  2  1  0  0
  // 每列对应 order-0 到 order-10 的空闲块数
  // order-0: 256 个 4KB 块        = 1MB
  // order-4: 16 个 64KB 块       = 1MB
  // order-10: 0 个 4MB 块         = 0 (无法分配 4MB 连续)
```

## 4. Slab/SLUB 分配器

```
用途: 高效管理频繁分配/释放的小对象

3 种实现 (编译时选择):
- SLAB: 经典实现, 复杂但缓存友好 (较少使用)
- SLUB: 现代默认实现, 简洁高效 ★ 最常用
- SLOB: 极简实现, 用于极小内存系统

关键调试接口:
  /proc/slabinfo           # 所有 slab cache 统计
  /sys/kernel/slab/        # 每个 cache 的详细控制
  slabtop                  # top 式实时查看

常用 kmalloc cache:
  kmalloc-8, kmalloc-16, kmalloc-32, ..., kmalloc-8192
  kmalloc-rcl-* (可回收类)
  kmalloc-cg-* (cgroup 计费类)
```

## 5. Vmalloc

```
特点: 虚拟地址连续, 物理地址可能不连续
用途: 大块但不需要物理连续的内核内存分配
地址范围: VMALLOC_START ~ VMALLOC_END (平台相关)

调试:
  cat /proc/vmallocinfo
  # 输出: 起始地址-结束地址  大小  调用者  页数  物理页列表

常见 vmalloc 用户:
  - 模块代码段 (.text)
  - ioremap 映射
  - vmap (将已有物理页映射到虚拟连续空间)
```

## 6. DMA 内存映射

```
DMA 映射类型:

1. Consistent/Coherent DMA (一致性):
   dma_alloc_coherent(dev, size, &dma_handle, GFP_KERNEL)
   → CPU 和设备看到一致的内容, 无需手动 sync
   → 通常从 CMA 分配

2. Streaming DMA (流式):
   dma_map_single(dev, vaddr, size, direction)
   → 高性能, 但需要手动 dma_sync_*
   → 不需要连续物理内存

3. DMA Pool:
   dma_pool_create() / dma_pool_alloc()
   → 适合频繁的小块一致性 DMA 分配

IOMMU 模式:
   有 IOMMU 时, dma_map 可以将非连续物理内存映射为设备看到的连续地址
   → 减少对 CMA 的依赖
```

## 7. 内存热插拔 (嵌入式少用)

```
CONFIG_MEMORY_HOTPLUG=y
CONFIG_MEMORY_HOTREMOVE=y

# 查看内存块:
ls /sys/devices/system/memory/

# 下线内存块:
echo offline > /sys/devices/system/memory/memory32/state

# 上线内存块:
echo online > /sys/devices/system/memory/memory32/state

# 嵌入式场景: 通常不涉及, 但在虚拟化 / 大型服务器环境中有用
```

# linux_memory_debug — Linux 内核内存问题调试技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`linux_memory_debug` 是一个**多平台通用**的 Linux 内核内存问题调试技能，专注于解决各类内存调试问题：OOM Killer 分析与调优、内存泄漏检测 (kmemleak / slub_debug / valgrind)、KASAN/KFENCE 越界与 use-after-free 检测、/proc/meminfo 系统内存状态分析、Slab 分配器调试、CMA/DMA 内存管理、内存碎片化诊断与优化等。

## 适用平台

| 平台 | 芯片示例 | 适用性 |
|------|---------|-------|
| Rockchip 瑞芯微 | RK3588 / RK3568 / RK3566 | ✅ |
| AllWinner 全志 | A64 / H616 / T527 | ✅ |
| NXP i.MX | i.MX8M / i.MX6 | ✅ |
| TI Sitara | AM335x / AM62x | ✅ |
| STM32MP | STM32MP157 / STM32MP135 | ✅ |
| Broadcom | BCM2711 (RPi4) | ✅ |
| RISC-V | StarFive JH7110 / T-Head | ✅ |
| Qualcomm | QCS404 / Snapdragon | ✅ |

> 凡运行 Linux 4.x+ 内核的嵌入式平台均适用。

## 功能说明

### 1. OOM 分析与调优
- **问题**: 系统触发 OOM Killer 杀进程
- **方法**: 解读 OOM 日志结构, 分析 oom_score 评分, 调整 overcommit 策略, 保护关键进程

### 2. 内存泄漏检测
- **问题**: 系统内存持续下降, 最终 OOM 或性能劣化
- **工具**: kmemleak (内核态), slub_debug (slab 级), valgrind (用户态), /proc/meminfo 趋势分析

### 3. 内存越界 / Use-After-Free 检测
- **问题**: 内存写越界导致数据损坏或随机崩溃
- **工具**: KASAN (开发环境), KFENCE (生产环境), slub_debug=FZ

### 4. 内存状态分析
- **方法**: /proc/meminfo, /proc/buddyinfo, /proc/slabinfo, /proc/vmstat 综合分析内存使用分布

### 5. CMA/DMA 内存管理
- **问题**: CMA 分配失败, DMA-BUF 泄漏
- **方法**: CMA debugfs, dma_buf/bufinfo, reserved-memory DTS 配置

### 6. 碎片化与水位调优
- **问题**: 高 order 分配失败, kswapd CPU 占用高
- **方法**: buddyinfo 碎片分析, compaction, min_free_kbytes 调优, ZRAM 配置

## 触发方式

当用户描述以下类型的问题时，本技能会被自动触发：

- 提到 OOM、内存不足、进程被杀
- 提到内存泄漏 (memory leak)、可用内存持续下降
- 提到 KASAN、KFENCE、use-after-free、内存越界
- 提到 /proc/meminfo、slabtop、slabinfo 等工具
- 提到 CMA 分配失败、DMA 内存问题
- 提到内存碎片化、page allocation failure、高 order 分配
- 提到 valgrind、ASan、内存调试工具
- 提到 min_free_kbytes、watermark、swap、ZRAM

## 文件结构

```
linux_memory_debug/
├── SKILL.md                                 # 主技能文件
├── README.md                                # 本说明文档
└── references/
    ├── memory_leak_detection.md             # 泄漏检测完整手册
    ├── oom_analysis.md                      # OOM 完整分析手册
    └── memory_subsystem.md                  # 内存子系统架构
```

## 文件加载机制

- `SKILL.md` 在技能触发时**自动加载**，提供完整的诊断决策树和常用命令
- `references/*.md` 按需加载，当 SKILL.md 中的内容不够详细时引用

## 使用示例

### 示例 1: OOM 问题排查
> 用户: "我的系统运行一段时间后会触发 OOM killer，日志显示 oom_score_adj=0"

技能响应：解读 OOM 日志, 分析 oom_score 评分和 overcommit 配置, 给出 oom_score_adj 保护方案。

### 示例 2: 内核内存泄漏
> 用户: "/proc/meminfo 显示 SUnreclaim 持续增长"

技能响应：引导使用 slabtop 定位增长的 cache, 开启 kmemleak 或 slub_debug=FZU 捕获泄漏调用栈。

### 示例 3: CMA 分配失败
> 用户: "dma_alloc_coherent 返回 NULL, CMA alloc failed"

技能响应：检查 CMA 区域大小和碎片化状态, 分析 CMA debugfs, 调整 CMA 配置或预留策略。

## 知识来源

- Linux kernel Documentation/admin-guide/mm/
- Linux kernel Documentation/dev-tools/kasan.rst / kfence.rst / kmemleak.rst
- /proc/meminfo 内核源码 (fs/proc/meminfo.c)
- Valgrind 官方文档
- 嵌入式 Linux 内存调优实践经验

## License

MIT License — 详见仓库根目录 LICENSE 文件

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

# linux_kernel_debug  通用 Linux 内核调试技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`linux_kernel_debug` 是一个**平台无关**的 Linux 内核调试 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户遇到内核崩溃、调试打印、动态追踪、内存错误、锁问题等内核层面的调试需求时，AI 会自动加载本技能，提供系统化的诊断流程和技术指导。

## 适用平台

本技能覆盖所有运行 Linux 内核的嵌入式及桌面平台：

| 厂商 | 代表 SoC/架构 |
|------|-------------|
| ARM64 | Rockchip/全志/NXP i.MX/TI/Qualcomm/Samsung/ST |
| ARM32 | STM32/OMAP/Broadcom BCM |
| x86_64 | Intel/AMD 通用 Linux |
| RISC-V | StarFive/SiFive/T-Head |
| MIPS | MediaTek/Ingenic |

## 功能说明

### 功能 1：内核崩溃分析

分析 Oops/Panic 日志，定位崩溃根因。

**你可以这样提问：**
- "内核 Oops 日志贴给你，帮我分析哪个函数出错了"
- "Kernel Panic - not syncing 怎么排查？"
- "Unable to handle kernel NULL pointer dereference 是什么问题？"
- "帮我用 addr2line 定位这个崩溃地址"

**AI 会返回：**
- Oops 日志逐字段解读
- addr2line/faddr2line 定位命令
- 崩溃模式识别和常见修复方案

### 功能 2：动态追踪与 ftrace

使用 ftrace/kprobes/trace-cmd 追踪内核函数调用和事件。

**你可以这样提问：**
- "帮我用 ftrace 追踪 i2c_transfer 函数"
- "怎么用 trace event 查看中断延迟？"
- "帮我写一个 kprobe 脚本抓取某函数的参数"
- "trace-cmd 怎么用？帮我录一段系统调用"

**AI 会返回：**
- 完整的 ftrace 操作步骤（debugfs 手动操作或 trace-cmd 命令）
- kprobe 语法和嵌入式平台的寄存器映射
- trace event 过滤和触发条件设置

### 功能 3：内存与锁调试

检测内存越界、泄漏、use-after-free、死锁、lockdep 告警等。

**你可以这样提问：**
- "KASAN 报告 slab-out-of-bounds 怎么看？"
- "怀疑内核内存泄漏，怎么用 KMEMLEAK 检测？"
- "lockdep 报 circular dependency 怎么解？"
- "系统 soft lockup 是什么原因？"

**AI 会返回：**
- 调试工具开启方法（CONFIG 和启动参数）
- 报告逐字段解读
- 常见错误模式和修复思路

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **内核调试 / kernel debug / printk / dmesg / Oops / Panic** 等关键词
- 提到追踪关键词：**ftrace / kprobes / trace-cmd / function_graph / trace event**
- 提到内存调试：**KASAN / KMEMLEAK / SLUB debug / page_owner**
- 提到锁调试：**lockdep / hung task / soft lockup / RCU stall / 死锁**
- 提到崩溃分析：**crash dump / kdump / vmcore / ramdump / pstore**
- 描述内核层面的问题（call trace、模块调试、驱动 probe 失败的内核侧分析等）

## 文件结构

```
linux_kernel_debug/
 SKILL.md                                 # 主技能文件 (AI 自动加载, ~550 行)
 README.md                                # 本说明文档 (供人阅读)
 references/                              # 深入参考资料 (AI 按需加载)
     printk_dynamic_debug.md              # printk 体系、日志缓冲区、console、earlycon、dynamic debug
     ftrace_kprobes.md                    # ftrace 全追踪器、trace event、kprobe 语法、trace-cmd、BPF
     oops_panic_crash.md                  # Oops 结构解析、ARM64 寄存器、kdump、crash 工具、pstore
     memory_lock_debug.md                 # KASAN 报告解读、KMEMLEAK、SLUB debug、lockdep、KCSAN、死锁模式
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含核心知识（诊断决策树、各工具速查、CONFIG 推荐）
- **references/**：AI 根据具体问题按需加载。例如：
  - 用户问 printk/dmesg → 加载 `printk_dynamic_debug.md`
  - 用户要用 ftrace/kprobes → 加载 `ftrace_kprobes.md`
  - 用户分析 Oops/Panic → 加载 `oops_panic_crash.md`
  - 用户调试内存/锁问题 → 加载 `memory_lock_debug.md`

## 使用示例

### 示例 1：分析 Oops 日志

**用户提问：**
> 内核日志出现 Unable to handle kernel NULL pointer dereference at virtual address 0000000000000010，帮我分析

**AI 行为：**
1. 自动触发 `linux_kernel_debug` 技能
2. 识别为 NULL 指针 + 偏移量访问（结构体成员偏移 0x10）
3. 提供 addr2line/faddr2line 命令定位出错源码行
4. 建议检查指针初始化和错误路径

### 示例 2：追踪 I2C 通信问题

**用户提问：**
> I2C 设备有时候读到错误数据，想用 ftrace 看看内核里 I2C 传输过程

**AI 行为：**
1. 提供 i2c trace event 的启用命令
2. 给出过滤特定 I2C adapter/地址的方法
3. 解释 trace 输出中各字段含义

### 示例 3：内核内存泄漏排查

**用户提问：**
> 系统运行两天后可用内存越来越少，怀疑内核内存泄漏

**AI 行为：**
1. 提供 KMEMLEAK 启用方法和扫描命令
2. 给出 /proc/meminfo + slabinfo 的对比分析方法
3. 如果发现泄漏，指导用调用栈定位泄漏源

## 知识来源

本技能的知识来源于：
- Linux 内核官方文档 `Documentation/admin-guide/` 和 `Documentation/dev-tools/`
- Rockchip 官方调试文档（DEBUG / PERF 系列）
- 内核源码 `kernel/trace/`、`mm/kasan/`、`lib/dynamic_debug.c` 等
- LWN.net 和 KernelNewbies 社区技术文章

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

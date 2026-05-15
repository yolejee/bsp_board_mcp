# linux_boot_debug — 通用 Linux 启动流程调试与开机优化技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`linux_boot_debug` 是一个**平台无关**的 Linux 启动流程调试与开机速度优化 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户遇到 Linux 系统启动失败、串口日志分析、开机速度优化等需求时，AI 会自动加载本技能，提供从 Bootloader 到 Kernel 到 Init 到 Userspace 的全流程诊断和优化指导。

## 适用平台

本技能覆盖所有运行 Linux 内核的嵌入式平台，不含特定 SoC 的 Bootloader 细节：

| 平台 | 代表 SoC |
|------|---------|
| Rockchip | RK3566/RK3568/RK3588/RK3399/PX30 |
| 全志 Allwinner | A64/H6/H616/D1 |
| NXP | i.MX6/i.MX8/i.MX9 |
| TI | AM335x/AM62x/AM64x |
| ST | STM32MP1/STM32MP2 |
| Broadcom | BCM2835 (Raspberry Pi) |
| RISC-V | StarFive/SiFive/T-Head |
| Qualcomm | QCS/QCM/Snapdragon |

## 功能说明

### 功能 1：启动失败诊断

分析启动过程中各阶段的失败原因，提供系统化排查方案。

**你可以这样提问：**
- "串口日志这里 kernel panic 了，帮我分析"
- "系统起不来，卡在内核阶段不动"
- "rootfs 挂载失败，报 VFS: Cannot open root device"
- "DTB 加载失败怎么排查？"
- "init 找不到是什么原因？"

**AI 会返回：**
- 根据错误信息定位到具体阶段
- 系统化排查步骤和调试命令
- 常见错误的已知修复方案

### 功能 2：串口日志分析

帮助用户分析和理解串口启动日志的每个阶段。

**你可以这样提问：**
- "帮我分析这段串口日志，看哪里有问题"
- "串口完全没输出怎么排查？"
- "earlycon 怎么配置？"
- "怎么从日志中找到启动卡住的位置？"

### 功能 3：开机速度优化

系统化的开机时间优化方案。

**你可以这样提问：**
- "开机时间 20 秒太慢了，怎么优化？"
- "哪些 initcall 最耗时？怎么看？"
- "systemd 启动哪些服务最慢？"
- "内核压缩方式用哪种最快？"
- "怎么做到 3 秒快速开机？"

**AI 会返回：**
- 各阶段耗时分析方法
- 具体的优化手段和预期收益
- 优先级排序的优化建议

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **启动调试 / boot debug / 开机慢 / 启动慢 / boot time / 快速启动** 等关键词
- 提到启动失败：**kernel panic on boot / 无法启动 / 起不来 / 引导失败** 等
- 提到串口分析：**串口日志 / serial log / boot log / earlycon / console** 等
- 提到启动流程：**initcall / bootargs / rootfs / init / systemd-analyze** 等
- 提到开机优化：**bootchart / bootgraph / initcall_debug / critical-chain** 等
- 用户粘贴串口启动日志并询问问题

## 文件结构

```
linux_boot_debug/
 SKILL.md                                  # 主技能文件 (AI 自动加载)
 README.md                                 # 本说明文档 (供人阅读)
 references/                               # 深入参考资料 (AI 按需加载)
     boot_flow_analysis.md                 # 完整启动流程深度分析
     boot_optimization.md                  # 开机速度优化全攻略
     boot_failure_diagnosis.md             # 启动失败完整诊断手册
```

### 文件加载机制

- **SKILL.md**：AI 触发技能时自动加载，包含核心诊断流程和速查表
- **references/**：AI 根据具体问题按需加载。例如：
  - 用户想了解启动流程 → 加载 `boot_flow_analysis.md`
  - 用户优化开机速度 → 加载 `boot_optimization.md`
  - 用户遇到启动失败 → 加载 `boot_failure_diagnosis.md`

## 使用示例

### 示例 1：分析串口日志中的启动失败

**用户提问：**
> 串口日志显示 "VFS: Cannot open root device "mmcblk0p8""，起不来了

**AI 行为：**
1. 自动触发 `linux_boot_debug` 技能
2. 识别为 rootfs 挂载失败
3. 提供排查步骤：检查 bootargs root= 参数、分区号、存储驱动 CONFIG
4. 给出修复建议和临时 workaround

### 示例 2：优化开机时间

**用户提问：**
> 开机需要 25 秒，我想优化到 5 秒以内

**AI 行为：**
1. 提供各阶段时间测量方法
2. 给出 initcall 耗时分析命令
3. 列出 systemd-analyze 使用方法
4. 按优先级推荐优化手段和预期收益

### 示例 3：earlycon 配置

**用户提问：**
> 串口在内核阶段没有输出，U-Boot 是有的

**AI 行为：**
1. 指导检查 bootargs console= 参数
2. 提供 earlycon 配置方法
3. 列出常见 UART 控制器的 earlycon 参数格式

## 知识来源

本技能的知识来源于：
- Linux 内核文档 `Documentation/admin-guide/kernel-parameters.txt`
- Linux 内核源码 `init/main.c` (start_kernel / initcall 机制)
- systemd 文档 (systemd-analyze / bootchart)
- 嵌入式 Linux 社区开机优化实践
- 各 SoC 厂商的 Boot Time Optimization Guide

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

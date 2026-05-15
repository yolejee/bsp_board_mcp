# linux_low_power — Linux 低功耗与休眠唤醒调试技能

> **Version:** V1.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-07

## 概述

`linux_low_power` 是一个面向 Linux 嵌入式系统的低功耗与休眠唤醒调试 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Linux 系统休眠（Suspend/Hibernate）、唤醒源排查、Runtime PM、功耗测量与优化、Power Domain 管理等低功耗相关问题时，AI 会自动加载本技能，提供系统化的分析方法论和调试指导。

本技能不限于特定 SoC 平台，适用于所有运行 Linux 的嵌入式系统。同时针对 Rockchip 和 Android 平台提供了专门的参考文档。

## 适用平台

- **通用 Linux**：所有使用标准 Linux PM 框架的系统
- **SoC 平台**：Rockchip、Allwinner、NXP i.MX、TI Sitara、Qualcomm、MediaTek、STM32MP、Xilinx/Zynq 等
- **操作系统**：Linux、Android（含 Framework 层分析）

## 功能说明

### 功能 1：Suspend/Resume 流程分析

系统休眠/唤醒全流程的深度分析，定位失败原因和性能瓶颈。

**你可以这样提问：**
- "系统执行 echo mem > /sys/power/state 后没有反应"
- "suspend 时报错 dpm_run_callback 返回 -16"
- "Freezing of tasks failed，怎么回事？"
- "resume 后系统很久才能再次 suspend"

**AI 会返回：**
- Suspend 流程中失败阶段的定位和分析
- pm_test 分级测试方案
- 驱动回调问题的排查步骤
- Active 时长异常的分层分析方法

### 功能 2：唤醒源管理与定位

wakeup sources 框架的使用、唤醒源排查、意外唤醒定位。

**你可以这样提问：**
- "系统被什么唤醒的？"
- "怎么禁用某个设备的唤醒功能？"
- "wakeup_sources 里哪些字段是关键的？"
- "怎么防止系统被意外唤醒？"

**AI 会返回：**
- 唤醒源查看和管理命令
- wakeup_sources 各字段的含义解读
- 意外唤醒的排查流程
- wakeup_count 精确控制方法

### 功能 3：Runtime PM 调试

设备级 Runtime 电源管理的配置和调试。

**你可以这样提问：**
- "这个设备为什么不进入 runtime suspend?"
- "runtime_usage 一直大于 0 怎么办？"
- "怎么在驱动里正确使用 Runtime PM？"

**AI 会返回：**
- 设备 Runtime PM 状态检查方法
- 使用计数泄漏的排查
- 驱动代码中 Runtime PM 的正确用法模板
- autosuspend 配置指导

### 功能 4：功耗测量与优化

从硬件测量到软件优化的全链条功耗分析。

**你可以这样提问：**
- "怎么测量待机功耗？"
- "待机电流太大，怎么排查？"
- "哪些模块在休眠时还在耗电？"

**AI 会返回：**
- 硬件测量方法（串联电阻、电流探头、功耗分析仪）
- 软件辅助分析（PD/Clock/Regulator 状态检查）
- 功耗优化清单
- 常见漏电点分析

### 功能 5：Rockchip 平台低功耗配置

RK3588/RK3399/RK3308 等平台的 suspend DTS 配置和调试。

**你可以这样提问：**
- "RK3588 的 sleep-mode-config 怎么配？"
- "GPIO 唤醒和 CPU 中断唤醒有什么区别？"
- "RK3308 VAD 产品的低功耗怎么配？"

**AI 会返回：**
- 各平台 sleep-mode-config 位域说明和推荐配置
- 唤醒源配置和注意事项
- Debug 方法（PMU 波形、sleep-debug-en）
- 休眠打印信息的解读

## 触发方式

以下情况会自动触发本技能：

**关键词触发：**
- 低功耗、low power、休眠、suspend、resume、待机、standby
- 唤醒、wakeup、wakeup source、wakelock
- 功耗、power consumption、底电流、漏电
- Runtime PM、autosuspend、电源域、power domain
- pm_test、suspend_stats、no_console_suspend
- S2RAM、S2Idle、freeze、hibernate

**场景触发：**
- 系统无法进入休眠或 suspend 失败
- 休眠后无法唤醒或 resume 挂死
- 待机功耗过高、底电流异常
- 唤醒源定位、意外唤醒问题
- 驱动 suspend/resume 回调调试
- Runtime PM 设备不进入低功耗
- Rockchip 平台 sleep-mode-config / wakeup-config 配置

## 文件结构

```
linux_low_power/
├── SKILL.md                              # 主技能文件 (AI 自动加载, ~580 行)
├── README.md                             # 本说明文档 (供人阅读)
└── references/                           # 深入参考资料 (AI 按需加载)
    ├── rockchip_suspend.md               # Rockchip 平台 suspend 配置详解
    ├── android_suspend.md                # Android suspend 软件层分析
    └── debug_commands.md                 # 调试命令速查表
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含核心知识（suspend 流程、唤醒源管理、Runtime PM、功耗分析、常见陷阱）
- **references/**：AI 根据具体问题按需加载：
  - 用户涉及 Rockchip 平台 → 加载 `rockchip_suspend.md`
  - 用户涉及 Android 系统 → 加载 `android_suspend.md`
  - 用户需要命令速查 → 加载 `debug_commands.md`

## 使用示例

### 示例一：Suspend 失败排查

```
用户：系统 echo mem > /sys/power/state 后报错 "dpm_run_callback returns -16"
AI：
  1. 识别问题: 设备 suspend 回调返回 -EBUSY (16)
  2. 查 dmesg 定位具体哪个驱动: dmesg | grep "failed to suspend"
  3. 使用 pm_test 分级测试:
     echo devices > /sys/power/pm_test
     echo mem > /sys/power/state
  4. 打开 initcall_debug 查看回调耗时
  5. 给出驱动修复方向: 检查设备是否正在使用中、DMA 传输未完成等
```

### 示例二：待机功耗排查

```
用户：板子待机功耗太高，怎么排查？
AI：
  1. 确认休眠是否成功: dmesg | grep "suspended for"
  2. 检查 PD 状态: cat /sys/kernel/debug/pm_genpd/pm_genpd_summary
     → 找出应该 off 但还 on 的 PD
  3. 检查时钟: cat /sys/kernel/debug/clk/clk_summary | awk '$3 > 0'
     → 找出仍然使能的时钟
  4. 检查 regulator: cat /sys/kernel/debug/regulator/regulator_summary
  5. 硬件分路测量各路 DCDC/LDO 电流
  6. 给出优化清单
```

### 示例三：Rockchip 平台配置

```
用户：RK3588 的低功耗 DTS 怎么配？
AI：(加载 references/rockchip_suspend.md)
  1. 提供 sleep-mode-config 各 bit 说明
  2. 推荐最低功耗配置: ARMOFF_LOGOFF + PMUALIVE_32K + DIS_OSC
  3. 配置唤醒源: GPIO0 唤醒（首选）或 CPU 中断唤醒
  4. 提供完整 DTS 模板
  5. Debug 方法: sleep-debug-en + PMU 波形
```

## 知识来源

本技能的知识体系基于以下来源构建：

- **Linux Kernel Documentation** — `Documentation/power/` (sleep-states, runtime_pm, basic-pm-debugging)
- **Rockchip 官方文档** — RK3588/RK3399/RK3308 系统待机配置指南
- **Rockchip 官方文档** — 功耗分析和优化开发指南
- **Android PM 软件分析指南** v2.4.0
- **Linux PM Core 源码** — `kernel/power/`, `drivers/base/power/`
- 多年嵌入式 Linux 低功耗开发与调试实践经验

## License

MIT License

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-04-07 | 首次发布：suspend/resume 全流程分析、唤醒源管理、Runtime PM、功耗分析、RK 平台参考、Android suspend 参考、调试命令速查 |

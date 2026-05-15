# perf_common  通用 Linux 嵌入式平台性能排查技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`perf_common` 是一个**不限 SoC 平台**的 Linux 嵌入式性能问题排查 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户在嵌入式 Linux 平台上遇到性能问题时，AI 会自动加载本技能，按系统化的方法论引导排查，从快速定位瓶颈到给出可执行的优化方案。

## 适用平台

所有运行 Linux 内核的嵌入式 SoC 平台：

| 厂商 | 代表芯片 |
|------|---------|
| NXP | i.MX6/i.MX8/i.MX9 |
| TI (Texas Instruments) | AM335x/AM62x/AM64x/Sitara |
| Qualcomm | Snapdragon / QCS |
| 全志 Allwinner | H6/H616/T507/A523/D1 |
| MediaTek | MT8183/Genio/Dimensity |
| Samsung | Exynos |
| ST | STM32MP1/STM32MP2 |
| Broadcom | BCM2711 (Raspberry Pi) |
| Microchip/Atmel | SAMA5/SAM9 |
| Xilinx/AMD | Zynq/ZynqMP/Versal |
| RISC-V | StarFive/SiFive/T-Head |
| Rockchip | RK3566/RK3568/RK3588/RK3399 等 |

## 功能说明

### 功能 1：快速诊断

不知道性能瓶颈在哪？AI 按决策树逐步引导排查。

**你可以这样提问：**
- "我的板子运行很卡，帮我排查"
- "系统响应很慢，不知道是 CPU 还是 IO 的问题"
- "应用帧率低，应该从哪里开始查？"

**AI 会返回：**
1. 按优先级排列的诊断步骤（温控降频  频率策略  负载分布  内存）
2. 每步需要执行的 shell 命令
3. 根据命令输出判断瓶颈类型，跳转到对应专项排查

### 功能 2：CPU 性能排查

CPU 占用高、单核瓶颈、调频策略不合理等问题。

**你可以这样提问：**
- "CPU 始终跑不到最高频率"
- "切到 performance governor 后性能提升明显，怎么调参？"
- "我需要把关键线程绑定到大核上"
- "帮我做一次 CPU 定频测试"

**AI 会返回：**
- CPUFreq sysfs 接口操作命令
- Governor 调参建议（ondemand/schedutil/interactive）
- 绑核方案（taskset/cpuset cgroup/isolcpus）

### 功能 3：GPU 性能排查

GPU 渲染帧率低、GPU 负载异常等问题。

**你可以这样提问：**
- "GPU 频率上不去，负载很低但画面卡顿"
- "glmark2 跑分很低，怎么优化？"
- "怎么确认 GPU 驱动是否正常工作？"

### 功能 4：内存/DDR 排查

内存不足、OOM、DDR 带宽瓶颈等问题。

**你可以这样提问：**
- "系统运行一段时间后 OOM kill"
- "怎么测试 DDR 带宽？"
- "CMA 分配失败导致摄像头打不开"
- "怀疑有内存泄漏，帮我定位"

### 功能 5：温控与功耗

温控降频导致性能下降、功耗过高等问题。

**你可以这样提问：**
- "芯片温度 90 度，性能大幅下降"
- "怎么调整温控策略让性能更好？"
- "power_allocator 和 step_wise 怎么选？"
- "怎么临时关闭温控做基准测试？"

### 功能 6：IO/存储性能

读写慢、IO 延迟高、eMMC/SD 速度不达标等问题。

**你可以这样提问：**
- "eMMC 写入速度只有 20MB/s，正常应该多少？"
- "怎么用 fio 测随机 4K 读写？"
- "IO 调度器应该选哪个？"

### 功能 7：实时性排查

中断延迟、调度抖动、RT 线程响应不及时等问题。

**你可以这样提问：**
- "cyclictest 最大延迟超过 500us"
- "怎么配置 PREEMPT_RT 内核？"
- "怎么把中断绑定到指定核？"

### 功能 8：子系统专项

USB/PCIe/网络/显示/启动等子系统的性能问题。

**你可以这样提问：**
- "USB3.0 设备传输速度只有 USB2.0 水平"
- "PCIe 链路速度没有跑到 Gen3"
- "千兆网络 iperf3 只能跑到 500Mbps"
- "系统启动到桌面要 30 秒，怎么优化？"

### 功能 9：工具指导

perf、ftrace、火焰图等性能分析工具的使用方法。

**你可以这样提问：**
- "怎么用 perf 抓 CPU 热点并生成火焰图？"
- "怎么用 ftrace 追踪调度事件？"
- "trace-cmd 怎么用？"
- "怎么做压力测试？"

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **性能 / 卡顿 / 帧率低 / 延迟高 / CPU 占用高 / 发热降频** 等症状描述
- 提到性能工具：**perf / ftrace / trace-cmd / 火焰图 / flamegraph / cyclictest / stress-ng / iperf3 / fio / glmark2 / sysbench** 等
- 提到调频调压：**cpufreq / devfreq / thermal / governor / opp-table / 定频** 等
- 提到性能指标：**throughput / bandwidth / latency / jitter / IOPS** 等
- 描述嵌入式 Linux 平台上任何与"慢、卡、热、延迟、吞吐量"相关的现象

## 文件结构

```
perf_common/
 SKILL.md                         # 主技能文件 (AI 自动加载, ~430 行)
 README.md                        # 本说明文档 (供人阅读)
 references/                      # 深入参考资料 (AI 按需加载)
     dvfs_thermal.md              # CPUFreq/Devfreq/Thermal 详解：Governor 调参、OPP DTS、EAS、功耗分析
     subsystem_perf.md            # 子系统专项：USB/PCIe/GMAC/多媒体/存储/显示/启动时间优化
     tools.md                     # 工具详解：perf/ftrace/trace-cmd/BPF/stress-ng/cyclictest/火焰图
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含快速诊断流程、各子系统排查要点、常用命令速查
- **references/**：AI 根据问题深度按需加载。例如：
  - 用户需要调 governor 参数  加载 `dvfs_thermal.md`
  - 用户排查 USB/PCIe/网络  加载 `subsystem_perf.md`
  - 用户需要 perf/ftrace 详细用法  加载 `tools.md`

## 使用示例

### 示例 1：系统卡顿排查

**用户提问：**
> 我的 i.MX8M 板子跑 Qt 应用很卡，不知道是 CPU 还是 GPU 的问题

**AI 行为：**
1. 自动触发 `perf_common` 技能
2. 按快速诊断决策树引导：先查温控降频  再查频率策略  查负载分布
3. 给出各步骤的 shell 命令
4. 根据用户反馈的命令输出，定位到 CPU/GPU/IO 瓶颈并给出优化方案

### 示例 2：基准测试

**用户提问：**
> 我想对这块全志 H616 板子做一次全面的性能基准测试

**AI 行为：**
1. 提供测试前准备步骤（定频、关温控）
2. 列出各维度基准工具和命令（CPU: UnixBench/CoreMark, 内存: mbw/stream, 存储: fio, 网络: iperf3, GPU: glmark2）
3. 给出结果解读建议

### 示例 3：实时性优化

**用户提问：**
> cyclictest 最大延迟 800us，需要优化到 100us 以内

**AI 行为：**
1. 检查内核配置（PREEMPT_RT、HZ、HIGH_RES_TIMERS）
2. 建议 isolcpus + nohz_full 隔离 CPU
3. 指导中断绑核和 RT 线程优先级配置
4. 加载 `references/tools.md` 提供 cyclictest 高级用法

## 知识来源

- Linux 内核官方文档（CPUFreq、Devfreq、Thermal、Scheduler）
- 各 SoC 厂商 BSP 性能调优指南
- Brendan Gregg 系统性能分析方法论
- RT-Linux 社区实时性优化最佳实践

## License

MIT License  自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

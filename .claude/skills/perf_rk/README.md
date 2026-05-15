# perf_rk  瑞芯微 RK 平台性能问题排查技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`perf_rk` 是一个面向 Rockchip（瑞芯微）全系列 SoC 平台的性能问题排查 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户描述 Rockchip 平台上的性能相关问题时，AI 会自动加载本技能，利用 RK 平台特有的 sysfs 路径、调频机制、DDR 场景控制、GPU 地址等知识，提供精准的排查方案。

## 覆盖芯片

| 芯片 | 架构 | CPU 最高主频 |
|------|------|-------------|
| **RK3588 / RK3588S** | 4A55 + 2A76 + 2A76 | 1800 + 2400 + 2400 MHz |
| **RK3568** | 4A55 | 2000 MHz |
| **RK3566** | 4A55 | 1800 MHz |
| **RK3399 / RK3399Pro** | 2A72 + 4A53 | 1800 + 1416 MHz |
| **RK3328** | 4A53 | 1296 MHz |
| **RK3288** | 4A17 | 1608 MHz |
| **PX30 / RK3326** | 4A35 | 1296 MHz |

## 功能说明

### 功能 1：快速诊断

不知道性能瓶颈在哪？AI 按 RK 平台专用的决策树逐步引导排查。

**你可以这样提问：**
- "RK3568 跑我的应用很卡，帮我排查"
- "RK3588 跑分比预期低很多"
- "不知道是 CPU、GPU 还是 DDR 的问题"

**AI 会返回：**
1. RK 平台专用的诊断命令（使用正确的 sysfs 路径：policy0/policy4/policy6）
2. 一键状态采集脚本（温度、频率、governor、cooling device、内存、Top 10 进程）
3. 根据输出结果判断瓶颈并跳转专项排查

### 功能 2：CPU 性能排查

大小核调频、定频测试、Leakage/PVTM 调压等 RK CPU 相关问题。

**你可以这样提问：**
- "RK3588 三 cluster 怎么分别定频？"
- "RK3399 大核频率上不去"
- "dmesg 中 leakage/pvtm 值是什么意思？"
- "怎么确认 OPP Table 是否正确？"

**AI 会返回：**
- 各 RK 平台的 CPU cluster 对应的 policy 编号和最高主频表
- 分 cluster 定频命令
- Leakage/PVTM 调压机制解读

### 功能 3：GPU 性能排查

GPU 频率、负载监控、调频阈值调整等问题。

**你可以这样提问：**
- "RK3568 GPU 频率一直很低"
- "glmark2 跑分比参考分数低很多"
- "GPU devfreq 的 upthreshold 怎么调？"

**AI 会返回：**
- 各 RK 芯片的 GPU devfreq 路径（RK3399: ff400000.gpu, RK3568: fde60000.gpu, RK3588: fb000000.gpu）
- GPU 定频和负载查看命令
- upthreshold/downdifferential DTS 调参

### 功能 4：DDR/内存排查

DDR 频率控制、带宽测试、场景调度、内存泄漏等问题。

**你可以这样提问：**
- "怎么用 rk-msch-probe 测 DDR 带宽？"
- "DDR 场景调频是怎么工作的？"
- "花屏是不是 DDR 带宽不足？"
- "DDR 降频到 200MHz 后不再死机，是 DDR 稳定性问题吗？"

**AI 会返回：**
- DDR 定频和带宽测试命令（rk-msch-probe）
- DDR 问题速查表（死机/花屏/串口报错/高负载异常）
- 内存排查命令（meminfo/slabinfo/dma_buf）

### 功能 5：温控与功耗

温控降频、Thermal Governor 调参、功耗测试等问题。

**你可以这样提问：**
- "RK3588 温度 95 度在限频，怎么优化散热策略？"
- "怎么临时关闭温控做测试？"
- "sustainable-power 参数怎么调？"
- "RK3399 的功耗应该是多少？"

**AI 会返回：**
- 温控状态查看命令（thermal_zone、trip_point、cooling_device）
- Thermal Governor 对比表
- RK3399 功耗参考数据（静态桌面 1.88W、压力测试 4.13W 等）

### 功能 6：子系统专项

USB/PCIe/MPP 编解码/RGA/GMAC 等 RK 平台子系统性能问题。

**你可以这样提问：**
- "MPP 硬件解码能力怎么查？"
- "RGA2 和 RGA3 性能差多少？"
- "USB3.0 设备速度不对"
- "PCIe 链路降速了"

### 功能 7：工具指导

perf、ftrace、systrace、streamline 等工具在 RK 平台上的使用。

**你可以这样提问：**
- "怎么在 RK3568 上用 perf 抓 CPU 热点？"
- "RK 平台怎么用 systrace？"
- "streamline 怎么连接 RK 开发板？"
- "ioblame 脚本怎么用？"

### 功能 8：基准跑分参考

提供各 RK 平台的标准性能基准分数，帮助判断性能是否达标。

**你可以这样提问：**
- "RK3588 的 glmark2 应该跑多少分？"
- "RK3568 的 UnixBench 分数正常多少？"
- "我跑的分数比参考值低 30%，可能是什么原因？"

**AI 会返回：**

| 基准 | RK3588 | RK3399 | RK3568 | RK3566 |
|------|--------|--------|--------|--------|
| Glmark2 (800600) | 4851 | 812 | 560 | 485 |
| UnixBench 单任务 | 1342 | 655 | 497 | 457 |
| UnixBench 多任务 | 4036 | 1403 | 1147 | 1039 |

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **RK3588 / RK3568 / RK3566 / RK3399 / RK3328 / RK3288 / PX30** 等芯片型号 + 性能相关描述
- 提到 **Rockchip / 瑞芯微** + 性能/卡顿/延迟等症状
- 描述 RK 平台任何与"慢、卡、热、延迟、吞吐量、跑分低"相关的现象
- 提到 RK 特有工具：**rk-msch-probe / MPP / RGA / systrace** 等
- 提到调频调压：**cpufreq / devfreq / thermal / governor / opp-table / 定频** 等

## 文件结构

```
perf_rk/
 SKILL.md                         # 主技能文件 (AI 自动加载, ~400 行)
 README.md                        # 本说明文档 (供人阅读)
 references/                      # 深入参考资料 (AI 按需加载)
     dvfs_thermal.md              # DVFS 调频详解：Governor 调参、OPP Table、Leakage/PVTM、Thermal DTS
     subsystem_perf.md            # 子系统专项：USB/PCIe/GMAC/MPP/RGA/Display/启动时间
     tools.md                     # 工具详解：perf/ftrace/systrace/streamline/cyclictest/火焰图
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 RK 各平台主频表、GPU 地址表、DDR 场景控制、基准分数参考等核心数据
- **references/**：AI 根据问题深度按需加载。例如：
  - 用户需要调 OPP/Thermal 参数  加载 `dvfs_thermal.md`
  - 用户排查 USB/PCIe/MPP  加载 `subsystem_perf.md`
  - 用户需要 perf/systrace 详细用法  加载 `tools.md`

## 使用示例

### 示例 1：RK3588 跑分偏低

**用户提问：**
> RK3588 glmark2 只跑了 2000 分，正常应该多少？

**AI 行为：**
1. 自动触发 `perf_rk` 技能
2. 查参考分数表：RK3588 在 800600 Performance 模式下应4851
3. 引导检查：GPU 是否定频最高、是否关闭了温控、分辨率是否正确
4. 给出定频和关温控命令

### 示例 2：DDR 带宽瓶颈

**用户提问：**
> 多路摄像头同时采集时画面卡顿，怀疑是 DDR 带宽不够

**AI 行为：**
1. 指导先 DDR 定频到最高频率
2. 给出 rk-msch-probe 带宽测试命令
3. 分析 ddr load 是否超过 70%
4. 建议优化：提高 DDR 频率、减少不必要的内存拷贝、使用 RGA 硬件加速

### 示例 3：温控降频排查

**用户提问：**
> RK3568 跑 AI 推理时越跑越慢，CPU 频率从 2GHz 降到了 1.4GHz

**AI 行为：**
1. 查看温度和 cooling device 状态
2. 确认温控策略（power_allocator vs step_wise）
3. 建议调整 sustainable-power、trip_point 温度阈值，或改善散热
4. 加载 `references/dvfs_thermal.md` 提供 DTS 调参细节

## 知识来源

- Rockchip 官方性能调优文档（Rockchip_Developer_Guide_Linux_Performance）
- Rockchip 官方 DVFS/Thermal 开发指南
- Rockchip BSP 内核源码与 DTS 参考配置
- 各 RK 开发板实际测试数据

## License

MIT License  自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

# rk_ddr  Rockchip DDR 内存子系统技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_ddr` 是一个面向 Rockchip 瑞芯微 SoC 平台的 DDR 内存子系统 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户在 Rockchip 平台上遇到 DDR 初始化、频率配置（DMC 变频/定频）、容量识别、带宽监控、ECC 纠错、颗粒稳定性验证等问题时，AI 会自动加载本技能，提供 RK 平台特有的 DDR bin 打印解读、DMC devfreq 场景控制、rk_msch_probe 带宽工具等深度知识。

## 覆盖芯片

| 芯片 | 架构 | 支持 DDR 类型 |
|------|------|-------------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | LPDDR4/4X, LPDDR5/5X |
| **RK3568** | 4A55, Mali-G52 | DDR3/3L, DDR4, LPDDR3/4/4X |
| **RK3566** | 4A55, Mali-G52 | DDR3/3L, DDR4, LPDDR3/4/4X |
| **RK3399 / RK3399Pro** | 2A72 + 4A53, Mali-T860 | DDR3/3L, LPDDR3/4 |
| **RK3328** | 4A53, Mali-450 | DDR3/3L, DDR4, LPDDR3 |
| **RK3288** | 4A17, Mali-T764 | DDR3/3L, LPDDR2/3 |
| **PX30 / RK3326** | 4A35, Mali-G31 | DDR3/3L, LPDDR2/3 |

## 功能说明

### 功能 1：DDR 频率配置

DMC devfreq 变频/定频、场景控制（视频/游戏/待机）、OPP Table 配置。

**你可以这样提问：**
- "RK3568 怎么将 DDR 定频到最高频率？"
- "怎么配置 DMC 的场景变频策略？"
- "dmc_opp_table 怎么修改 DDR 频率电压表？"
- "auto-freq-en 和 system-status-freq 各参数什么意思？"
- "DDR 变频时死机，怎么排查？"

**AI 会返回：**
- DDR 定频 / 变频的 sysfs 命令和 DTS 配置方法
- DMC 场景调频参数详解（SYS_STATUS_NORMAL/VIDEO_4K/SUSPEND 等）
- 负载变频参数调优（upthreshold/downdifferential）

### 功能 2：DDR 问题排查

死机、花屏、串口报错、high load 异常等 DDR 相关问题的系统化诊断。

**你可以这样提问：**
- "板子跑一段时间就死机，怀疑 DDR 不稳定"
- "降频到 200MHz 就不死机了，是颗粒问题吗？"
- "DDR 初始化打印 Memory OK 后面的参数怎么解读？"
- "花屏是不是 DDR 带宽或信号质量问题？"

**AI 会返回：**
- DDR 问题速查决策树（死机 → 定频二分法 → de-skew 调整 → 颗粒更换）
- Loader DDR 打印信息逐字段解读
- DDR 信号质量排查要点（走线、电源、de-skew/DQ/DQS/CLK skew）

### 功能 3：DDR 稳定性验证

DDR 颗粒验证全流程，包括定频/变频/reboot/sleep 拷机。

**你可以这样提问：**
- "新的 DDR 颗粒怎么验证稳定性？"
- "stressapptest 和 memtester 怎么用？"
- "DDR 拷机需要跑多长时间？"
- "白牌颗粒替代原厂颗粒需要做哪些验证？"

**AI 会返回：**
- DDR 颗粒验证标准流程（定频逐频点 → 变频 → reboot → sleep 循环）
- stressapptest / memtester / ddr_freq_scan 等工具使用方法
- 验证通过标准和常见不通过场景分析

### 功能 4：DDR 带宽与 ECC

带宽监控工具使用、ECC 配置与纠错查看。

**你可以这样提问：**
- "怎么用 rk_msch_probe 测 DDR 实时带宽？"
- "多路视频同时解码时 DDR 带宽够不够？"
- "RK3568 的 DDR ECC 怎么配置？"
- "HAL DDR ECC 的中断报告怎么解读？"

**AI 会返回：**
- rk_msch_probe 工具使用方法和输出解读
- DDR 带宽估算方法与瓶颈判断标准
- SideBand ECC 的 DTS 配置和中断处理流程

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **DDR / DRAM / 内存 / LPDDR4 / LPDDR5 / DDR4 / DDR3** 等存储类型
- 提到 **DMC / dmc / devfreq/dmc / dmc_opp_table / DDR 变频 / DDR 定频** 等频率控制
- 提到 **DDR 带宽 / rk_msch_probe / DDR load** 等带宽相关
- 提到 **stressapptest / memtester / DDR 拷机 / DDR 验证 / 颗粒验证** 等稳定性
- 提到 **DDR ECC / de-skew / DQ / DQS** 等信号质量
- 描述 DDR 相关症状：**死机 / 花屏 / 重影 / MemTotal 不对 / DDR 初始化失败**

## 文件结构

```
rk_ddr/
├── SKILL.md                              # 主技能文件 (AI 自动加载, ~500 行)
├── README.md                             # 本说明文档 (供人阅读)
└── references/                           # 深入参考资料 (AI 按需加载)
    ├── ddr_freq_config.md                # DDR 频率配置详解：DMC 场景/负载变频、OPP Table、定频方法
    └── ddr_debug_verification.md         # DDR 问题排查与颗粒验证：故障决策树、拷机流程、ECC 配置
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 DDR 核心知识（初始化打印解读、定频命令、问题速查表、验证流程概要）
- **references/**：AI 根据问题按需加载。例如：
  - 用户配 DDR 变频策略 → 加载 `ddr_freq_config.md`
  - 用户排查 DDR 死机或做颗粒验证 → 加载 `ddr_debug_verification.md`

## 使用示例

### 示例 1：DDR 定频排查死机

**用户提问：**
> RK3568 板子跑压力测试会随机死机，怀疑 DDR 不稳定

**AI 行为：**
1. 自动触发 `rk_ddr` 技能
2. 指导先 DDR 定频到最高频率复现，再二分法定位不稳定频点
3. 给出定频 sysfs 命令和 stressapptest 拷机参数
4. 根据结果引导排查方向（颗粒兼容性 / de-skew / 电源纹波）

### 示例 2：DMC 场景变频配置

**用户提问：**
> RK3588 播放 4K 视频时 DDR 频率不够高导致卡顿，怎么调？

**AI 行为：**
1. 解释 DMC 场景变频机制（SYS_STATUS_VIDEO_4K 触发高频）
2. 给出 DTS 中 system-status-freq 参数配置方法
3. 提供实时查看 DDR 频率和负载的命令
4. 加载 `references/ddr_freq_config.md` 提供完整调参细节

### 示例 3：DDR 颗粒验证

**用户提问：**
> 换了一款国产 DDR 颗粒，需要做完整验证，流程是什么？

**AI 行为：**
1. 给出 Rockchip 标准 DDR 颗粒验证流程
2. 指导定频逐频点拷机 → 变频拷机 → reboot 循环 → sleep 循环
3. 提供各测试工具的命令和参数
4. 说明验证通过标准和不通过时的排查方向

## 知识来源

| 文档 | 说明 |
|------|------|
| Rockchip_Developer_Guide_DDR_CN | DDR 开发指南 (打印解读、频率配置、定频、容量、ECC、de-skew) |
| Rockchip_DDR_Troubleshooting_CN | DDR 问题排查手册 (排查方法与手段) |
| Rockchip_DDR_Problem_Solution_CN | DDR 问题排查手册 (根因与解决方案) |
| Rockchip_DDR_Verification_Process_CN | DDR 颗粒验证流程说明 (定频/变频/reboot/sleep 拷机) |
| Rockchip_DDR_Bandwidth_Tool_CN | DDR 带宽工具 (rk_msch_probe) 使用说明 |
| Rockchip_Developer_Guide_HAL_DDR_ECC | HAL DDR ECC 开发指南 (RK3568 ECC) |

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

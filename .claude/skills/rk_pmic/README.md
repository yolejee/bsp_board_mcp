# rk_pmic  Rockchip PMIC 电源管理与 DVFS 技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_pmic` 是一个面向 Rockchip 瑞芯微 SoC 平台的 PMIC 电源管理与 DVFS 调频调压 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip 平台的 PMIC（RK806/RK809/RK817/RK808/RK805）配置、regulator DTS 编写、电源树设计、休眠唤醒功耗管理，以及 CPUFreq/Devfreq/OPP Table 动态调频调压框架等问题时，AI 会自动加载本技能，提供 PMIC 型号选型、regulator 参数配置、DVFS 性能调优等深度知识。

## 覆盖芯片

| 芯片 | 架构 | 典型 PMIC |
|------|------|----------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | RK806 (Master + Slave 双 PMIC) |
| **RK3568** | 4A55, Mali-G52 | RK809 |
| **RK3566** | 4A55, Mali-G52 | RK817 |
| **RK3399 / RK3399Pro** | 2A72 + 4A53, Mali-T860 | RK808 / RK809 |
| **PX30 / RK3326** | 4A35, Mali-G31 | RK817 / RK805 |

## 功能说明

### 功能 1：PMIC DTS 配置

各型号 PMIC 的 regulator 节点编写、I2C/SPI 总线挂载、Sleep/Shutdown 模式配置。

**你可以这样提问：**
- "帮我写 RK809 的完整 PMIC DTS 配置"
- "RK806 双 PMIC 的 Master/Slave 怎么配？"
- "regulator-always-on 和 regulator-boot-on 有什么区别？"
- "休眠时 VCC_3V3 需要保持供电，怎么配？"
- "PMIC 的 Sleep Pin 和中断引脚 DTS 怎么写？"

**AI 会返回：**
- 完整的 PMIC DTS 模板（I2C/SPI 节点 + regulators 子节点 + 中断/Sleep Pin）
- 各 PMIC 型号的 DCDC/LDO 通道列表和电压范围
- 休眠态电压设置（regulator-state-mem / regulator-suspend-microvolt）
- RK806 双 PMIC 主从配置方法

### 功能 2：CPUFreq / Devfreq 调频调压

CPU Governor 选择、OPP Table 配置、GPU devfreq、DMC 场景变频等 DVFS 配置。

**你可以这样提问：**
- "CPUFreq 的 interactive 和 schedutil 哪个适合我的场景？"
- "OPP Table 怎么删除某个频点？"
- "Leakage/PVTM 自动调压是什么原理？"
- "GPU devfreq 的 upthreshold 怎么调？"
- "DMC 场景变频怎么配 DTS？"

**AI 会返回：**
- CPUFreq Governor 对比表和推荐选择
- OPP Table DTS 配置（频率-电压对、删除频点、添加频点）
- Leakage/PVTM 自动调压机制和 OPP 高级配置
- GPU/DMC devfreq 参数调优方法

### 功能 3：功耗分析与优化

电源域划分、功耗测量方法、各场景功耗折算、低功耗优化策略。

**你可以这样提问：**
- "怎么测 RK3568 整板功耗？各电源域分别多少？"
- "待机功耗太高，怎么排查哪个模块在耗电？"
- "怎么组合 CPU/GPU/DDR 降频来降低功耗？"
- "Suspend 后功耗应该降到多少？"

**AI 会返回：**
- 功耗测量方法（各电压域测量点、电流测量方法）
- 功耗折算公式（P = V × I，动态功耗 vs 静态功耗）
- 各场景功耗参考值和异常判断
- 低功耗优化清单（CPU/GPU/DDR 降频、外设关闭、Suspend 优化）

### 功能 4：PMIC 故障排查

PMIC 不启动、regulator 使能失败、电压异常、休眠唤醒异常等问题诊断。

**你可以这样提问：**
- "板子上电 PMIC 不启动，什么原因？"
- "regulator enable 失败报 -ENODEV"
- "某路 LDO 实际输出电压和 DTS 设置不符"
- "Suspend 后无法唤醒"

**AI 会返回：**
- PMIC 上电时序检查清单（PWRON/RESET/VCC_IO）
- Regulator 调试命令（regulator_summary、PMIC 寄存器读取）
- 电压异常排查方法（DTS 配置 vs 寄存器值 vs 实测值对比）
- Suspend/Resume 失败排查（wakeup-source 配置、regulator 休眠状态）

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **PMIC / RK806 / RK809 / RK817 / RK808 / RK805** 等型号
- 提到 **regulator / DCDC / LDO / NLDO / PLDO / SWITCH / BUCK** 等电源概念
- 提到 **CPUFreq / Devfreq / DVFS / OPP / opp-table / Governor** 等调频调压
- 提到 RK 特有属性：**vdd_cpu / vdd_gpu / vdd_logic / vdd_npu / vcc_ddr / regulator-state-mem**
- 提到 **功耗 / 低功耗 / 待机功耗 / Suspend / 休眠 / power analysis** 等功耗话题
- 描述电源相关症状：**PMIC 不启动 / regulator 失败 / 电压异常 / 唤醒失败**

## 文件结构

```
rk_pmic/
├── SKILL.md                              # 主技能文件 (AI 自动加载, ~600 行)
├── README.md                             # 本说明文档 (供人阅读)
└── references/                           # 深入参考资料 (AI 按需加载)
    ├── pmic_dts_config.md                # 各型号 PMIC 完整 DTS 模板、Regulator 属性详解
    └── dvfs_power_tuning.md              # CPUFreq/Devfreq 完整配置、OPP 高级调压、功耗分析方法论
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 PMIC 核心知识（型号对比、regulator 概要、DVFS 框架、功耗基础）
- **references/**：AI 根据问题按需加载。例如：
  - 用户要写 PMIC DTS → 加载 `pmic_dts_config.md`
  - 用户要调 DVFS/功耗 → 加载 `dvfs_power_tuning.md`

## 使用示例

### 示例 1：RK809 PMIC 配置

**用户提问：**
> 帮我写 RK3568 配 RK809 的完整 PMIC DTS，需要配置休眠电压

**AI 行为：**
1. 自动触发 `rk_pmic` 技能
2. 生成完整的 RK809 DTS（I2C 节点 + 9 路 regulator + 中断 + Sleep Pin）
3. 为每路 regulator 配置 regulator-state-mem 休眠状态
4. 加载 `references/pmic_dts_config.md` 提供每路电压范围和用途说明

### 示例 2：OPP Table 调优

**用户提问：**
> RK3588 想删掉 CPU 最高频点并且调低对应电压，OPP Table 怎么改？

**AI 行为：**
1. 解释 OPP Table 的 DTS 结构和 status = "disabled" 用法
2. 给出删除频点和修改电压的 DTS overlay 代码
3. 提醒 Leakage/PVTM 分档可能影响实际电压
4. 加载 `references/dvfs_power_tuning.md` 提供完整 OPP 高级调压说明

### 示例 3：待机功耗排查

**用户提问：**
> RK3566 Suspend 后功耗 800mA，正常应该多少？

**AI 行为：**
1. 给出 RK3566 Suspend 功耗参考值
2. 引导检查各电源域的 Suspend 状态（哪些 regulator 保持开启）
3. 指导逐路排查（关闭不必要外设、WiFi/BT 电源管理）
4. 提供 wakeup-source 和 regulator-state-mem 的 DTS 优化建议

## 知识来源

- Rockchip_RK806_Developer_Guide_CN_V1.1.pdf (15p)
- Rockchip_RK809_Developer_Guide_CN_V1.1.pdf (14p)
- Rockchip_RK817_Developer_Guide_CN_V1.0.0.pdf (15p)
- Rockchip_RK808_Developer_Guide_CN_V1.0.1.pdf (19p)
- Rockchip_Developer_Guide_Power_Analysis_CN_V1.0.pdf (15p)
- Rockchip_Developer_Guide_CPUFreq_CN_V1.1.1.pdf (21p)
- Rockchip_Developer_Guide_Devfreq_CN_V1.1.1.pdf (26p)

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

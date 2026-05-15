# rk_isp  Rockchip ISP 图像信号处理与调优技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_isp` 是一个面向 Rockchip 瑞芯微 SoC 平台的 ISP 图像信号处理与调优 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip ISP 的图像质量调优（IQ Tuning）、3A 算法（AE/AWB/AF）、IQ XML 文件配置、RkAiq 软件框架与 API 调用等问题时，AI 会自动加载本技能，提供 ISP 各处理模块参数详解、调优方法论、色彩优化和降噪策略等深度知识。

## 覆盖芯片

| 芯片 | ISP 版本 | 分辨率能力 |
|------|---------|-----------|
| **RK3588 / RK3588S** | ISP30 ×2 + ISP32-lite | 双 ISP 8K 合成, 单 ISP 4K |
| **RK3568** | ISP21 | 单路 4K |
| **RK3566** | ISP21 | 单路 4K |
| **RV1126 / RV1109** | ISP20 | 双路 1080p / 单路 4K |
| **RV1106** | ISP32-lite | 单路 1080p |

## 功能说明

### 功能 1：ISP 模块参数调优

逐模块调试 ISP 图像处理管线：BLC、LSC、AWB、CCM、Gamma、NR、SHP、DRC、DEHAZE 等。

**你可以这样提问：**
- "ISP30 的降噪模块 (BNR/YNR/CNR) 参数怎么调？"
- "Gamma 曲线怎么调可以让暗部细节更好？"
- "CCM 偏色，色彩校正矩阵怎么标定？"
- "LSC 暗角校正的标定方法是什么？"
- "DRC/DEHAZE 模块的区别和使用场景？"

**AI 会返回：**
- 各 ISP 模块的参数含义和典型调试范围
- 模块间的依赖关系和推荐调试顺序
- IQ XML 文件中对应的 tag 和属性名
- 不同场景（室内/室外/低照度/逆光）的调优策略

### 功能 2：3A 算法配置

AE（自动曝光）、AWB（自动白平衡）、AF（自动聚焦）的参数调优和自定义扩展。

**你可以这样提问：**
- "AE 曝光收敛太慢，怎么调？"
- "AWB 在特定光源下偏色严重"
- "怎么自定义 3A 算法替换 RkAiq 默认的？"
- "HDR 模式下的多帧曝光融合怎么配？"

**AI 会返回：**
- AE 参数调优（收敛速度、目标亮度、防闪烁、手动曝光表）
- AWB 色温曲线校准和自定义白平衡增益
- 自定义 3A 库开发接口说明
- HDR 多帧曝光比和融合参数

### 功能 3：RkAiq 框架与 API

RkAiq（camera_engine_rkaiq）软件架构、API 调用、rkisp_3A_server 配置。

**你可以这样提问：**
- "RkAiq API 怎么在应用层动态调整曝光参数？"
- "rkisp_3A_server 启动参数怎么配？"
- "怎么在代码中获取当前 AE 状态和 AWB 色温？"
- "IQ XML 文件的加载路径和命名规则？"

**AI 会返回：**
- RkAiq API 初始化和参数设置代码示例
- rkisp_3A_server 的启动命令和配置参数
- IQ XML 文件命名规则和加载优先级
- 调试工具（RKNN_LOG_LEVEL、dump 开关）

### 功能 4：画质问题诊断

偏色、噪点多、过曝/欠曝、暗角、畸变等图像质量问题的系统化排查。

**你可以这样提问：**
- "出图偏绿是什么原因？"
- "低照度下噪点太多，画面模糊"
- "图像局部过曝，高光区域全白"
- "鱼眼镜头畸变怎么校正？"

**AI 会返回：**
- 画质问题到 ISP 模块的映射关系（偏色→AWB/CCM、噪点→NR、过曝→AE/DRC）
- 逐步排查流程
- 对应模块的调优建议和参数调整方向

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **ISP / ISP20 / ISP21 / ISP30 / ISP32 / RKISP / RkAiq** 等关键词
- 提到 **3A / AE / AEC / AWB / AF / 自动曝光 / 自动白平衡** 等 3A 相关
- 提到 **IQ 文件 / IQ XML / iqfiles / 图像调优 / tuning** 等调优相关
- 提到 ISP 模块：**BLC / LSC / CCM / Gamma / NR / BNR / YNR / CNR / SHP / DRC / DEHAZE / FEC / LDCH**
- 描述画质问题：**偏色 / 偏绿 / 偏红 / 噪点多 / 过曝 / 欠曝 / 暗角 / 畸变**

## 文件结构

```
rk_isp/
├── SKILL.md                             # 主技能文件 (AI 自动加载, ~600 行)
├── README.md                            # 本说明文档 (供人阅读)
└── references/                          # 深入参考资料 (AI 按需加载)
    ├── isp_module_tuning.md             # ISP 模块逐项调试参考 (BLC/LSC/AWB/CCM/NR/Gamma/DRC/DEHAZE/FEC/OTP)
    └── rkaiq_api_reference.md           # RkAiq API 完整参考与代码示例
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 ISP 核心知识（管线架构、模块概览、调优方法论、3A 框架）
- **references/**：AI 根据问题按需加载。例如：
  - 用户要调具体 ISP 模块参数 → 加载 `isp_module_tuning.md`
  - 用户要调用 RkAiq API → 加载 `rkaiq_api_reference.md`

## 使用示例

### 示例 1：降噪参数调优

**用户提问：**
> RK3568 ISP21 低照度下画面噪点很多，怎么调降噪？

**AI 行为：**
1. 自动触发 `rk_isp` 技能
2. 解释 ISP21 的降噪模块链路（BNR → YNR → UVNR/CNR）
3. 给出各模块在低照度场景的推荐参数调整方向
4. 加载 `references/isp_module_tuning.md` 提供具体 IQ XML tag 和数值范围

### 示例 2：AWB 偏色修正

**用户提问：**
> Camera 在暖色灯光下严重偏黄，AWB 不准

**AI 行为：**
1. 分析 AWB 色温曲线是否覆盖该光源
2. 建议检查 AWB 白区范围和增益限制
3. 给出 IQ XML 中 AWB 参数的调整方法
4. 如果需要精确标定，指导使用 Tuner 工具

### 示例 3：RkAiq API 动态调参

**用户提问：**
> 怎么在应用程序中用 RkAiq API 动态设置手动曝光？

**AI 行为：**
1. 给出 rk_aiq_uapi2 的初始化和 AE 手动模式设置代码
2. 说明曝光时间和增益的设置范围和单位
3. 加载 `references/rkaiq_api_reference.md` 提供完整 API 列表

## 知识来源

| 文档 | 说明 |
|------|------|
| Rockchip_Tuning_Guide_ISP30_CN | ISP30 调试指南 (124 页) |
| Rockchip_Development_Guide_ISP30_CN | ISP30 开发指南 (357 页) |
| Rockchip_Color_Optimization_Guide_ISP30_CN | 色彩优化指南 (69 页) |
| Rockchip_Development_Guide_3A_ISP30_CN | 自定义 3A 开发指南 (38 页) |
| Rockchip_IQ_Tools_Guide_ISP2x_ISP3x_CN | IQ 工具使用指南 (51 页) |

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

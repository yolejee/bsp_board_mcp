# rk_camera  Rockchip Camera 摄像头子系统技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_camera` 是一个面向 Rockchip 瑞芯微 SoC 平台的 Camera 摄像头子系统 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip 平台的摄像头 Sensor 驱动开发、MIPI CSI-2 接口调试、V4L2/Media Controller 框架配置、多摄方案设计等问题时，AI 会自动加载本技能，提供 RK 平台特有的 Camera 链路配置、DPHY/DCPHY 选型、多摄拓扑设计、MIPI 错误诊断等深度知识。

## 覆盖芯片

| 芯片 | 架构 | Camera 能力 |
|------|------|------------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | 最多 7 路 Sensor, DCPHY×2 + DPHY×4, 双 ISP30 8K |
| **RK3568** | 4A55, Mali-G52 | DPHY×2, ISP21 |
| **RK3566** | 4A55, Mali-G52 | DPHY×1, ISP21 |
| **RK3399 / RK3399Pro** | 2A72 + 4A53, Mali-T860 | DPHY×2, ISP1.x |
| **RV1126 / RV1109** | 4A35 + 1RISC-V, ISP20 | DPHY×2, 专业视觉 |
| **RV1106** | 1A35, ISP32-lite | DPHY×1, 轻量 IPC |
| **PX30 / RK3326** | 4A35, Mali-G31 | DPHY×1 |

## 功能说明

### 功能 1：Sensor 驱动开发移植

从零移植 Camera Sensor 驱动，涵盖上电时序、V4L2 subdev 回调、controls 注册与 DTS 配置。

**你可以这样提问：**
- "帮我移植 IMX415 sensor 驱动到 RK3568 平台"
- "Sensor probe 失败，chip id 读不到，怎么排查？"
- "帮我写一个新 sensor 的 power_on 上电时序"
- "OV5695 的 v4l2_subdev_ops 应该实现哪些回调？"
- "帮我配置 sensor 的 DTS 节点，包括 clock、regulator、reset/pwdn GPIO"

**AI 会返回：**
- 完整的 Sensor 驱动移植框架（power sequence、stream on/off、enum_mbus_code 等）
- RK 平台标准的 Sensor DTS 模板（camera-module-index/facing/name）
- 上电时序诊断清单（regulator/clk/reset-gpio/pwdn-gpio 逐项检查）

### 功能 2：Camera DTS 链路配置

配置 MIPI CSI-2（DPHY/DCPHY/CPHY）、DVP（BT601/BT656/BT1120）接口的完整 DTS 链路。

**你可以这样提问：**
- "帮我配 RK3588 的 MIPI CSI2 DPHY 4lane 链路"
- "RK3568 两路 Camera 的 DTS 怎么写？"
- "DVP BT656 接口的 DTS 配置模板给一个"
- "csi2_dphy 的 split mode 和 full mode 怎么选？"

**AI 会返回：**
- 各平台完整的 DTS 链路配置（sensor → csi2_dphy → mipi_csi2 → vicap → isp）
- data-lanes 配置与 DPHY Split/Full Mode 选择指导
- DVP 各模式（BT601/BT656/BT1120）的节点配置差异

### 功能 3：多摄方案设计

RK3588 最多 7 路 Sensor 的多摄拓扑设计、分时复用、HDR、双 ISP 8K 合成。

**你可以这样提问：**
- "RK3588 怎么同时接 4 路 MIPI 摄像头？"
- "我要做双目摄像头方案，DPHY 链路怎么分配？"
- "HDR 模式需要几条 lane？DTS 怎么配？"
- "8K 双 ISP 合成怎么配置？"

**AI 会返回：**
- RK3588 完整的 DPHY/DCPHY 资源分配表
- 多摄拓扑图（哪些 DPHY 可以 split、哪些必须 full）
- HDR 多帧合成的 lane 分配与 ISP 虚拟设备配置

### 功能 4：MIPI 错误诊断与调试

SOT/ECC/CRC/PIC_SIZE_ERROR 等 MIPI CSI-2 错误的系统化排查。

**你可以这样提问：**
- "dmesg 中报 MIPI CRC error，怎么排查？"
- "Camera 出图花屏/绿屏"
- "media-ctl 命令怎么用？帮我查 Camera pipeline 拓扑"
- "v4l2-ctl 抓图命令怎么写？"

**AI 会返回：**
- MIPI CSI-2 错误诊断决策树（SOT → 信号质量、ECC → lane 配置、CRC → 数据完整性）
- media-ctl / v4l2-ctl 完整调试命令
- 花屏/绿屏/不出图的分类排查流程

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **Camera / 摄像头 / sensor / MIPI CSI / DPHY / DCPHY / DVP** 等关键词
- 提到 **VICAP / CIF / RKCIF / RKISP / V4L2 / v4l2-ctl / media-ctl** 等框架
- 提到 Sensor 型号：**IMX415 / IMX464 / OV5695 / OS04A10 / GC8034** 等
- 描述 Camera 相关症状：**不出图 / 花屏 / 绿屏 / 帧率低 / chip id 读失败 / stream on 失败**
- 提到 RK 特有属性：**camera-module-index / camera-module-facing / csi2_dphy / split mode**

## 文件结构

```
rk_camera/
├── SKILL.md                              # 主技能文件 (AI 自动加载, ~544 行)
├── README.md                             # 本说明文档 (供人阅读)
└── references/                           # 深入参考资料 (AI 按需加载)
    ├── sensor_driver_porting.md          # Sensor 驱动移植详解 + DTS 完整示例
    ├── rk3588_multi_camera.md            # RK3588 多摄方案 + DPHY/DCPHY 链路配置
    └── mipi_v4l2_debug.md               # MIPI CSI-2 错误诊断 + V4L2 调试命令
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 Camera 核心知识（链路模型、DTS 模板、错误诊断决策树）
- **references/**：AI 根据问题按需加载。例如：
  - 用户要移植新 Sensor → 加载 `sensor_driver_porting.md`
  - 用户配多摄/RK3588 → 加载 `rk3588_multi_camera.md`
  - 用户排查 MIPI 错误 → 加载 `mipi_v4l2_debug.md`

## 使用示例

### 示例 1：移植新 Sensor

**用户提问：**
> 帮我把 IMX464 移植到 RK3568 上，4lane MIPI，分辨率 2688×1520

**AI 行为：**
1. 自动触发 `rk_camera` 技能
2. 生成 Sensor DTS 节点（clock、regulator、reset/pwdn GPIO、data-lanes）
3. 给出 MIPI CSI2 DPHY → VICAP → ISP 完整链路 DTS
4. 提供驱动 probe 验证命令（dmesg grep、media-ctl topology）

### 示例 2：RK3588 四路摄像头

**用户提问：**
> RK3588 需要同时接 4 路 200 万 Camera，帮我设计 DPHY 链路分配

**AI 行为：**
1. 分析 RK3588 的 6 个 DPHY（csi2_dphy0~5）资源
2. 推荐 Split Mode 或 Full Mode 分配方案
3. 生成 4 路 Camera 的完整 DTS 链路配置
4. 提醒 ISP 虚拟设备数量限制和带宽评估

### 示例 3：MIPI 花屏排查

**用户提问：**
> RK3566 Camera 出图花屏，dmesg 有 CRC error

**AI 行为：**
1. 按 MIPI CSI-2 错误诊断决策树定位（CRC → 数据完整性）
2. 引导检查：data-lanes 配置、lane-rate、PCB 走线、Sensor 输出格式
3. 给出 v4l2-ctl 抓帧和 media-ctl 拓扑查看命令

## 知识来源

- Rockchip_Developer_Guide_Linux4.4_Camera_CN V2.0.0
- Rockchip_Trouble_Shooting_Linux4.4_Camera_CN
- Rockchip_Driver_Guide_VI_CN v1.1.1 / v1.1.3 (ISP2X / ISP3X / ISP21 / ISP32-lite)

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

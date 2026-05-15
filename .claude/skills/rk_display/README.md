# rk_display  Rockchip 显示子系统技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_display` 是一个面向 Rockchip 瑞芯微 SoC 平台的显示子系统 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip 平台的 MIPI DSI 面板移植、HDMI/DP/eDP 输出调试、VOP2 多屏显示配置、DRM 驱动分析等问题时，AI 会自动加载本技能，提供 RK 平台特有的显示通路架构、面板 init-sequence 编写、多屏图层分配等深度知识。

## 覆盖芯片

| 芯片 | 架构 | 显示能力 |
|------|------|---------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | VOP2 4VP, HDMI×2 + DP×2 + DSI×2 + eDP, 8K |
| **RK3568** | 4A55, Mali-G52 | VOP2 3VP, HDMI + DSI×2 + eDP/LVDS |
| **RK3566** | 4A55, Mali-G52 | VOP2 3VP, HDMI + DSI + LVDS |
| **RK3399 / RK3399Pro** | 2A72 + 4A53, Mali-T860 | VOP Big/Little, HDMI + DP + DSI×2 + eDP |
| **PX30 / RK3326** | 4A35, Mali-G31 | VOP, DSI + LVDS |

## 功能说明

### 功能 1：MIPI DSI 面板移植

从面板 datasheet 生成完整的 DSI panel DTS 配置，包括 init-sequence、display-timings、背光控制。

**你可以这样提问：**
- "帮我移植一块 1024×600 MIPI DSI 屏幕到 RK3568"
- "面板 init-sequence 怎么从 datasheet 的寄存器列表转换？"
- "DSI 面板用 panel-simple 还是 panel-dsi？"
- "PWM 背光怎么配？亮度反了怎么办？"
- "DSI2 和 DSI 有什么区别？RK3588 用哪个？"

**AI 会返回：**
- 完整的 DSI panel DTS 节点（panel-init-sequence、timings、backlight）
- init-sequence 格式规范（Generic Short/Long Write、DCS 命令编码）
- DSI 时钟计算方法（lane-rate 与 pixel clock 关系）
- panel-simple vs panel-dsi 选型指导

### 功能 2：HDMI / DP / eDP 输出调试

HDMI、DisplayPort、eDP 的配置、调试、EDID 分析与 Link Training 问题排查。

**你可以这样提问：**
- "RK3588 HDMI 输出没信号，怎么排查？"
- "HDMI 热插拔检测不到"
- "DP 输出分辨率不对，Link Training 失败"
- "eDP 面板点不亮，DTS 怎么配？"
- "HDCP 怎么启用？"

**AI 会返回：**
- HDMI/DP 调试命令（connector status、EDID dump、link status）
- HPD（热插拔）相关的 GPIO 和中断配置检查
- Link Training 失败分析（lane count、link rate、PHY 配置）
- eDP panel 的 DTS 配置和供电时序

### 功能 3：VOP2 多屏显示配置

VOP2 显示通路选择（VP0~VP3）、图层分配、多屏异显/同显方案。

**你可以这样提问：**
- "RK3568 怎么配 HDMI + MIPI DSI 双屏异显？"
- "VOP2 的 VP0、VP1、VP2 分别该连什么接口？"
- "baseparameter 分区是做什么的？怎么配？"
- "怎么调整图层 Plane 的优先级和分配？"
- "三屏输出时 Cluster/Esmart/Smart 图层怎么分？"

**AI 会返回：**
- VOP2 VP 到显示接口的路由配置（route_hdmi/route_dsi0 等）
- 图层类型（Cluster/Esmart/Smart）能力对比和分配策略
- 多屏 DTS 配置模板
- baseparameter 分区的配置工具和使用方法

### 功能 4：显示故障排查

黑屏、花屏、闪屏、分辨率异常、撕裂等显示问题的系统化诊断。

**你可以这样提问：**
- "板子上电后屏幕不亮，连 kernel logo 都没有"
- "MIPI 屏有显示但是花屏/闪白"
- "HDMI 输出有撕裂感"
- "modetest 测试命令怎么用？"

**AI 会返回：**
- 显示不亮分层排查（U-Boot logo → kernel DRM → 用户态 DE）
- MIPI 信号质量检查（lane-rate、timing 参数、init-sequence 时序）
- DRM 调试命令（modetest、connector/CRTC/encoder 状态查看）

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **显示 / display / 屏幕 / LCD / panel / 面板** 等关键词
- 提到 **VOP / VOP2 / MIPI DSI / HDMI / DP / eDP / LVDS / DRM** 等显示接口
- 提到 **modetest / connector / CRTC / encoder / plane / backlight** 等 DRM 概念
- 提到 RK 特有属性：**route_hdmi / route_dsi0 / panel-init-sequence / baseparameter**
- 描述显示相关症状：**黑屏 / 不亮 / 花屏 / 闪屏 / 撕裂 / 分辨率不对**

## 文件结构

```
rk_display/
├── SKILL.md                               # 主技能文件 (AI 自动加载, ~515 行)
├── README.md                              # 本说明文档 (供人阅读)
└── references/                            # 深入参考资料 (AI 按需加载)
    ├── mipi_dsi_panel_porting.md          # MIPI DSI 面板完整移植、init-sequence 编写、驱动 IC
    ├── hdmi_dp_debug.md                   # HDMI/DP/eDP/LVDS 深入调试、PHY 配置
    └── vop2_multi_display.md              # VOP2 架构、图层分配、多屏配置、baseparameter
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含显示核心知识（VOP2 架构、DSI/HDMI 配置模板、故障排查决策树）
- **references/**：AI 根据问题按需加载。例如：
  - 用户要移植 DSI 面板 → 加载 `mipi_dsi_panel_porting.md`
  - 用户调试 HDMI/DP → 加载 `hdmi_dp_debug.md`
  - 用户配多屏 → 加载 `vop2_multi_display.md`

## 使用示例

### 示例 1：移植 MIPI DSI 面板

**用户提问：**
> 帮我把一块 ILI9881C 驱动 IC 的 1280×800 MIPI DSI 屏移植到 RK3568

**AI 行为：**
1. 自动触发 `rk_display` 技能
2. 生成完整的 panel DTS 节点（init-sequence、display-timings、reset-gpio、backlight）
3. 配置 DSI host 节点和 route_dsi0
4. 提供验证命令（modetest、connector 状态查看）

### 示例 2：HDMI 无信号排查

**用户提问：**
> RK3588 HDMI 输出接电视没有信号，但系统已经正常启动

**AI 行为：**
1. 引导检查 connector status（是否 connected）
2. 检查 HPD GPIO 和 EDID 读取是否正常
3. 确认 VOP2 route 配置是否正确
4. 排查 HDMI PHY 和 HDCP 状态

### 示例 3：三屏异显配置

**用户提问：**
> RK3568 需要 HDMI + MIPI DSI + LVDS 三屏异显，DTS 怎么配？

**AI 行为：**
1. 分析 RK3568 VOP2 的 3 个 VP 资源
2. 分配 VP0→HDMI、VP1→DSI、VP2→LVDS
3. 生成三屏的 route 和 endpoint 配置
4. 说明图层（Cluster/Esmart/Smart）的分配策略

## 知识来源

- Rockchip DRM Display Driver 开发指南
- Rockchip DRM Panel Porting Guide
- Rockchip HDMI / DP / MIPI DSI2 开发文档
- Rockchip VOP2 Plane Assign 文档

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

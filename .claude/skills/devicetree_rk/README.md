# devicetree_rk  Rockchip 瑞芯微平台设备树技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`devicetree_rk` 是一个面向 Rockchip 瑞芯微 SoC 平台的设备树 (Device Tree) AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip 平台的设备树配置时，AI 会自动加载本技能，提供 RK 平台特有的 GPIO 编号、pinctrl mux 组、Combo PHY、PMIC、VOP2 显示通路等深度知识。

## 覆盖芯片

| 芯片 | 架构 | 典型产品 |
|------|------|----------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | 旗舰 SBC / 边缘 AI |
| **RK3568** | 4A55, Mali-G52 | 工业网关 / 广告机 |
| **RK3566** | 4A55, Mali-G52 | 平板 / 教育终端 |
| **RK3399 / RK3399Pro** | 2A72 + 4A53, Mali-T860 | 开发板 / Chromebook |
| **RK3328** | 4A53, Mali-450 | 电视盒子 / NAS |
| **RK3308** | 4A35 | 语音 / IoT |
| **PX30 / RK3326** | 4A35, Mali-G31 | 低功耗手持 / 电子书 |

## 功能说明

### 功能 1：RK 平台 DTS 编写

为 Rockchip 板卡编写设备树代码，涵盖 RK 平台特有的配置方式。

**你可以这样提问：**
- "帮我为 RK3566 板卡添加 GT911 触摸屏节点，挂在 I2C1，中断用 GPIO3_A1"
- "帮我写 RK3568 的 MIPI DSI 屏幕配置，面板分辨率 1024600"
- "帮我写一个 Overlay 启用 UART3 的 m1 mux 组"
- "帮我配 RK3566 的 HDMI + MIPI 双屏输出"
- "帮我配 rk809 PMIC 的 regulator 输出"

**AI 会返回：**
- 使用 RK 专用宏 (`RK_PA0`~`RK_PD7`) 的 DTS 代码
- 正确的 pinctrl mux 组 (m0/m1/m2) 选择
- VOP2 显示通路 (VP0/VP1) 连接配置
- Combo PHY 互斥关系提醒

### 功能 2：DTS 关系梳理

分析 Rockchip BSP 中的 DTS 层级结构和节点覆盖关系。

**你可以这样提问：**
- "帮我梳理 rk3566-lubancat-1-hdmi.dts 的 include 层级"
- "rk3566.dtsi 和 rk3568.dtsi 是什么关系？"
- "这个 GMAC 节点的 clock 引用链是什么？"
- "VOP2 的 endpoint 连接关系帮我理一下"

**AI 会返回：**
- RK BSP 标准的 DTS 分层图（SoC  变体  核心板  底板  显示）
- 节点属性覆盖路径追踪
- VOP2 显示管道连接关系

### 功能 3：问题排查

Rockchip 平台外设不工作、显示异常、启动失败等问题的系统化排查。

**你可以这样提问：**
- "RK3566 MIPI 屏不亮，帮我排查 DTS"
- "GT911 触摸没有响应，I2C 扫描不到设备"
- "RK3568 GMAC 网络不通"
- "USB3.0 设备插上没反应"
- "板子上电后 PMIC 不启动"

**AI 会返回：**
- RK 平台专用的诊断清单（按外设类型分类）
- 需要在板上执行的调试命令（`i2cdetect`、`pinmux-pins`、GPIO 状态等）
- RK 常见陷阱提醒（如 Combo PHY 互斥、mux 组选错、VOP2 VP 通路冲突）

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **RK3566 / RK3568 / RK3588 / RK3399 / PX30 / RK3328 / RK3308** 等芯片型号
- 提到 **Rockchip / 瑞芯微** 厂商名
- 提到 RK 板卡名称：**LubanCat / 鲁班猫 / 野火 / Rock-3A / EVB** 等
- 提到 RK 特有 DTS 属性：**rk809 / rk817 / VOP2 / Combo PHY / combphy / gmac1m0 / gmac1m1 / route_hdmi / route_dsi0 / video_phy0 / fiq-debugger** 等
- 使用 RK GPIO 宏格式：**GPIO3_A1 / RK_PA0** 等

## 文件结构

```
devicetree_rk/
 SKILL.md                              # 主技能文件 (AI 自动加载, ~340 行)
 README.md                             # 本说明文档 (供人阅读)
 references/                           # 深入参考资料 (AI 按需加载)
     display-subsystem.md              # VOP2/HDMI/MIPI DSI/eDP 显示子系统详细配置
     peripheral-bindings.md            # RK 常见外设 DTS 绑定完整参考 (GMAC/CSI/PMIC 等)
     troubleshooting-guide.md          # 扩展故障排查案例集 (MIPI 不亮/网络不通等)
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 RK 平台核心知识（GPIO 体系、pinctrl mux、Combo PHY、VOP2 通路、排查清单）
- **references/**：AI 根据问题按需加载。例如：
  - 用户要配 HDMI/DSI 显示  加载 `display-subsystem.md`
  - 用户要写外设节点  加载 `peripheral-bindings.md`
  - 用户排查复杂故障  加载 `troubleshooting-guide.md`

## 使用示例

### 示例 1：配置双屏显示

**用户提问：**
> 我的 RK3566 板卡需要 HDMI + MIPI DSI 双屏输出，帮我写 DTS

**AI 行为：**
1. 自动触发 `devicetree_rk` 技能
2. 根据 VOP2 双 VP 架构，分配 VP0HDMI、VP1DSI0
3. 生成 route 和 endpoint 配置代码
4. 提醒 `video_phy0` 需要启用

### 示例 2：排查 GMAC 网络不通

**用户提问：**
> RK3568 的千兆网口 ping 不通，ethtool 显示 link detected: no

**AI 行为：**
1. 自动触发 `devicetree_rk` 技能
2. 按 GMAC 诊断清单逐项检查
3. 重点提示：phy-mode、tx_delay/rx_delay、pinctrl mux (gmac1m0 vs gmac1m1)、PHY reset GPIO、drive level

### 示例 3：编写 UART Overlay

**用户提问：**
> 帮我写一个 RK3566 的 overlay，启用 UART3 使用 m1 引脚组

**AI 行为：**
1. 生成带 `/plugin/;` 的 overlay DTS
2. 使用正确的 pinctrl 引用 `&uart3m1_xfer`
3. 提醒需要检查 m1 引脚是否与其他外设冲突

## RK 平台特有知识点

本技能包含以下 Rockchip 独有的专业知识：

| 领域 | 内容 |
|------|------|
| **GPIO 编号** | `GPIOx_Yy` 格式、`RK_Pxy` 宏、bank32+offset 计算 |
| **pinctrl mux** | m0/m1/m2 多组复用、mux 组冲突检测 |
| **Combo PHY** | USB3/SATA/PCIe 互斥关系、各 SoC 的 PHY 数量 |
| **VOP2 显示** | VP0/VP1 通路选择、route 配置、endpoint 连接 |
| **PMIC** | rk809/rk817 regulator 配置、电压范围、中断 |
| **LubanCat 映射** | 板卡型号  DTS 文件名对照表 |

## 知识来源

- Rockchip 官方 BSP 源码与文档
- LubanCat / 野火开发板参考设计
- Rockchip 开发者社区 (opensource.rock-chips.com)
- Linux 内核 Rockchip binding 文档

## License

MIT License  自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

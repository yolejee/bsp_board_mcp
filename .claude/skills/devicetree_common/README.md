# devicetree_common  通用嵌入式 Linux 设备树技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`devicetree_common` 是一个**平台无关**的嵌入式 Linux 设备树 (Device Tree) AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论与设备树相关的任务时，AI 会自动加载本技能并获得专业的 DTS 领域知识，从而提供精准的代码生成、关系分析和故障排查辅助。

## 适用平台

本技能覆盖所有使用 Device Tree 的嵌入式 Linux 平台：

| 厂商 | 代表 SoC |
|------|---------|
| Rockchip | RK3566/RK3568/RK3588/RK3399/PX30 |
| 全志 Allwinner | A64/H6/H616/D1 |
| NXP | i.MX6/i.MX8/i.MX9 |
| TI (Texas Instruments) | AM335x/AM62x/AM64x/Sitara |
| Qualcomm | SDM845/SM8xxx/QCS |
| Samsung | Exynos |
| ST | STM32MP1/STM32MP2 |
| Broadcom | BCM2835 (Raspberry Pi) |
| Microchip/Atmel | SAMA5/SAM9 |
| Xilinx/AMD | Zynq/ZynqMP/Versal |
| RISC-V | StarFive JH71x0, SiFive, T-Head |

## 功能说明

### 功能 1：设备树编写与生成

为新板卡或新外设编写 DTS 代码。

**你可以这样提问：**
- "帮我写一个 GT911 触摸屏的 I2C 设备节点"
- "帮我写一个 MIPI DSI 面板的 display-timings"
- "帮我为这块板写一个 Device Tree Overlay 启用 SPI1"
- "帮我配置一个固定 3.3V 的 regulator 节点"

**AI 会返回：**
- 符合内核 binding 规范的 DTS 代码片段
- 关键属性的含义说明
- 需要根据原理图确认的参数提示

### 功能 2：设备树关系梳理

分析现有 DTS 文件的 include 层级、节点合并覆盖规则、phandle 引用关系。

**你可以这样提问：**
- "帮我梳理这个 board.dts 的 include 层级关系"
- "这个 UART 节点最终的属性是什么？有哪些文件覆盖了它？"
- "帮我追踪 clocks 属性引用的时钟源"
- "这两个 endpoint 的 remote-endpoint 是否正确配对？"

**AI 会返回：**
- 树状 include 层级图
- 属性合并后的最终结果
- phandle 引用链路追踪

### 功能 3：问题排查与诊断

外设不工作、DTS 编译报错、设备 probe 失败等问题的系统化排查。

**你可以这样提问：**
- "I2C 设备 probe 失败，帮我排查"
- "屏幕不亮，可能是 DTS 哪里配错了？"
- "dtc 编译报 unexpected token 怎么解决？"
- "GMAC 网络不通，帮我检查 DTS 配置"

**AI 会返回：**
- 按优先级排列的排查步骤
- 需要在目标板上执行的调试命令
- 常见错误模式和修复方案

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **设备树 / device tree / DTS / DTSI / DTB / DTBO / overlay** 等关键词
- 提到外设配置关键词：**compatible / pinctrl / regulator / display-timings / I2C / SPI / UART / GPIO / USB / PCIe / GMAC / HDMI / MIPI DSI** 等
- 描述嵌入式 Linux 硬件配置或外设驱动适配问题
- 即使没有明确说"设备树"，只要问题可能与 DTS 配置相关，也会触发

## 文件结构

```
devicetree_common/
 SKILL.md                              # 主技能文件 (AI 自动加载, ~350 行)
 README.md                             # 本说明文档 (供人阅读)
 references/                           # 深入参考资料 (AI 按需加载)
     dt-syntax-reference.md            # DTS 语法完整参考：数据类型、特殊节点、delete 语法
     peripheral-templates.md           # 全量外设 DTS 节点模板 (LED/I2C/SPI/UART/USB/PCIe/DSI/HDMI 等)
     overlay-guide.md                  # Device Tree Overlay 编写与调试完整指南
     multi-platform-pinctrl.md         # 11 个平台的 pinctrl binding 语法对比
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含核心知识（语法速查、编写指南、排查流程）
- **references/**：AI 根据具体问题按需加载。例如：
  - 用户要写外设节点  加载 `peripheral-templates.md`
  - 用户写 overlay  加载 `overlay-guide.md`
  - 用户问 pinctrl 跨平台差异  加载 `multi-platform-pinctrl.md`

## 使用示例

### 示例 1：生成 I2C 外设节点

**用户提问：**
> 帮我为一块 NXP i.MX8M 板卡添加 GT911 触摸屏设备树节点，挂在 I2C2 上，中断用 GPIO1_IO5，复位用 GPIO1_IO6

**AI 行为：**
1. 自动触发 `devicetree_common` 技能
2. 加载 `references/peripheral-templates.md` 获取 I2C 外设模板
3. 根据 i.MX8M 平台的 GPIO 和中断 binding 生成 DTS 代码
4. 标注需要根据原理图确认的参数（I2C 地址、中断极性等）

### 示例 2：排查 UART 不工作

**用户提问：**
> 我的 STM32MP157 板卡 UART4 不工作，TX 有信号但 RX 收不到数据

**AI 行为：**
1. 自动触发 `devicetree_common` 技能
2. 按 SKILL.md 中的通用排查流程引导
3. 提供调试命令（检查 status、pinctrl mux、clock、driver probe 状态）

### 示例 3：梳理 DTS 层级

**用户提问：**
> 帮我分析一下这个 board.dts 的 include 关系和节点覆盖链

**AI 行为：**
1. 分析所有 `#include` 指令，绘制树状层级图
2. 对关键节点追踪属性覆盖路径
3. 指出潜在冲突（如同一属性被多处覆盖）

## 知识来源

本技能的知识来源于：
- Linux 内核官方 Device Tree Specification
- 内核文档 `Documentation/devicetree/bindings/`
- 各 SoC 厂商 BSP 文档和参考设计
- eLinux.org Device Tree 社区资源

## License

MIT License  自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

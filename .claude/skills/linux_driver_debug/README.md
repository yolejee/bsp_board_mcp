# linux_driver_debug  通用 Linux 驱动调试技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`linux_driver_debug` 是一个**平台无关**的 Linux 设备驱动调试 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户遇到驱动 probe 失败、外设不工作、总线通信异常、电源管理问题等驱动层面的调试需求时，AI 会自动加载本技能，提供系统化的诊断方法和排查命令。

## 适用平台

本技能覆盖所有运行 Linux 内核的嵌入式平台，不含特定 SoC 寄存器细节：

| 平台 | 代表 SoC |
|------|---------|
| Rockchip | RK3566/RK3568/RK3588/RK3399/PX30 |
| 全志 Allwinner | A64/H6/H616/D1 |
| NXP | i.MX6/i.MX8/i.MX9 |
| TI | AM335x/AM62x/AM64x |
| ST | STM32MP1/STM32MP2 |
| Broadcom | BCM2835 (Raspberry Pi) |
| RISC-V | StarFive/SiFive |

## 功能说明

### 功能 1：设备 Probe 失败排查

诊断设备为什么没有成功 probe、驱动为什么没加载。

**你可以这样提问：**
- "设备 probe 失败返回 -517 是什么意思？"
- "为什么 /dev 下找不到我的设备？"
- "deferred probe 一直卡着怎么办？"
- "怎么看驱动有没有绑定到设备？"

**AI 会返回：**
- 设备/驱动匹配机制解释
- 系统化排查步骤和调试命令
- 常见错误码含义和修复方向

### 功能 2：总线驱动调试 (I2C/SPI/UART/GPIO)

外设通信异常的系统化排查。

**你可以这样提问：**
- "I2C 扫不到设备怎么办？"
- "SPI 收发数据全是 0xFF"
- "串口乱码怎么排查？"
- "GPIO 电平不对是什么原因？"

### 功能 3：子系统框架调试

clock、pinctrl、regulator、power domain、DMA、IOMMU 等内核子系统的调试。

**你可以这样提问：**
- "怎么看时钟有没有开？"
- "引脚复用配对了吗？"
- "regulator 供电链怎么查？"
- "IOMMU fault 怎么分析？"

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **驱动调试 / driver debug / probe 失败 / driver not bound / deferred probe** 等关键词
- 提到总线调试：**I2C / SPI / UART / GPIO / i2cdetect / spidev** 等
- 提到子系统：**clock / pinctrl / regulator / power domain / DMA / IOMMU**
- 提到外设驱动：**USB / PCIe / GMAC / MMC / eMMC** 等
- 描述外设不工作的问题（即使没有明确说"驱动"）

## 文件结构

```
linux_driver_debug/
 SKILL.md                                  # 主技能文件 (AI 自动加载, ~575 行)
 README.md                                 # 本说明文档 (供人阅读)
 references/                               # 深入参考资料 (AI 按需加载)
     probe_failure_debug.md                # probe 失败全流程、匹配机制、deferred probe、initcall、模块加载
     bus_driver_debug.md                   # I2C/SPI/UART/GPIO 深入调试、协议分析、中断调试
     subsystem_framework_debug.md          # clock/pinctrl/regulator/PD/DMA/IOMMU 框架深度调试
     peripheral_driver_debug.md            # USB/PCIe/GMAC/MMC 驱动调试、枚举流程、PHY调试
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含核心排查流程和速查表
- **references/**：AI 根据具体问题按需加载。例如：
  - 用户问 probe 失败 → 加载 `probe_failure_debug.md`
  - 用户调试 I2C/SPI → 加载 `bus_driver_debug.md`
  - 用户问 clock/regulator → 加载 `subsystem_framework_debug.md`
  - 用户调试 USB/PCIe/网卡 → 加载 `peripheral_driver_debug.md`

## 使用示例

### 示例 1：I2C 设备 probe 失败

**用户提问：**
> I2C 触摸屏 probe 失败，dmesg 显示 error -5

**AI 行为：**
1. 自动触发 `linux_driver_debug` 技能
2. 识别 error -5 = -EIO，硬件通信失败
3. 提供 I2C 诊断命令（i2cdetect 扫描、trace event）
4. 给出排查方向：供电、地址、上拉电阻、信号完整性

### 示例 2：设备存在但没有驱动绑定

**用户提问：**
> /sys/bus/platform/devices 下有我的设备，但没有 driver 链接

**AI 行为：**
1. 提供 compatible 匹配检查命令
2. 指导检查 CONFIG 和模块加载状态
3. 如果是 deferred probe，给出依赖链排查方法

### 示例 3：Regulator 启用失败

**用户提问：**
> 驱动中 regulator_enable 返回错误

**AI 行为：**
1. 提供 regulator_summary 查看命令
2. 检查 PMIC 驱动是否 probe 成功
3. 检查供电链和 I2C 通信

## 知识来源

本技能的知识来源于：
- Linux 内核源码 `drivers/base/`、`drivers/i2c/`、`drivers/spi/` 等
- Rockchip 官方外设驱动开发文档 (I2C/SPI/UART/USB/GMAC/PCIe/MMC)
- 内核文档 `Documentation/driver-api/` 和 `Documentation/devicetree/bindings/`
- 嵌入式 Linux 社区实践

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

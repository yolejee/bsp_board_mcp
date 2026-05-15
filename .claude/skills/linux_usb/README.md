# linux_usb — Linux USB 问题排查与调试技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`linux_usb` 是一个**多平台通用**的 Linux USB 问题排查与调试技能，专注于解决各类 USB 问题：USB 设备枚举与识别、主机控制器 (xHCI/EHCI/DWC2/DWC3) 调试、USB Gadget/OTG 模式配置、USB 类设备 (存储/HID/CDC/UVC) 调试、USB 电源管理与自动挂起、usbmon 抓包分析、USB Type-C/PD 配置、USB 性能优化。

## 适用平台

| 平台 | 芯片示例 | 适用性 |
|------|---------|-------|
| Rockchip 瑞芯微 | RK3588 / RK3568 / RK3566 | ✅ |
| AllWinner 全志 | A64 / H616 / T527 | ✅ |
| NXP i.MX | i.MX8M / i.MX6 | ✅ |
| TI Sitara | AM335x / AM62x | ✅ |
| STM32MP | STM32MP157 / STM32MP135 | ✅ |
| Broadcom | BCM2711 (RPi4) | ✅ |
| RISC-V | StarFive JH7110 / T-Head | ✅ |
| Qualcomm | QCS404 / Snapdragon | ✅ |

> 凡运行 Linux 内核且使用标准 USB 子系统的平台均适用。

## 功能说明

### 1. USB 枚举与识别排查
- **问题**: 设备插入后不识别, lsusb 看不到设备
- **方法**: dmesg 错误码分析, sysfs 设备检查, VBUS/PHY/信号排查

### 2. USB 控制器调试
- **问题**: 控制器 probe 失败, 端口不工作
- **方法**: 控制器类型识别 (xHCI/EHCI/DWC2/DWC3), debugfs, DTS 检查

### 3. USB Gadget/OTG
- **问题**: Gadget 设备主机端不识别, OTG 不自动切换
- **方法**: ConfigFS 配置, dr_mode, UDC 绑定, ID pin 检测

### 4. USB 类设备调试
- **工具**: lsblk (存储), evtest (HID), v4l2-ctl (UVC), ls /dev/ttyUSB* (串口)
- **方法**: 驱动模块检查, 设备节点验证

### 5. USB 电源管理
- **问题**: 设备频繁断连, 自动挂起
- **方法**: autosuspend 配置, VBUS 供电, 过流检测

### 6. USB 信号与性能
- **问题**: USB3 降速, 传输慢
- **方法**: 速率检查, usbmon 抓包, 线缆/PHY 排查

## 触发方式

当用户描述以下类型的问题时，本技能会被自动触发：

- 提到 USB 不识别、USB 设备不工作、lsusb
- 提到 USB 枚举失败、USB 断连
- 提到 xHCI、EHCI、DWC2、DWC3、USB 控制器
- 提到 USB Gadget、OTG、ConfigFS、dr_mode
- 提到 USB 存储/键盘/鼠标/摄像头/串口 问题
- 提到 USB autosuspend、VBUS、过流
- 提到 Type-C、USB PD、TCPM
- 提到 USB 速率、USB3 降速、传输慢

## 文件结构

```
linux_usb/
├── SKILL.md                                 # 主技能文件
├── README.md                                # 本说明文档
└── references/
    ├── usb_enumeration.md                   # USB 枚举完整流程
    ├── usb_gadget_guide.md                  # USB Gadget 开发指南
    └── usb_phy_debug.md                     # USB PHY 调试
```

## 文件加载机制

- `SKILL.md` 在技能触发时**自动加载**，提供完整的诊断决策树和常用命令
- `references/*.md` 按需加载，当 SKILL.md 中的内容不够详细时引用

## 使用示例

### 示例 1: USB 设备不识别
> 用户: "U 盘插入板子后 lsusb 看不到"

技能响应：检查 dmesg 枚举日志, 分析错误码, 排查 VBUS 供电/PHY 初始化/DTS 配置。

### 示例 2: USB Gadget 配置
> 用户: "想让板子作为 USB 串口 (ACM) 连接到 PC"

技能响应：提供 ConfigFS 配置步骤, 创建 ACM function, 绑定 UDC。

### 示例 3: USB 频繁断连
> 用户: "USB 摄像头使用一段时间后会自动断连"

技能响应：检查 autosuspend 设置, 禁用自动挂起, 检查 VBUS 供电电流。

## 知识来源

- Linux kernel Documentation/usb/
- USB 2.0 / USB 3.x 规范
- Linux USB Gadget 框架文档
- lsusb / usbmon / usbutils 工具文档
- 嵌入式 Linux USB 调试实践经验

## License

MIT License — 详见仓库根目录 LICENSE 文件

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

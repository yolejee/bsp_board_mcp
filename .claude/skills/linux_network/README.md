# linux_network — Linux 网络问题排查与调试技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`linux_network` 是一个**多平台通用**的 Linux 网络问题排查与调试技能，专注于解决各类网络问题：网络接口配置与管理、IP/路由/DNS 配置、连通性排查、网络性能测速 (iperf3)、抓包分析 (tcpdump)、以太网 PHY/MAC 调试 (ethtool)、WiFi/BT 连接、防火墙/NAT、网桥/VLAN/Bond 高级网络等。

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

> 凡运行 Linux 内核的嵌入式平台均适用。

## 功能说明

### 1. 网络连通性排查
- **问题**: ping 不通、连接超时、路由错误
- **方法**: 逐层排查 (物理→链路→网络→传输→应用), ARP/路由/DNS 检查

### 2. 网络性能测速
- **问题**: 网速慢、带宽不达标、丢包
- **工具**: iperf3 TCP/UDP 测速, 延迟测试, MTU 路径发现

### 3. 以太网 PHY/MAC 调试
- **问题**: 网口不亮、link 不起、速率异常
- **工具**: ethtool 链路/统计/寄存器, PHY 复位/时钟/IO 配置排查

### 4. WiFi/蓝牙调试
- **问题**: WiFi 连不上、信号弱、蓝牙配对失败
- **工具**: iw, wpa_supplicant, bluetoothctl, rfkill, btmon

### 5. 抓包与协议分析
- **方法**: tcpdump 过滤抓包, TCP 三次握手/重传分析, DHCP 流程分析

### 6. 防火墙/NAT/高级网络
- **方法**: iptables/nftables 规则管理, 网桥/VLAN/Bond 配置

## 触发方式

当用户描述以下类型的问题时，本技能会被自动触发：

- 提到网络不通、ping 不通、连接超时
- 提到 ethtool、PHY、MAC、RGMII、网口不亮
- 提到 iperf3、网速慢、丢包、带宽测试
- 提到 tcpdump、抓包、Wireshark
- 提到 iptables、nftables、防火墙、NAT
- 提到 WiFi、wpa_supplicant、蓝牙、bluetoothctl
- 提到 DHCP、DNS、路由、IP 配置
- 提到网桥、VLAN、Bond、链路聚合

## 文件结构

```
linux_network/
├── SKILL.md                                 # 主技能文件
├── README.md                                # 本说明文档
└── references/
    ├── network_performance.md               # 网络性能深度调优
    ├── phy_mac_debug.md                     # PHY/MAC 深度调试
    └── wifi_bt_guide.md                     # WiFi/BT 调试指南
```

## 文件加载机制

- `SKILL.md` 在技能触发时**自动加载**，提供完整的诊断决策树和常用命令
- `references/*.md` 按需加载，当 SKILL.md 中的内容不够详细时引用

## 使用示例

### 示例 1: 网口不通排查
> 用户: "我的嵌入式板子 eth0 ping 不通网关"

技能响应：按物理→链路→网络层逐步排查, 检查 ethtool link, IP/路由, ARP, 防火墙。

### 示例 2: 网络测速
> 用户: "千兆网口实测只有 300Mbps"

技能响应：使用 iperf3 测速, 检查 ethtool speed/duplex, 查看网卡统计错误计数, 检查 offload 配置。

### 示例 3: WiFi 连接问题
> 用户: "WiFi 扫描不到热点"

技能响应：检查 rfkill, iw dev, 无线驱动加载, 固件文件是否存在, wpa_supplicant 配置。

## 知识来源

- Linux kernel Documentation/networking/
- ethtool 官方文档
- iperf3, tcpdump, iw, wpa_supplicant 手册
- iptables/nftables 官方文档
- 嵌入式 Linux 网络调试实践经验

## License

MIT License — 详见仓库根目录 LICENSE 文件

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

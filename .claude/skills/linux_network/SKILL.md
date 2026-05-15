---
name: linux_network
description: "通用 Linux 网络问题排查与调试技能，不限于任何特定 SoC 平台。覆盖网络接口配置与管理、IP/路由/DNS 配置、网络连通性排查、网络性能测速 (iperf3/netperf)、抓包分析 (tcpdump/Wireshark)、以太网 PHY/MAC 调试 (ethtool/mdio)、WiFi/BT 连接问题、防火墙/NAT (iptables/nftables)、网桥/VLAN/Bond、socket 编程调试。触发关键词：网络、network、ping 不通、网络不通、DHCP、DNS、路由、ip addr、ip link、NetworkManager、ethtool、PHY、MAC、RGMII、iperf3、丢包、网速慢、tcpdump、Wireshark、iptables、NAT、端口转发、网桥、bridge、VLAN、bond、WiFi、wpa_supplicant、hostapd、蓝牙、Bluetooth、rfkill、socket、TCP、UDP、ss、netstat。当用户描述 Linux 网络层面的问题（连接问题、网速、丢包、网卡配置、WiFi/BT 等），都应触发本技能。"
---
<!-- ===== QUICK NAVIGATION ===== -->
| 快速导航 | 跳转链接 |
|---------|---------|
| 接口配置 | [§1](#1-网络接口配置与管理) |
| 连通性 | [§2](#2-网络连通性排查) |
| 性能测速 | [§3](#3-网络性能测速) |
| 抓包分析 | [§4](#4-抓包与协议分析) |
| PHY/MAC | [§5](#5-以太网-phymac-调试) |
| WiFi/BT | [§6](#6-wifibt-调试) |
| 防火墙 | [§7](#7-防火墙与-nat) |
| 高级网络 | [§8](#8-网桥vlanbond) |
| Socket | [§9](#9-socket-与连接调试) |
| DNS/DHCP | [§10](#10-dnsdhcp-排查) |
| 参考索引 | [§REF](#reference-index) |

---

## 诊断决策树
```
网络问题
├── 网络接口 down / 无 IP → §1 接口配置
├── ping 不通 → §2 连通性排查 (逐层: 链路→IP→路由→防火墙)
├── 能 ping 通但应用连不上 → §7 防火墙 + §9 Socket
├── 网络慢 / 带宽低 → §3 性能测速 + §5 PHY/MAC (半双工/速率)
├── 间歇性丢包 → §4 抓包 + §5 ethtool 统计
├── 网卡不识别 / link down → §5 PHY/MAC + DTS 检查
├── WiFi 连不上 / 断连 → §6 WiFi 调试
├── 蓝牙问题 → §6 BT 调试
├── DNS 解析失败 → §10 DNS 排查
└── DHCP 获取不到 IP → §10 DHCP 排查
```

---

## §1 网络接口配置与管理

### 1.1 ip 命令 (推荐)
```bash
# 查看所有接口:
ip link show                          # 接口状态
ip addr show                          # IP 地址
ip -s link show eth0                  # 统计信息 (RX/TX 字节、错误、丢包)

# 启用/禁用接口:
ip link set eth0 up
ip link set eth0 down

# 配置 IP:
ip addr add 192.168.1.100/24 dev eth0
ip addr del 192.168.1.100/24 dev eth0

# 配置路由:
ip route add default via 192.168.1.1 dev eth0
ip route add 10.0.0.0/8 via 192.168.1.1
ip route show                         # 查看路由表
ip route get 8.8.8.8                  # 测试特定目标的路由
```

### 1.2 网络管理服务
```bash
# systemd-networkd (嵌入式常用):
# 配置文件: /etc/systemd/network/*.network
# [Match]
# Name=eth0
# [Network]
# DHCP=yes
# # 或 Address=192.168.1.100/24, Gateway=192.168.1.1

systemctl status systemd-networkd
networkctl status eth0

# NetworkManager (桌面/复杂场景):
nmcli device status
nmcli connection show
nmcli connection modify eth0 ipv4.addresses "192.168.1.100/24"
```

---

## §2 网络连通性排查

### 2.1 逐层排查法
```bash
# Layer 1 - 物理层:
ethtool eth0 | grep "Link detected"   # 网线是否连接
# "Link detected: yes" → 物理层 OK

# Layer 2 - 数据链路层:
ip link show eth0                      # 查看 MAC 地址, 状态
arp -n                                 # ARP 表, 是否能解析网关 MAC
arping -I eth0 192.168.1.1             # ARP 级 ping

# Layer 3 - 网络层:
ping -c 4 192.168.1.1                  # ping 网关
ping -c 4 8.8.8.8                      # ping 外网 IP
ip route get 8.8.8.8                   # 路由是否正确

# Layer 4/7 - 传输层/应用层:
ping -c 4 www.baidu.com                # DNS + ICMP
curl -v http://www.baidu.com           # HTTP 请求
nc -zv 192.168.1.100 22                # 测试端口连通性
```

### 2.2 常见连通性问题排查
```bash
# "Network is unreachable":
ip route show                          # 检查默认路由是否存在

# "Destination Host Unreachable":
arp -n                                 # 检查网关 ARP 是否解析
ip addr show                           # 检查 IP 和子网是否正确

# "Connection refused":
ss -tlnp | grep <port>                 # 目标端口是否有监听

# "Connection timed out":
iptables -L -n -v                      # 检查防火墙规则
traceroute 目标IP                       # 检查路由路径
```

---

## §3 网络性能测速

### 3.1 iperf3 测速
```bash
# 服务端:
iperf3 -s

# 客户端 - TCP 测速:
iperf3 -c <server_ip> -t 30            # 30 秒 TCP 测试
iperf3 -c <server_ip> -t 30 -R         # 反向测试 (测下行)
iperf3 -c <server_ip> -P 4             # 4 并发流
iperf3 -c <server_ip> -w 256K          # 指定窗口大小

# 客户端 - UDP 测速:
iperf3 -c <server_ip> -u -b 100M       # UDP 100Mbps
iperf3 -c <server_ip> -u -b 1G         # UDP 1Gbps (测试千兆极限)
# 重点关注: Lost/Total, Jitter

# 常见 iperf3 问题:
# 速度远低于预期 → 检查 ethtool speed/duplex, MTU, offload 设置
# UDP 丢包严重 → 降低 -b 目标带宽, 检查中间设备 QoS
```

### 3.2 其他测速工具
```bash
# 简单下载测速:
wget -O /dev/null http://server/testfile     # HTTP 下载速度
dd if=/dev/zero bs=1M count=100 | nc -q 1 <server_ip> <port>  # 原始 TCP

# 延迟测试:
ping -c 100 -i 0.01 192.168.1.1              # 短间隔 ping
ping -f 192.168.1.1                           # flood ping (需 root)
# 关注: min/avg/max/mdev, 丢包率

# MTU 路径发现:
ping -c 4 -M do -s 1472 192.168.1.1          # 测试 MTU (1472+28=1500)
```

---

## §4 抓包与协议分析

### 4.1 tcpdump 常用命令
```bash
# 基础抓包:
tcpdump -i eth0                               # 抓取 eth0 所有包
tcpdump -i eth0 -c 100                        # 抓 100 个包
tcpdump -i eth0 -w /tmp/capture.pcap          # 保存为 pcap 文件

# 过滤:
tcpdump -i eth0 host 192.168.1.100            # 指定主机
tcpdump -i eth0 port 80                       # 指定端口
tcpdump -i eth0 tcp and port 22               # TCP + 端口
tcpdump -i eth0 icmp                          # 只抓 ICMP
tcpdump -i eth0 'src 192.168.1.100 and dst port 443'  # 组合

# 显示选项:
tcpdump -i eth0 -nn                           # 不解析主机名和端口名
tcpdump -i eth0 -X                            # 显示十六进制和 ASCII
tcpdump -i eth0 -e                            # 显示链路层头部
tcpdump -i eth0 -v                            # 详细模式
```

### 4.2 抓包分析要点
```
TCP 问题排查:
- 三次握手: SYN → SYN-ACK → ACK (缺少某步 → 连接问题)
- 重传 (Retransmission): 网络丢包或延迟大
- RST: 连接被拒绝
- Window Size = 0: 接收方缓冲区满

ARP 问题:
- 大量 ARP REQUEST 无 REPLY → 目标不存在或网络隔离
- Duplicate ARP → IP 冲突

DHCP 流程:
- DISCOVER → OFFER → REQUEST → ACK (缺少哪步看哪个环节有问题)
```

---

## §5 以太网 PHY/MAC 调试

### 5.1 ethtool 常用命令
```bash
# 查看链路参数:
ethtool eth0
# Speed: 1000Mb/s    → 协商速率
# Duplex: Full       → 全双工/半双工
# Link detected: yes → 链路状态
# Auto-negotiation: on

# 强制速率/双工:
ethtool -s eth0 speed 100 duplex full autoneg off

# 查看统计 (关键!):
ethtool -S eth0
# rx_errors, rx_crc_errors    → 物理层问题 (线缆/信号)
# rx_fifo_errors              → FIFO 溢出 (CPU 来不及处理)
# tx_carrier_errors           → 载波错误 (PHY 问题)
# collisions                  → 碰撞 (半双工或线缆问题)

# 查看驱动信息:
ethtool -i eth0
# driver: stmmac      → 使用的驱动
# firmware-version     → 固件版本

# 查看 offload 特性:
ethtool -k eth0
# rx-checksumming: on   → 硬件校验和
# tx-checksumming: on
# scatter-gather: on
# generic-segmentation-offload: on
```

### 5.2 PHY 寄存器调试
```bash
# 读 PHY 寄存器 (通过 MDIO):
# 需要 mii-tool 或 phytool 或 ethtool:
ethtool -d eth0                        # dump 驱动寄存器

# 常见 PHY 问题:
# Link 不起来:
#   1. 检查 PHY Reset GPIO 是否正确拉高
#   2. 检查 MDIO 通信 (能否读到 PHY ID)
#   3. 检查 DTS 中 phy-mode (rgmii/rmii/sgmii)
#   4. 检查 tx/rx delay 配置 (rgmii-rxid/rgmii-txid)
#   5. 检查时钟配置 (125MHz for RGMII 千兆)

# DTS 关键属性:
# phy-mode = "rgmii-rxid";  // rgmii/rgmii-id/rgmii-rxid/rgmii-txid/rmii
# phy-handle = <&phy0>;
# snps,reset-gpio = <&gpio3 RK_PB7 GPIO_ACTIVE_LOW>;
```

---

## §6 WiFi/BT 调试

### 6.1 WiFi 排查
```bash
# 检查无线接口:
iw dev                                 # 查看无线设备
iw phy                                 # 查看无线 PHY 能力
rfkill list                            # 查看射频开关状态

# 扫描 AP:
iw dev wlan0 scan | grep -E "SSID|signal|freq"

# wpa_supplicant 连接:
wpa_passphrase "SSID" "password" > /etc/wpa_supplicant.conf
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf
dhclient wlan0                         # 获取 IP

# 调试:
wpa_supplicant -i wlan0 -c /etc/wpa_supplicant.conf -d  # debug 模式
dmesg | grep -i wifi                   # 内核日志
dmesg | grep -i wlan
journalctl -u wpa_supplicant           # systemd 日志
```

### 6.2 蓝牙排查
```bash
# 查看蓝牙状态:
hciconfig -a                           # 或 bluetoothctl show
rfkill list bluetooth                  # 射频开关

# bluetoothctl 交互:
bluetoothctl
  power on
  agent on
  scan on                              # 扫描设备
  pair <MAC>                           # 配对
  connect <MAC>                        # 连接
  info <MAC>                           # 设备信息

# 调试:
btmon                                  # 实时 HCI 数据监控
dmesg | grep -i bluetooth
dmesg | grep -i "hci\|bt\|firmware"    # 固件加载日志
```

---

## §7 防火墙与 NAT

### 7.1 iptables 基础
```bash
# 查看规则:
iptables -L -n -v                      # 所有链
iptables -t nat -L -n -v               # NAT 表

# 允许/拒绝:
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -j DROP

# NAT / 端口转发:
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE       # 源 NAT (共享上网)
iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to 192.168.1.100:80
echo 1 > /proc/sys/net/ipv4/ip_forward                     # 开启转发

# 清除规则:
iptables -F                            # 清空 filter 表
iptables -t nat -F                     # 清空 NAT 表

# 排查时临时禁用防火墙:
iptables -P INPUT ACCEPT; iptables -P FORWARD ACCEPT; iptables -F
```

### 7.2 nftables (新一代)
```bash
# 查看规则:
nft list ruleset

# 基本操作:
nft add table inet filter
nft add chain inet filter input '{ type filter hook input priority 0; policy accept; }'
nft add rule inet filter input tcp dport 22 accept
```

---

## §8 网桥/VLAN/Bond

### 8.1 网桥 (Bridge)
```bash
# 创建网桥:
ip link add br0 type bridge
ip link set eth0 master br0
ip link set eth1 master br0
ip link set br0 up
ip addr add 192.168.1.1/24 dev br0

# 查看网桥:
bridge link show
bridge fdb show
```

### 8.2 VLAN
```bash
# 创建 VLAN 接口:
ip link add link eth0 name eth0.100 type vlan id 100
ip addr add 192.168.100.1/24 dev eth0.100
ip link set eth0.100 up
```

### 8.3 Bond 链路聚合
```bash
# 创建 bond:
ip link add bond0 type bond mode balance-rr   # 模式: balance-rr/active-backup/802.3ad
ip link set eth0 master bond0
ip link set eth1 master bond0
ip link set bond0 up
```

---

## §9 Socket 与连接调试

### 9.1 ss / netstat
```bash
# 查看所有监听端口:
ss -tlnp                               # TCP 监听
ss -ulnp                               # UDP 监听

# 查看所有连接:
ss -tnp                                # TCP 连接
ss -s                                  # 统计汇总

# 查看特定端口:
ss -tlnp | grep :80
```

### 9.2 连接调试
```bash
# 测试端口连通:
nc -zv <host> <port>                   # TCP
nc -zuv <host> <port>                  # UDP

# 检查 TIME_WAIT 堆积:
ss -s | grep TIME-WAIT
# 大量 TIME_WAIT → 调整:
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_fin_timeout=30
```

---

## §10 DNS/DHCP 排查

### 10.1 DNS 排查
```bash
# 检查 DNS 配置:
cat /etc/resolv.conf
resolvectl status                      # systemd-resolved

# 测试 DNS 解析:
nslookup www.baidu.com
dig www.baidu.com
host www.baidu.com

# DNS 不工作时:
# 1. 检查 /etc/resolv.conf 是否有正确的 nameserver
# 2. ping DNS 服务器 IP 是否可达
# 3. nslookup 指定 DNS: nslookup www.baidu.com 8.8.8.8
```

### 10.2 DHCP 排查
```bash
# 手动请求 DHCP:
dhclient -v eth0                       # verbose 模式
udhcpc -i eth0 -v                      # BusyBox dhcp

# 查看 DHCP 日志:
journalctl -u dhcpcd
journalctl -u systemd-networkd

# DHCP 不工作排查:
# 1. tcpdump -i eth0 port 67 or port 68  → 看有无 DISCOVER/OFFER
# 2. 无 DISCOVER → 接口可能 down 或 MAC 有问题
# 3. 有 DISCOVER 无 OFFER → DHCP 服务器问题或网络隔离
# 4. 有 OFFER 无 ACK → 客户端配置问题
```

---

## Reference Index

| 参考文件 | 内容概要 |
|---------|---------|
| [network_performance.md](references/network_performance.md) | 网络性能深度调优, TCP 参数优化, 网卡队列/中断亲和/GRO/TSO, 内核协议栈调优 |
| [phy_mac_debug.md](references/phy_mac_debug.md) | 以太网 PHY/MAC 深度调试, MDIO 寄存器, RGMII 时序, 常见 PHY 芯片 (RTL8211/YT8511) 问题 |
| [wifi_bt_guide.md](references/wifi_bt_guide.md) | WiFi/BT 模组驱动加载, 固件路径, wpa_supplicant 高级配置, BT HCI 调试, coexistence |

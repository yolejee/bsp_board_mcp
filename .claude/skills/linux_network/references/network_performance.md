# 网络性能深度调优

## 1. TCP 参数优化

### 1.1 TCP 缓冲区
```bash
# 查看当前 TCP 缓冲区设置:
sysctl net.ipv4.tcp_rmem    # 接收: min default max
sysctl net.ipv4.tcp_wmem    # 发送: min default max
sysctl net.core.rmem_max    # 全局最大接收
sysctl net.core.wmem_max    # 全局最大发送

# 千兆网络推荐:
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"

# 万兆网络或高延迟链路:
sysctl -w net.core.rmem_max=67108864
sysctl -w net.core.wmem_max=67108864
sysctl -w net.ipv4.tcp_rmem="4096 87380 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 65536 67108864"

# BDP (Bandwidth-Delay Product) 计算:
# 需要的缓冲区 ≥ 带宽 × RTT
# 例: 1Gbps, RTT=10ms → 1G/8 * 0.01 = 1.25MB
```

### 1.2 TCP 拥塞控制
```bash
# 查看可用拥塞算法:
sysctl net.ipv4.tcp_available_congestion_control

# 切换:
sysctl -w net.ipv4.tcp_congestion_control=bbr  # Google BBR (推荐)
modprobe tcp_bbr                                # 加载 BBR 模块

# BBR 优势: 高吞吐、低延迟, 特别适合高延迟/有丢包的网络
```

### 1.3 其他 TCP 优化
```bash
# TCP Fast Open (减少三次握手延迟):
sysctl -w net.ipv4.tcp_fastopen=3    # 客户端+服务端都启用

# Keepalive:
sysctl -w net.ipv4.tcp_keepalive_time=60
sysctl -w net.ipv4.tcp_keepalive_intvl=10
sysctl -w net.ipv4.tcp_keepalive_probes=6

# 连接回收:
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_fin_timeout=15

# listen backlog:
sysctl -w net.core.somaxconn=4096
sysctl -w net.ipv4.tcp_max_syn_backlog=8192
```

## 2. 网卡队列与中断优化

### 2.1 多队列与 RSS
```bash
# 查看网卡队列数:
ethtool -l eth0
# Combined: 4    → 4 个收发合一队列

# 设置队列数:
ethtool -L eth0 combined 4

# RSS (Receive Side Scaling) 哈希:
ethtool -x eth0                        # 查看 RSS 哈希表
ethtool -X eth0 equal 4                # 均匀分配到 4 个队列

# 中断亲和性:
# 查看网卡中断号:
grep eth0 /proc/interrupts
# 绑定到特定 CPU:
echo 1 > /proc/irq/<IRQ>/smp_affinity  # CPU0
echo 2 > /proc/irq/<IRQ>/smp_affinity  # CPU1
echo 4 > /proc/irq/<IRQ>/smp_affinity  # CPU2
```

### 2.2 RPS/RFS (软件层面)
```bash
# RPS (Receive Packet Steering) — 无多队列时的软件替代:
echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus   # 分散到 CPU0-3

# RFS (Receive Flow Steering) — 将包送到处理 socket 的 CPU:
echo 32768 > /proc/sys/net/core/rps_sock_flow_entries
echo 2048 > /sys/class/net/eth0/queues/rx-0/rps_flow_cnt
```

## 3. 硬件 Offload 调优

```bash
# 查看 offload 状态:
ethtool -k eth0

# 关键 offload:
ethtool -K eth0 rx-checksumming on     # 接收校验和卸载
ethtool -K eth0 tx-checksumming on     # 发送校验和卸载
ethtool -K eth0 gro on                 # Generic Receive Offload
ethtool -K eth0 tso on                 # TCP Segmentation Offload
ethtool -K eth0 gso on                 # Generic Segmentation Offload
ethtool -K eth0 sg on                  # Scatter-Gather

# 注意: 某些嵌入式网卡不支持所有 offload
# 如果开启后性能反而下降或出错 → 关闭对应 offload
```

## 4. 内核协议栈调优

```bash
# 网络设备队列长度 (发送):
ip link set eth0 txqueuelen 10000

# netdev_budget (NAPI):
sysctl -w net.core.netdev_budget=600          # 单次 poll 最大处理包数
sysctl -w net.core.netdev_budget_usecs=8000   # 单次 poll 最大时间

# backlog:
sysctl -w net.core.netdev_max_backlog=10000   # 队列积压上限

# ARP 表:
sysctl -w net.ipv4.neigh.default.gc_thresh3=4096   # 大型网络提高 ARP 表上限
```

## 5. MTU 与 Jumbo Frame

```bash
# 查看当前 MTU:
ip link show eth0 | grep mtu

# 设置 MTU:
ip link set eth0 mtu 9000              # Jumbo Frame (需要交换机支持)

# MTU 路径发现测试:
ping -c 4 -M do -s 8972 192.168.1.1   # 测试 9000 MTU (8972+28=9000)

# 注意: 嵌入式网卡可能不支持 Jumbo Frame
# 使用前确认: ethtool -i eth0 查看驱动是否支持
```

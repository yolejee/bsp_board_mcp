# 子系统性能专项参考（通用 Linux）

本文件包含 USB、PCIe、网络、多媒体、存储、显示、启动时间等子系统的性能排查详细指南。

## 目录

1. [USB 性能分析](#1-usb-性能分析)
2. [PCIe 性能分析](#2-pcie-性能分析)
3. [网络性能](#3-网络性能)
4. [多媒体性能](#4-多媒体性能)
5. [存储 IO 性能](#5-存储-io-性能)
6. [显示性能](#6-显示性能)
7. [启动时间优化](#7-启动时间优化)

---

## 1. USB 性能分析

### 1.1 USB 速度标准

| 标准 | 速度 | sysfs speed | 典型吞吐 |
|------|------|-------------|----------|
| USB 1.1 | 12 Mbps | 12 | ~1 MB/s |
| USB 2.0 | 480 Mbps | 480 | ~40 MB/s |
| USB 3.0 (Gen1) | 5 Gbps | 5000 | ~350 MB/s |
| USB 3.1 (Gen2) | 10 Gbps | 10000 | ~700 MB/s |
| USB 3.2 (Gen2x2) | 20 Gbps | 20000 | ~1.4 GB/s |

### 1.2 确认链路速度

```bash
# USB 设备树结构
lsusb -t

# 查看设备速度
cat /sys/bus/usb/devices/*/speed

# 查看 USB 控制器类型
cat /sys/bus/usb/devices/usb*/product
# EHCI = USB 2.0,  xHCI = USB 3.x,  OHCI/UHCI = USB 1.x
```

### 1.3 性能测试

```bash
# USB 存储读写测试
dd if=/dev/sda of=/dev/null bs=1M count=100 iflag=direct       # 读
dd if=/dev/zero of=/dev/sda bs=1M count=100 oflag=direct conv=fsync  # 写

# USB 网卡测试
iperf3 -c <server_ip> -t 30

# UVC 摄像头带宽
v4l2-ctl --list-formats-ext -d /dev/video0
```

### 1.4 常见问题排查

| 问题 | 可能原因 | 排查方法 |
|------|---------|---------|
| USB3 设备只跑 480Mbps | 插错口/线缆不支持 | 检查 `speed` 是否为 5000 |
| 传输速度远低于理论值 | URB 内存不足 | `echo 1024 > /sys/module/usbcore/parameters/usbfs_memory_mb` |
| UVC 摄像头卡顿 | 带宽超标/bulk 传输拥塞 | 降分辨率或用 MJPEG 格式 |
| USB 设备掉线 | 供电不足或信号问题 | 检查 `dmesg` 中 USB 错误 |
| U 盘写入卡顿 | 文件系统 journal 开销 | 用 `direct IO` 或 `fio` 排除文件系统因素 |

### 1.5 USB 调试

```bash
# 启用 USB 事件跟踪
echo 1 > /sys/kernel/debug/tracing/events/xhci-hcd/enable  # xHCI
echo 1 > /sys/kernel/debug/tracing/events/usb/enable

# usbmon（USB 包抓取）
modprobe usbmon
cat /sys/kernel/debug/usb/usbmon/0u     # bus 0 抓包
# 或用 Wireshark USB capture
```

---

## 2. PCIe 性能分析

### 2.1 PCIe 带宽理论值

| 规格 | 编码 | x1 | x2 | x4 | x8 | x16 |
|------|------|-----|-----|-----|-----|------|
| Gen1 (2.5GT/s) | 8b/10b | 250 MB/s | 500 MB/s | 1 GB/s | 2 GB/s | 4 GB/s |
| Gen2 (5GT/s) | 8b/10b | 500 MB/s | 1 GB/s | 2 GB/s | 4 GB/s | 8 GB/s |
| Gen3 (8GT/s) | 128b/130b | 1 GB/s | 2 GB/s | 4 GB/s | 8 GB/s | 16 GB/s |
| Gen4 (16GT/s) | 128b/130b | 2 GB/s | 4 GB/s | 8 GB/s | 16 GB/s | 32 GB/s |

### 2.2 链路状态检查

```bash
# 查看 PCIe 设备
lspci
lspci -vvv

# 关键字段：
# LnkCap: Speed 8GT/s, Width x4    → 设备能力
# LnkSta: Speed 8GT/s, Width x4    → 实际协商结果
# 如果 LnkSta < LnkCap → 信号质量问题或 DTS 配置问题

# 快速检查
lspci -vvv | grep -E "LnkCap|LnkSta"

# 查看 PCIe 控制器信息
ls /sys/bus/pci/devices/
cat /sys/bus/pci/devices/*/link_speed
cat /sys/bus/pci/devices/*/link_width
```

### 2.3 PCIe 性能测试

```bash
# NVMe SSD 测试
fio --name=seqread --ioengine=libaio --direct=1 --bs=128k \
    --numjobs=4 --size=1G --runtime=30 --rw=read --filename=/dev/nvme0n1

# PCIe 网卡测试
iperf3 -c <server_ip> -P 4 -t 30

# PCIe Wi-Fi 测试
iperf3 -c <server_ip> -t 30
iw dev wlan0 link
```

### 2.4 PCIe 电源管理对性能的影响

```bash
# ASPM（Active State Power Management）可能影响延迟
lspci -vvv | grep ASPM

# 关闭 ASPM 测试性能
echo performance > /sys/module/pcie_aspm/parameters/policy

# 或通过 bootargs
# pcie_aspm=off
```

---

## 3. 网络性能

### 3.1 链路检查

```bash
# 链路速度和双工模式
ethtool eth0

# 网络统计
ethtool -S eth0

# 查看丢包和错误
cat /proc/net/dev
ip -s link show eth0
```

### 3.2 吞吐量测试

```bash
# iperf3 基础测试
iperf3 -s                                    # 服务端
iperf3 -c <server_ip> -t 30                  # TCP 单流
iperf3 -c <server_ip> -P 4 -t 30             # TCP 多流
iperf3 -c <server_ip> -u -b 1G -t 30         # UDP
iperf3 -c <server_ip> -R                      # 反向测试

# netperf（更多高级选项）
netperf -H <server_ip> -t TCP_STREAM -l 30
netperf -H <server_ip> -t TCP_RR -l 30       # 请求/应答延迟
```

参考值：
- 千兆网：TCP 单流 ~940 Mbps
- 2.5G 网：TCP 单流 ~2.35 Gbps
- Wi-Fi 5 (AC): ~400-600 Mbps (取决于信道宽度)
- Wi-Fi 6 (AX): ~600-1200 Mbps

### 3.3 延迟测试

```bash
# ping
ping -c 100 <target_ip>
# 关注 avg 和 max

# 有线局域网参考：<1ms
# Wi-Fi 参考：1-5ms
```

### 3.4 网络优化

```bash
# 中断聚合
ethtool -C eth0 rx-usecs 100

# RX/TX ring buffer
ethtool -g eth0                    # 查看
ethtool -G eth0 rx 4096            # 增大

# RPS/RFS（软件接收负载均衡，多核网络）
echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus      # 分配到多个核
echo 32768 > /proc/sys/net/core/rps_sock_flow_entries

# TCP 参数调优
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"
```

### 3.5 RGMII 延迟线（嵌入式常见问题）

使用 RGMII 接口的以太网需要精确的延迟配置，否则可能丢包或降速：

```dts
/* DTS 通用格式 */
&gmac {
    phy-mode = "rgmii-id";         /* 由 PHY 提供延迟 */
    /* 或 */
    phy-mode = "rgmii-rxid";       /* PHY 提供 RX 延迟，MAC 端配 TX */
    /* 或 */
    phy-mode = "rgmii-txid";       /* 反过来 */
    /* 或 */
    phy-mode = "rgmii";            /* MAC 端提供双向延迟 */

    tx-delay = <0x28>;              /* TX 延迟值（平台相关）*/
    rx-delay = <0x11>;              /* RX 延迟值 */
};
```

> 延迟值需要根据 PCB 走线和 PHY 规格调整，通常由硬件工程师提供。

---

## 4. 多媒体性能

### 4.1 V4L2 硬件编解码

大多数嵌入式平台通过 V4L2 M2M (Memory-to-Memory) 接口暴露硬件编解码器：

```bash
# 查看 V4L2 设备
v4l2-ctl --list-devices

# 查看编解码器能力
v4l2-ctl -d /dev/video0 --list-formats
v4l2-ctl -d /dev/video0 --list-formats-out

# GStreamer 测试编解码
# 解码
gst-launch-1.0 filesrc location=test.mp4 ! qtdemux ! h264parse ! v4l2h264dec ! videoconvert ! autovideosink

# 编码
gst-launch-1.0 videotestsrc ! video/x-raw,width=1920,height=1080 ! v4l2h264enc ! h264parse ! mp4mux ! filesink location=out.mp4
```

### 4.2 FFmpeg 硬件加速

```bash
# 列出可用的硬件加速器
ffmpeg -hwaccels

# V4L2 M2M 解码
ffmpeg -hwaccel v4l2m2m -i input.mp4 -f null -

# DRM/KMS 直接输出
ffmpeg -hwaccel v4l2m2m -i input.mp4 -f drm /dev/dri/card0

# 编码性能测试
ffmpeg -i input.mp4 -c:v h264_v4l2m2m -b:v 5M output.mp4
```

### 4.3 多媒体性能指标

| 指标 | 测量方法 | 关注点 |
|------|---------|--------|
| 解码帧率 | ffmpeg 输出的 fps | 应≥目标帧率（如 4K@30 需≥30fps）|
| 编码帧率 | ffmpeg 编码速度 | 实时编码需 speed ≥ 1x |
| 端到端延迟 | 从采集到显示的时间差 | 实时应用通常要求<100ms |
| CPU 占用 | top 观察 ffmpeg 进程 | 硬件加速时 CPU 应很低 |

### 4.4 GPU 2D 加速器

不同平台的 2D 加速器：

| 平台 | 加速器 | 功能 |
|------|--------|------|
| Rockchip | RGA | 缩放/旋转/格式转换/混合 |
| NXP i.MX | PXP / G2D | 缩放/旋转/CSC |
| 全志 | G2D / DE2 | 缩放/旋转/混合 |
| TI | TIDSS | 显示加速 |

---

## 5. 存储 IO 性能

### 5.1 存储接口与速度

| 接口 | 常见模式 | 理论最高 |
|------|---------|---------|
| eMMC 4.5 (DDR52) | DDR52 | 104 MB/s |
| eMMC 5.0 (HS200) | HS200 | 200 MB/s |
| eMMC 5.1 (HS400) | HS400 | 400 MB/s |
| SD (UHS-I SDR104) | SDR104 | 104 MB/s |
| SD (UHS-II) | — | 312 MB/s |
| UFS 2.1 | HS-G3 2L | 1.2 GB/s |
| UFS 3.1 | HS-G4 2L | 2.3 GB/s |
| NAND (raw) | — | 取决于控制器和通道数 |

### 5.2 确认存储速度模式

```bash
# eMMC
cat /sys/kernel/debug/mmc0/ios
# 关注 timing spec 和 clock

# SD Card
cat /sys/kernel/debug/mmc1/ios

# NVMe
nvme smart-log /dev/nvme0
nvme id-ctrl /dev/nvme0

# SATA
hdparm -I /dev/sda | grep -E "Transport|speed"
```

### 5.3 IO 性能指标解读

```bash
# iostat 关键指标
iostat -x 1 5

# 字段说明：
# rrqm/s wrqm/s  - 每秒合并的读/写请求
# r/s    w/s     - 每秒完成的读/写请求
# rMB/s  wMB/s   - 每秒读/写吞吐量
# avgrq-sz       - 平均请求大小 (sector)
# avgqu-sz       - 平均队列深度
# await          - 平均 IO 等待时间 (ms)
# svctm          - 平均服务时间 (ms)
# %util          - 设备利用率 (>90% = IO 饱和)
```

### 5.4 IO 调度器选择

| 调度器 | 适用场景 | 说明 |
|--------|---------|------|
| `mq-deadline` | eMMC / UFS / NVMe | 保证请求在 deadline 内完成 |
| `bfq` | 多任务公平性要求高 | 基于预算的公平队列 |
| `none` (noop) | NVMe 等超高速设备 | 不做调度，直接下发 |
| `kyber` | 高 IOPS 设备 | 限制队列深度，控制延迟 |

```bash
# 查看和切换
cat /sys/block/mmcblk0/queue/scheduler
echo mq-deadline > /sys/block/mmcblk0/queue/scheduler
```

### 5.5 文件系统选择

| 文件系统 | 适用场景 | 特点 |
|---------|---------|------|
| ext4 | 通用 | 稳定、成熟、日志 |
| f2fs | 闪存 (eMMC/SD/SSD) | 闪存友好、随机写优化 |
| squashfs | 只读根文件系统 | 极高压缩比 |
| overlayfs | 只读底层+可写层 | 适合 OTA 方案 |
| btrfs | 需要快照/压缩 | 功能丰富但开销大 |

---

## 6. 显示性能

### 6.1 帧率检查

```bash
# DRM 信息
cat /sys/kernel/debug/dri/0/summary 2>/dev/null
cat /sys/kernel/debug/dri/0/state 2>/dev/null

# 连接器和分辨率
cat /sys/class/drm/card0-*/status
cat /sys/class/drm/card0-*/modes

# 帧率计数器（部分平台支持）
cat /sys/kernel/debug/dri/0/crtc-0/fps_sink 2>/dev/null
```

### 6.2 显示带宽计算

```
显示带宽 = 宽 × 高 × 颜色深度(bytes) × 刷新率 × 层数

示例：1920×1080×4(ARGB)×60Hz×2层 = 995 MB/s
4K: 3840×2160×4×60Hz×2层 = 3.97 GB/s
```

### 6.3 常见帧率问题

| 现象 | 可能原因 | 排查方法 |
|------|---------|---------|
| 帧率不到刷新率 | GPU 频率太低 | 定频 GPU 最高频测试 |
| 画面撕裂 | VSync 未开启 | 检查 DRM atomic / page flip |
| 动画卡顿 | 合成器瓶颈 | 检查 GPU 利用率和合成器日志 |
| 分辨率切换闪屏 | HDMI/DP 重新训练 | 检查 connector 日志 |
| 多显示器花屏 | DDR 带宽不足 | 提高 DDR 频率 |

---

## 7. 启动时间优化

### 7.1 测量方法

```bash
# systemd 分析（用户空间阶段）
systemd-analyze
systemd-analyze blame | head -20
systemd-analyze critical-chain

# 内核阶段
dmesg | head -5                                    # 最早的时间戳
dmesg | grep "Freeing unused kernel"               # 内核初始化完成

# 详细 initcall 分析
# bootargs 加入: initcall_debug printk.time=1
dmesg | grep initcall | sort -t= -k2 -n -r | head -20

# grabserial（串口精确计时）
grabserial -d /dev/ttyUSB0 -t -m "U-Boot" -q "login:"
```

### 7.2 各阶段优化方向

| 阶段 | 典型耗时 | 优化方向 |
|------|---------|---------|
| Bootloader (U-Boot) | 1-3s | 精简初始化、跳过 delay/menu |
| Kernel | 1-5s | 裁剪不用的驱动/编译为模块 |
| 用户空间 | 2-10s | systemd 精简/并行启动/按需加载 |

### 7.3 内核优化

```bash
# 1. 裁剪不需要的驱动
# 只编译必要的驱动为 built-in，其余编译为模块或不编译

# 2. 延迟加载
# bootargs: deferred_probe_timeout=1
# 非关键设备在 initramfs 后再探测

# 3. 压缩内核
# 使用 LZ4 压缩代替 gzip（解压更快）
# CONFIG_KERNEL_LZ4=y
```

### 7.4 用户空间优化

```bash
# 1. systemd 精简
# 禁用不需要的 service
systemctl disable <unnecessary.service>
systemctl mask <unnecessary.service>

# 2. 分析关键路径
systemd-analyze critical-chain <target.service>

# 3. 使用 socket activation 延迟启动
# 在 .service 文件中使用 After= / Wants= 控制依赖

# 4. 使用 init=/sbin/init 直接启动（不用 systemd）
# 最轻量但管理不便
```

# 子系统性能专项参考

本文件包含 USB、PCIe、网络、多媒体、存储等子系统的性能排查详细指南。

## 目录

1. [USB 性能分析](#1-usb-性能分析)
2. [PCIe 性能分析](#2-pcie-性能分析)
3. [网络/GMAC 性能](#3-网络gmac-性能)
4. [多媒体 MPP/RGA 性能](#4-多媒体-mpprga-性能)
5. [存储 IO 性能](#5-存储-io-性能)
6. [显示性能](#6-显示性能)
7. [启动时间优化](#7-启动时间优化)

---

## 1. USB 性能分析

### 1.1 确认 USB 链路速度

```bash
# 列出 USB 设备树
lsusb -t

# 查看设备速度
cat /sys/bus/usb/devices/*/speed
# 12=USB1.1  480=USB2.0  5000=USB3.0  10000=USB3.1

# 查看 USB 控制器
cat /sys/bus/usb/devices/usb*/product
```

### 1.2 性能测试

```bash
# USB 存储读写
dd if=/dev/sda of=/dev/null bs=1M count=100 iflag=direct
dd if=/dev/zero of=/dev/sda bs=1M count=100 oflag=direct conv=fsync

# USB 网卡
iperf3 -c <server_ip> -t 30
```

### 1.3 常见问题与优化

| 问题 | 原因 | 解决 |
|------|------|------|
| USB3 设备只跑 480Mbps | 插到了 USB2 口 | 确认物理接口是否 USB3 |
| 大量 URB 提交失败 | usbfs 内存不足 | `echo 1024 > /sys/module/usbcore/parameters/usbfs_memory_mb` |
| UVC 摄像头卡顿 | 带宽不足 | 降低分辨率或使用压缩格式 (MJPEG) |
| USB 有线网卡断连 | 供电不足 | 检查 USB VBUS 电源 |

### 1.4 USB 信号质量

```bash
# USB SQ 测试需要示波器配合
# RK 提供 USB SQ 测试工具，参考 Rockchip_Developer_Guide_USB_SQ_Test_CN.pdf
```

---

## 2. PCIe 性能分析

### 2.1 链路状态检查

```bash
# 查看 PCIe 设备
lspci -vvv

# 重点关注：
# LnkCap: Speed <expected>, Width <expected>   # 能力
# LnkSta: Speed <actual>, Width <actual>       # 实际

# 常见问题：LnkSta 速度低于 LnkCap → 信号质量问题
```

### 2.2 带宽理论值

| 规格 | x1 | x2 | x4 |
|------|-----|-----|-----|
| Gen2 (5GT/s) | ~500 MB/s | ~1 GB/s | ~2 GB/s |
| Gen3 (8GT/s) | ~1 GB/s | ~2 GB/s | ~4 GB/s |

### 2.3 性能测试

```bash
# NVMe SSD 测试
fio --name=seqread --ioengine=libaio --direct=1 --bs=128k \
    --numjobs=4 --size=1G --runtime=30 --rw=read --filename=/dev/nvme0n1

# PCIe 网卡测试
iperf3 -c <server_ip> -P 4 -t 30
```

### 2.4 RK PCIe 注意事项

- RK3568 有 1 个 PCIe 3.0 x2（可拆分为 2 个 x1）+ 1 个 PCIe 2.0 x1
- RK3588 有 1 个 PCIe 3.0 x4 + 1 个 PCIe 3.0 x2 + 1 个 PCIe 2.0 x1
- Combo PHY 复用：PCIe/SATA/USB3 共用 PHY，DTS 中需要正确配置

---

## 3. 网络/GMAC 性能

### 3.1 基本检查

```bash
# 链路速度
ethtool eth0 | grep Speed
# 预期: 1000Mb/s (千兆)

# 查看网络统计
ethtool -S eth0

# 查看丢包
cat /proc/net/dev
ifconfig eth0 | grep -E "errors|dropped"
```

### 3.2 吞吐量测试

```bash
# iperf3
iperf3 -s                           # 服务端
iperf3 -c <server_ip> -t 30         # TCP 测试
iperf3 -c <server_ip> -u -b 1G     # UDP 测试
iperf3 -c <server_ip> -P 4         # 多流测试

# 千兆参考：TCP 单流 940+ Mbps
```

### 3.3 GMAC 延迟线校准

RGMII 接口需要精确的延迟线配置，否则可能导致丢包或降速：

```bash
# 查看 RGMII 延迟
cat /sys/bus/mdio_bus/devices/*/phy_id

# DTS 配置
# tx_delay/rx_delay 需要根据实际硬件调试
```

参考文档：`Rockchip_Developer_Guide_Linux_GMAC_RGMII_Delayline_CN.pdf`

### 3.4 DPDK 高性能网络

DPDK 绕过内核协议栈，直接在用户态操作网卡，可大幅提升包处理性能。

```bash
# DPDK 编译和使用参考
# Rockchip_Developer_Guide_Linux_DPDK_CN.pdf
# Rockchip_Developer_Guide_Linux_GMAC_DPDK_CN.pdf
```

---

## 4. 多媒体 MPP/RGA 性能

### 4.1 MPP（Media Process Platform）

RK 硬件编解码接口：

```bash
# 查看 MPP 能力
cat /proc/mpp_service/dump/capability

# 常见编解码能力：
# RK3588: 8K@30fps H.265 解码, 8K@30fps H.265 编码
# RK3568: 4K@60fps H.265 解码, 4K@30fps H.265 编码
# RK3399: 4K@30fps H.265 解码, 1080P@30fps H.264 编码
```

### 4.2 RGA（Raster Graphic Acceleration）

2D 图形加速引擎，处理缩放、旋转、格式转换等：

```bash
# 查看 RGA 版本
cat /sys/kernel/debug/rkrga/driver_version

# RGA 能力：
# RGA2: 最大 8192×8192，约 1GB/s 带宽
# RGA3: 最大 8176×8176，4K@60fps

# 常见性能问题：
# - 软件回退：format 不支持导致 RGA 回退到 CPU
# - 分辨率超限：超过 RGA 最大支持尺寸
# - 多实例抢占：多路同时使用 RGA
```

### 4.3 编解码性能调优

```bash
# 确保 DDR 频率足够
echo performance > /sys/class/devfreq/dmc/governor

# RK3588 NPU SRAM 共享说明
# NPU 和 Video Codec 共享 SRAM，同时使用时可能互相影响
# 参考 RK3588_NPU_SRAM_usage.md
```

---

## 5. 存储 IO 性能

### 5.1 eMMC/SD 性能测试

```bash
# 顺序读
dd if=/dev/mmcblk0 of=/dev/null bs=1M count=100 iflag=direct

# 顺序写
dd if=/dev/zero of=/tmp/testfile bs=1M count=100 oflag=direct conv=fsync

# 随机读写 (fio)
fio --name=rand4k --ioengine=libaio --direct=1 --bs=4k \
    --numjobs=4 --size=256M --runtime=30 --rw=randrw --filename=/tmp/fio_test
```

### 5.2 eMMC 速度模式

```
HS400: ~300 MB/s (RK3588)
HS200: ~150 MB/s
SDR50:  ~50 MB/s
DDR50:  ~45 MB/s
SDR25:  ~25 MB/s
```

```bash
# 查看 eMMC 速度模式
cat /sys/kernel/debug/mmc0/ios
```

### 5.3 IO 调度器

```bash
# 查看当前调度器
cat /sys/block/mmcblk0/queue/scheduler

# 切换调度器
echo mq-deadline > /sys/block/mmcblk0/queue/scheduler

# 调整预读
blockdev --setra 2048 /dev/mmcblk0    # 单位：512B 扇区
```

### 5.4 文件系统优化

| 文件系统 | 适用场景 | 性能特点 |
|----------|----------|----------|
| ext4 | 通用 | 成熟稳定，随机写一般 |
| f2fs | Flash 设备 | 针对 NAND 优化，随机写更好 |
| squashfs | 只读 rootfs | 压缩存储，启动快 |

### 5.5 diskstats 字段说明

`/proc/diskstats` 各域含义：

| 域序号 | 含义 |
|--------|------|
| 4 | 读完成次数 |
| 5 | 合并读次数 |
| 6 | 读扇区数（重点关注） |
| 7 | 读花费毫秒数 |
| 8 | 写完成次数 |
| 9 | 合并写次数 |
| 10 | 写扇区数（重点关注） |
| 11 | 写花费毫秒数 |
| 12 | 正在处理的 IO 数（空闲时应为 0） |
| 13 | IO 操作花费毫秒数 |
| 14 | IO 加权毫秒数 |

---

## 6. 显示性能

### 6.1 帧率检查

```bash
# VOP summary
cat /sys/kernel/debug/dri/0/summary

# Vsync 调整（RK3588）
# 参考 Rockchip_RK3588_Developer_Guide_Vsync_Adjust_CN.pdf
```

### 6.2 显示带宽计算

VOP 带宽 = 分辨率 × 刷新率 × 像素深度 × 图层数

例如：1920×1080@60Hz × 4Bytes × 2 layers ≈ 995 MB/s

当 VOP 带宽需求高时，需确保 DDR 频率足够：

```dts
&dmc {
    vop-bw-dmc-freq = <
        0    577  200000
        578  1701 300000
        1702 99999 400000
    >;
};
```

### 6.3 常见显示性能问题

| 现象 | 可能原因 | 排查 |
|------|---------|------|
| 撕裂(tearing) | Vsync 未同步 | 检查 DRM atomic commit 模式 |
| 丢帧 | GPU 渲染慢或 DDR 带宽不足 | 定频 GPU+DDR 测试 |
| 闪屏 | 时序配置错误 | 检查 display-timings DTS |

---

## 7. 启动时间优化

### 7.1 分析启动时间

```bash
# 查看内核启动时间
dmesg | grep "Freeing unused kernel"

# systemd 启动分析
systemd-analyze
systemd-analyze blame
systemd-analyze critical-chain
```

### 7.2 优化方向

1. **提高 U-Boot CPU 频率**：默认低频启动，可配置提频
2. **裁剪 Kernel**：移除不需要的驱动（减小 Image 体积）
3. **减少 bootdelay**：U-Boot 等待时间设为 0
4. **延迟加载**：非关键驱动改为 module 按需加载
5. **rootfs 优化**：使用 squashfs 压缩只读根文件系统

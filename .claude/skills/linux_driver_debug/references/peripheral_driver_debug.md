# USB / PCIe / GMAC / MMC 外设驱动深度调试

## 目录

1. [USB 调试](#1-usb-调试)
2. [PCIe 调试](#2-pcie-调试)
3. [GMAC 网卡调试](#3-gmac-网卡调试)
4. [MMC / eMMC / SD 调试](#4-mmc-emmc-sd-调试)
5. [Watchdog 调试](#5-watchdog-调试)

---

## 1. USB 调试

### 1.1 USB 控制器类型

| 控制器 | 协议 | 速度 | 常见 IP |
|--------|------|------|--------|
| OHCI | USB 1.1 | 12 Mbps | 通用 |
| EHCI | USB 2.0 Host | 480 Mbps | SoC 集成 |
| xHCI | USB 3.0+ | 5/10 Gbps | DWC3/新平台 |
| DWC2 | USB 2.0 OTG | 480 Mbps | Rockchip/ST |
| DWC3 | USB 3.0 OTG | 5 Gbps | Rockchip/TI/NXP |
| MUSB | USB 2.0 OTG | 480 Mbps | TI Sitara |

### 1.2 USB 枚举调试

```bash
# 查看已枚举设备
lsusb
lsusb -t          # 树形 (显示速度/驱动)
lsusb -v -d <vid>:<pid>  # 详细描述符

# USB 设备详细信息
cat /sys/kernel/debug/usb/devices

# 枚举日志
dmesg | grep -i "usb\|hub\|port"

# 常见枚举失败日志:
# "unable to enumerate USB device" → PHY/信号/供电问题
# "device not accepting address" → 信号质量差 / PHY 配置错
# "device descriptor read/64, error -110" → 超时, 设备没响应
# "not running at top speed" → 降速, 信号完整性差
```

### 1.3 USB PHY 调试

```bash
# 查看 USB PHY
ls /sys/class/phy/

# USB 2.0 PHY 调测点:
# 1. VBUS 电压: 应为 5V±5%
# 2. D+/D- 差分信号: 眼图测试
# 3. PHY 时钟: 通常需要 480MHz

# DTS 中的 PHY 配置
# usb2_phy: usb2-phy@... {
#     rockchip,otg-vbus-gpios = <&gpio0 RK_PB7 GPIO_ACTIVE_HIGH>;
# };
```

### 1.4 USB OTG 调试

```bash
# 查看 OTG 模式
cat /sys/devices/platform/*.usb/role

# DTS dr_mode 配置:
# dr_mode = "host";          # 固定 Host
# dr_mode = "peripheral";    # 固定 Device
# dr_mode = "otg";           # 自动切换 (需 id-pin/typec)

# 手动切换角色 (部分平台)
echo host > /sys/devices/platform/*.usb/role
echo device > /sys/devices/platform/*.usb/role
```

### 1.5 USB Gadget 调试

```bash
# 查看 UDC
ls /sys/class/udc/

# ConfigFS Gadget 配置
ls /sys/kernel/config/usb_gadget/

# 常见 Gadget function:
# mass_storage, acm (serial), ecm/rndis (network), hid, uvc

# usbmon 抓包
modprobe usbmon
cat /sys/kernel/debug/usb/usbmon/0u    # 所有 bus
# 或使用 wireshark + usbmon
```

---

## 2. PCIe 调试

### 2.1 PCIe 拓扑查看

```bash
# 列出设备
lspci
lspci -tv            # 树形拓扑

# 详细信息
lspci -vvv -s <BDF>  # BDF = Bus:Device.Function

# 查看链路速度
lspci -vvv | grep -E "LnkCap|LnkSta"
# LnkCap: Speed 8GT/s, Width x4    ← 能力
# LnkSta: Speed 8GT/s, Width x4    ← 实际
```

### 2.2 PCIe Link 训练失败

```bash
dmesg | grep -i "pcie\|link"

# 常见日志:
# "PCIe link down" → Link 训练失败
# 排查顺序:
# 1. PERST# GPIO: 检查复位信号时序
# 2. CLKREQ#: 参考时钟请求
# 3. 参考时钟: 100MHz refclk 是否正常
# 4. PHY: lane 数量和速度匹配
# 5. 电源: 12V/3.3V 供电
# 6. 物理连接: 金手指接触
```

### 2.3 PCIe BAR/Resource

```bash
# 查看 BAR 分配
lspci -vvv -s <BDF> | grep "Region"
cat /sys/bus/pci/devices/<BDF>/resource

# BAR 分配失败:
# "BAR N: can't assign" → 地址空间不够
# 检查 DTS 中 ranges 是否足够大
# 32-bit BAR 最多 4GB, 64-bit BAR 无限制
```

### 2.4 PCIe 设备驱动问题

```bash
# 查看设备绑定的驱动
ls -l /sys/bus/pci/devices/<BDF>/driver

# 手动绑定/解绑
echo <BDF> > /sys/bus/pci/drivers/<drv>/unbind
echo <BDF> > /sys/bus/pci/drivers/<drv>/bind

# PCIe 设备重新扫描
echo 1 > /sys/bus/pci/rescan
```

---

## 3. GMAC 网卡调试

### 3.1 基本诊断

```bash
# 查看接口状态
ip link show
ethtool eth0
ethtool -i eth0    # 驱动信息
ethtool -S eth0    # 统计计数 (收发/错误/丢包)

# PHY 信息
ethtool eth0       # Speed/Duplex/Link detected
cat /sys/class/net/eth0/carrier    # 1=有link

# 查看 MDIO 上的 PHY
ls /sys/bus/mdio_bus/*/
```

### 3.2 网卡不通排查流程

```
网卡不通
├── Link 不起 (carrier=0)
│   ├── PHY 没 probe → 检查 MDIO/MDC 信号, PHY 供电/复位
│   ├── PHY ID 读不到 → MDIO 通信失败, 检查地址
│   ├── Link 训练失败 → 检查网线/对端/自协商
│   └── RGMII delayline → 调整 tx/rx delay
├── 有 Link 无数据 (ping 不通)
│   ├── MAC/PHY 接口不匹配 → 检查 phy-mode
│   ├── Delayline 不对 → 调整 DTS tx/rx delay
│   ├── IP 配置错误 → 检查 IP/子网/路由
│   └── IOMMU fault → 检查 DMA 映射
└── 有数据但丢包
    ├── 延迟大 → 中断合并配置
    ├── 半双工 → ethtool 强制全双工
    └── ring buffer 小 → ethtool -G eth0 rx 4096
```

### 3.3 RGMII Delay 调整

```dts
// DTS 中 GMAC delay 配置 (Rockchip)
&gmac1 {
    phy-mode = "rgmii-id";        // PHY 内部 delay
    // 或:
    phy-mode = "rgmii";            // 外部 delay
    tx_delay = <0x3c>;             // TX delay (十六进制)
    rx_delay = <0x2f>;             // RX delay

    // delay 的值需要根据 PHY 芯片和板子走线调试
    // 方法: 二分法调整, 跑 iperf 测试吞吐量
};

// 测试命令
iperf3 -s              // 服务端
iperf3 -c <ip> -t 60   // 客户端, 测 60 秒
```

### 3.4 PHY 寄存器读写

```bash
# 使用 mdio-tools (如果有)
mdio-tool read eth0 <phy_addr> <reg>
mdio-tool write eth0 <phy_addr> <reg> <value>

# 使用 ethtool
# 查看 PHY ID (寄存器 2/3)
ethtool -d eth0    # dump 寄存器 (部分驱动支持)

# 使用 devmem2 (需要知道 MDIO 寄存器地址)
# 或通过 debugfs (部分驱动提供)
```

---

## 4. MMC / eMMC / SD 调试

### 4.1 MMC 子系统检查

```bash
# 查看 MMC host
ls /sys/class/mmc_host/

# 查看已识别的卡
ls /sys/bus/mmc/devices/
cat /sys/bus/mmc/devices/mmc*:*/type     # SD/MMC/SDIO
cat /sys/bus/mmc/devices/mmc*:*/name
cat /sys/bus/mmc/devices/mmc*:*/hwrev

# 查看当前 IO 设置
cat /sys/class/mmc_host/mmc0/ios
# clock: 当前时钟频率
# timing: 通信模式 (legacy/sd-hs/mmc-hs200/mmc-hs400)
# bus width: 1/4/8
```

### 4.2 MMC 识别失败

```bash
dmesg | grep -i "mmc\|sdhci\|dwmmc"

# 常见日志:
# "mmc0: error -110 whilst initialising" → 超时, 卡没响应
#   → 检查供电 (VCCQ/VCC)
#   → 检查 CMD/CLK/DAT 信号
#   → 检查 DTS 中 bus-width, max-frequency

# "mmc0: tuning failed" → 速度模式切换失败
#   → 降速: 减小 max-frequency
#   → 或禁用高速模式: no-mmc-hs200, no-mmc-hs400

# "mmc0: card never left busy state" → 卡忙
#   → 卡损坏或供电不足
```

### 4.3 MMC DTS 配置

```dts
// eMMC 配置
&sdhci {
    bus-width = <8>;
    max-frequency = <200000000>;
    mmc-hs200-1_8v;
    mmc-hs400-1_8v;
    non-removable;
    status = "okay";
};

// SD 卡配置
&sdmmc0 {
    bus-width = <4>;
    max-frequency = <150000000>;
    cap-sd-highspeed;
    sd-uhs-sdr104;
    cd-gpios = <&gpio0 RK_PA4 GPIO_ACTIVE_LOW>;  // 卡检测
    vmmc-supply = <&vcc_3v3>;
    vqmmc-supply = <&vccio_sd>;
    status = "okay";
};
```

### 4.4 MMC 性能测试

```bash
# 读速度
dd if=/dev/mmcblk0 of=/dev/null bs=4M count=256

# 写速度
dd if=/dev/zero of=/dev/mmcblk0p1/testfile bs=4M count=64 oflag=direct

# 或使用 fio
fio --name=seq_read --filename=/dev/mmcblk0 --rw=read --bs=128k \
    --ioengine=libaio --iodepth=32 --direct=1 --size=512M
```

---

## 5. Watchdog 调试

### 5.1 基本使用

```bash
# 查看 watchdog 设备
ls /dev/watchdog*
cat /sys/class/watchdog/watchdog0/status
cat /sys/class/watchdog/watchdog0/timeout

# 测试 watchdog
echo V > /dev/watchdog    # 关闭 watchdog (Magic close)
echo 1 > /dev/watchdog    # 启动 watchdog (写任意字符喂狗)

# DTS 配置
&wdt {
    status = "okay";
};
```

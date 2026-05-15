---
name: linux_usb
description: "通用 Linux USB 问题排查与调试技能，不限于任何特定 SoC 平台。覆盖 USB 设备枚举与识别、主机控制器 (xHCI/EHCI/DWC2/DWC3) 调试、USB Gadget/OTG 模式配置、USB 类设备 (存储/HID/CDC/UVC/UAC) 调试、USB 电源管理与唤醒、usbmon 抓包分析、USB 速率与性能优化。触发关键词：USB、USB 枚举、USB 不识别、lsusb、usbmon、xHCI、EHCI、DWC2、DWC3、USB host、USB gadget、USB OTG、dr_mode、USB Type-C、TCPM、PD 协议、VBUS、autosuspend、USB 2.0、USB 3.0、SuperSpeed、configfs、g_serial、g_ether、FunctionFS、USB hub、USB PHY、眼图、U 盘、USB 串口、USB 摄像头、USB 传输慢、USB 断连。当用户描述 Linux USB 层面的问题（USB 设备不识别、USB 功能异常、OTG 配置、Type-C 等），都应触发本技能。"
---
<!-- ===== QUICK NAVIGATION ===== -->
| 快速导航 | 跳转链接 |
|---------|---------|
| 枚举排查 | [§1](#1-usb-设备枚举与识别) |
| 控制器 | [§2](#2-usb-主机控制器调试) |
| Gadget/OTG | [§3](#3-usb-gadgetotg) |
| 类设备 | [§4](#4-usb-类设备调试) |
| 电源管理 | [§5](#5-usb-电源管理) |
| 抓包 | [§6](#6-usbmon-抓包分析) |
| Type-C | [§7](#7-usb-type-c-与-pd) |
| DTS 配置 | [§8](#8-usb-dts-配置) |
| 性能 | [§9](#9-usb-性能优化) |
| 常见问题 | [§10](#10-常见-usb-问题速查) |
| 参考索引 | [§REF](#reference-index) |

---

## 诊断决策树
```
USB 问题
├── lsusb 看不到设备 → §1 枚举排查 (接口/供电/信号)
├── 设备识别但功能异常 → §4 类设备调试 + §6 usbmon
├── USB 控制器 probe 失败 → §2 控制器 + §8 DTS
├── USB Gadget 不工作 → §3 Gadget/OTG 配置
├── USB 频繁断连 → §5 电源管理 (autosuspend) + 信号质量
├── USB 传输慢 → §9 性能优化
├── Type-C 检测问题 → §7 Type-C/PD
├── OTG 主从切换异常 → §3 dr_mode 配置
└── USB PHY 初始化失败 → §8 DTS + PHY 驱动
```

---

## §1 USB 设备枚举与识别

### 1.1 基础检查
```bash
# 查看 USB 设备:
lsusb                                  # 简要列表
lsusb -t                               # 树状拓扑
lsusb -v -d <VID>:<PID>               # 详细描述符
usb-devices                            # 详细设备信息

# 查看内核日志:
dmesg | grep -i usb
dmesg | tail -20                       # 插入设备后查看最新日志

# 正常枚举日志:
# "usb 1-1: new high-speed USB device number 2 using xhci-hcd"
# "usb 1-1: New USB device found, idVendor=1234, idProduct=5678"
# "usb 1-1: Product: My USB Device"
```

### 1.2 枚举失败排查
```bash
# 常见枚举错误:

# "device not accepting address N, error -62"
# → -ETIME, 设备未响应
# → 检查: USB 线缆, 供电, PHY 配置

# "unable to enumerate USB device"
# → 多次重试失败
# → 检查: USB PHY 时钟, Reset, VBUS

# "device descriptor read/64, error -71"
# → -EPROTO, 协议错误
# → 检查: USB 信号质量, 线缆质量

# "Cannot enable port N. Maybe the USB cable is bad?"
# → 端口使能失败
# → 检查: 供电, 过流保护, hub

# "USB disconnect" (刚连上就断)
# → 可能供电不足, 或 autosuspend 导致
# → 尝试: echo -1 > /sys/bus/usb/devices/<dev>/power/autosuspend
```

### 1.3 USB 地址与路径
```bash
# USB 设备路径格式:
# usb<bus>-<port>[.<port>]...
# 例: usb1-1.2 → 总线1, 根hub的端口1, 下级hub的端口2

# sysfs 路径:
ls /sys/bus/usb/devices/
# 1-0:1.0  → 总线1根hub的接口0
# 1-1      → 总线1端口1的设备
# 1-1:1.0  → 总线1端口1设备的配置1接口0

# 查看设备描述符:
cat /sys/bus/usb/devices/1-1/idVendor
cat /sys/bus/usb/devices/1-1/idProduct
cat /sys/bus/usb/devices/1-1/speed     # 速率 (12/480/5000)
```

---

## §2 USB 主机控制器调试

### 2.1 控制器类型
```
控制器        速率            常见 SoC
──────────────────────────────────────────────────
OHCI         USB 1.1 (12M)   旧芯片 Full-Speed
EHCI         USB 2.0 (480M)  大多数带 USB2 的 SoC
xHCI         USB 3.x (5G+)   新型 SoC (RK3588 等)
DWC2         USB 2.0 OTG     RK3399/RK3328/STM32/全志等
DWC3         USB 3.x OTG     RK3588/RK3568/i.MX8 等
MUSB         USB 2.0 OTG     TI AM335x/AM62x
ChipIdea     USB 2.0 OTG     NXP i.MX6/i.MX8
```

### 2.2 控制器调试
```bash
# 查看当前使用的控制器:
cat /sys/bus/usb/devices/usb1/product
# xHCI Host Controller → xHCI
# EHCI Host Controller → EHCI
# DWC OTG Controller   → DWC2

# 检查控制器是否 probe 成功:
dmesg | grep -iE "xhci|ehci|ohci|dwc|musb|chipidea"
# 正常: "xhci-hcd xxx: xHCI Host Controller"
# 失败: "probe failed" / "unable to init"

# 检查控制器驱动:
lsmod | grep -iE "xhci|ehci|ohci|dwc|musb"

# debugfs:
ls /sys/kernel/debug/usb/
# 可能有 xhci/ ehci/ ohci/ 等目录
```

---

## §3 USB Gadget/OTG

### 3.1 dr_mode 配置
```dts
/* DTS 中 USB 控制器的模式配置 */
&usb_otg {
    dr_mode = "host";        /* 仅主机模式 */
    /* dr_mode = "peripheral"; */  /* 仅从机模式 (gadget) */
    /* dr_mode = "otg"; */         /* OTG 模式 (自动切换) */
    status = "okay";
};
```

### 3.2 USB Gadget ConfigFS
```bash
# 使用 ConfigFS 创建 USB Gadget:
cd /sys/kernel/config/usb_gadget
mkdir g1 && cd g1

# 设置设备描述符:
echo 0x1d6b > idVendor       # Linux Foundation
echo 0x0104 > idProduct
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

# 字符串:
mkdir strings/0x409
echo "My Device" > strings/0x409/product
echo "123456789" > strings/0x409/serialnumber
echo "ovcell" > strings/0x409/manufacturer

# 配置:
mkdir configs/c.1
mkdir configs/c.1/strings/0x409
echo "Config 1" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower

# --- 添加功能 (选一或多) ---

# USB 串口 (ACM):
mkdir functions/acm.usb0
ln -s functions/acm.usb0 configs/c.1/

# USB 网卡 (ECM/RNDIS):
mkdir functions/ecm.usb0
ln -s functions/ecm.usb0 configs/c.1/

# USB 大容量存储:
mkdir functions/mass_storage.usb0
echo /dev/mmcblk0 > functions/mass_storage.usb0/lun.0/file
ln -s functions/mass_storage.usb0 configs/c.1/

# --- 绑定到 UDC ---
ls /sys/class/udc/                    # 查看可用 UDC
echo <udc_name> > UDC                 # 绑定, 设备出现在主机端
```

### 3.3 OTG 调试
```bash
# ID pin 检查 (OTG 主从切换):
# ID=0 → Host mode (插入 OTG 线)
# ID=1 → Device mode (默认)
cat /sys/bus/usb/devices/usb*/otg_state  # OTG 状态

# 手动切换 (部分平台支持):
echo host > /sys/bus/platform/devices/<usb>/role
echo device > /sys/bus/platform/devices/<usb>/role

# OTG 不切换排查:
# 1. 检查 ID pin GPIO 配置 (DTS)
# 2. 检查 USB PHY 的 OTG 支持
# 3. dmesg | grep otg
```

---

## §4 USB 类设备调试

### 4.1 USB 存储 (Mass Storage)
```bash
# 检查:
lsblk                                  # 查看块设备
dmesg | grep -i "scsi\|sd\|usb-storage"
# 正常: "Attached SCSI removable disk"
# 文件系统: mount /dev/sda1 /mnt

# 不出块设备:
# 检查 CONFIG_USB_STORAGE=y
# 检查文件系统支持 (vfat/ntfs/exfat)
```

### 4.2 USB HID (键盘/鼠标)
```bash
# 检查:
cat /proc/bus/input/devices | grep -A 5 -i usb
ls /dev/input/event*
evtest /dev/input/eventN              # 实时显示事件

# HID 不工作: 检查 CONFIG_USB_HID=y
```

### 4.3 USB 串口 (CDC ACM / CP2102 / CH340 / FTDI)
```bash
# 检查:
ls /dev/ttyUSB* /dev/ttyACM*
dmesg | grep -i "tty\|ch341\|cp210x\|ftdi\|cdc_acm"

# 需要的驱动:
# CP2102: CONFIG_USB_SERIAL_CP210X=y
# CH340:  CONFIG_USB_SERIAL_CH341=y
# FTDI:   CONFIG_USB_SERIAL_FTDI_SIO=y
# CDC:    CONFIG_USB_ACM=y
```

### 4.4 USB 摄像头 (UVC)
```bash
# 检查:
v4l2-ctl --list-devices
ls /dev/video*
dmesg | grep -i uvc

# 需要: CONFIG_USB_VIDEO_CLASS=y
```

---

## §5 USB 电源管理

### 5.1 Autosuspend
```bash
# USB autosuspend 可能导致设备断连:
# 查看当前设置:
cat /sys/bus/usb/devices/1-1/power/autosuspend  # 秒数, -1=禁用

# 禁用单个设备的 autosuspend:
echo -1 > /sys/bus/usb/devices/1-1/power/autosuspend
echo on > /sys/bus/usb/devices/1-1/power/control

# 全局禁用:
echo -1 > /sys/module/usbcore/parameters/autosuspend

# 或 bootargs: usbcore.autosuspend=-1

# 查看电源状态:
cat /sys/bus/usb/devices/1-1/power/runtime_status
# active / suspended
```

### 5.2 VBUS 供电
```bash
# VBUS 控制 (DTS):
# vbus-supply = <&vcc5v0_usb>;
# 或通过 GPIO 控制 VBUS 使能

# 过流保护:
dmesg | grep -i "over-current\|overcurrent"
# "USB port over-current" → VBUS 过流, 检查负载

# USB 供电能力:
# USB 2.0: 500mA (默认), 可协商更高
# USB 3.0: 900mA
# Type-C: 1.5A / 3A (标准), 5A (PD)
```

---

## §6 usbmon 抓包分析

### 6.1 使用 usbmon
```bash
# 加载模块:
modprobe usbmon

# 查看可用 bus:
ls /sys/kernel/debug/usb/usbmon/

# 抓包 (文本模式):
cat /sys/kernel/debug/usb/usbmon/1u    # 总线 1 的所有包
# 格式: <timestamp> <URB-type> <endpoint> <data...>
# URB 类型: S=Submit(提交), C=Callback(完成)

# 抓包 (pcap 格式, 用 Wireshark 分析):
tcpdump -i usbmon1 -w /tmp/usb.pcap
# 或使用 usbmon 的 binary 接口

# 过滤特定设备:
# 用 -f 参数 或 在 Wireshark 中过滤:
# usb.device_address == 2
```

### 6.2 分析要点
```
常见 USB 分析场景:
1. 枚举过程分析:
   - GET_DESCRIPTOR (Device/Config/String)
   - SET_ADDRESS
   - SET_CONFIGURATION
   - 如果某步失败 → 看 URB 的 status 字段

2. 数据传输分析:
   - Bulk/Interrupt/Isochronous Transfer
   - 关注 URB status: 0=成功, -EPIPE, -ETIMEDOUT 等

3. 性能分析:
   - 计算 throughput = 数据量 / 时间
   - 检查是否有大量 NAK (设备未就绪)
```

---

## §7 USB Type-C 与 PD

### 7.1 Type-C 基础
```
Type-C CC (Configuration Channel) 检测:
- CC pin 上的电阻确定角色:
  → Rp (上拉) → Source/Host
  → Rd (下拉) → Sink/Device
- 电流能力也由 Rp 值确定

Linux Type-C 框架:
- TCPM (Type-C Port Manager)
- TCPC (Type-C Port Controller) 驱动
- typec class: /sys/class/typec/

# 查看 Type-C 状态:
cat /sys/class/typec/port0/data_role      # host/device
cat /sys/class/typec/port0/power_role     # source/sink
cat /sys/class/typec/port0/orientation    # normal/reverse
```

### 7.2 Type-C DTS
```dts
/* Type-C with TCPM/TCPC */
&i2c4 {
    fusb302: fusb302@22 {
        compatible = "fcs,fusb302";
        reg = <0x22>;
        interrupt-parent = <&gpio1>;
        interrupts = <RK_PA2 IRQ_TYPE_LEVEL_LOW>;
        vbus-supply = <&vcc5v0_typec>;

        usb_con: connector {
            compatible = "usb-c-connector";
            label = "USB-C";
            data-role = "dual";
            power-role = "dual";
            try-power-role = "sink";

            ports {
                port@0 { /* USB2 */
                    reg = <0>;
                    usb_con_hs: endpoint { remote-endpoint = <&usb_hs>; };
                };
                port@1 { /* USB3 */
                    reg = <1>;
                    usb_con_ss: endpoint { remote-endpoint = <&usb_ss>; };
                };
            };
        };
    };
};
```

---

## §8 USB DTS 配置

### 8.1 通用 USB 控制器 DTS
```dts
/* USB 2.0 Host (EHCI) */
&ehci {
    status = "okay";
};
&ohci {
    status = "okay";
};

/* USB 3.0 Host (xHCI) */
&xhci {
    status = "okay";
};

/* DWC3 OTG */
&usbdrd3 {
    status = "okay";
};
&usbdrd_dwc3 {
    dr_mode = "otg";          /* host / peripheral / otg */
    status = "okay";
};

/* DWC2 OTG */
&usb_otg {
    dr_mode = "otg";
    status = "okay";
};

/* USB PHY */
&u2phy0 {
    status = "okay";
    u2phy0_host: host-port {
        status = "okay";
    };
    u2phy0_otg: otg-port {
        status = "okay";
        vbus-supply = <&vcc5v0_usb>;
    };
};
```

### 8.2 VBUS 与 GPIO 控制
```dts
/* VBUS 控制 regulator */
vcc5v0_usb: vcc5v0-usb-regulator {
    compatible = "regulator-fixed";
    regulator-name = "vcc5v0_usb";
    regulator-min-microvolt = <5000000>;
    regulator-max-microvolt = <5000000>;
    enable-active-high;
    gpio = <&gpio0 RK_PA5 GPIO_ACTIVE_HIGH>;
    pinctrl-names = "default";
    pinctrl-0 = <&usb_vbus_en>;
};
```

---

## §9 USB 性能优化

### 9.1 USB 传输速率参考
```
标准             理论峰值       实测典型值       备注
────────────────────────────────────────────────────
USB 1.1 Full    12 Mbps       ~1 MB/s          键盘鼠标等
USB 2.0 High    480 Mbps      ~35-40 MB/s      U 盘/摄像头
USB 3.0 Super   5 Gbps        ~350-400 MB/s    高速存储
USB 3.1 Gen2    10 Gbps       ~700-800 MB/s    NVMe 外置
```

### 9.2 存储传输优化
```bash
# 测试 USB 存储速度:
dd if=/dev/sda of=/dev/null bs=1M count=100    # 读速度
dd if=/dev/zero of=/dev/sda bs=1M count=100    # 写速度 (危险!)

# 或使用文件:
dd if=/dev/zero of=/mnt/usb/testfile bs=1M count=100
dd if=/mnt/usb/testfile of=/dev/null bs=1M

# 优化:
# 1. 确认设备在正确的速率运行:
cat /sys/bus/usb/devices/1-1/speed    # 480=USB2, 5000=USB3
# 如果 USB3 设备以 USB2 速率运行 → 检查线缆/接口

# 2. 调整块大小:
dd ... bs=4M                           # 增大块大小可能提升吞吐

# 3. 检查调度器:
cat /sys/block/sda/queue/scheduler
echo noop > /sys/block/sda/queue/scheduler  # 嵌入式推荐 noop/none
```

---

## §10 常见 USB 问题速查

| 问题 | 可能原因 | 排查方向 |
|------|---------|---------|
| 设备完全不识别 | VBUS 未供电/PHY 未初始化 | dmesg, DTS, PHY clock |
| 枚举报错 -62/-71 | 信号质量/线缆/供电 | 换线, 检查 VBUS 电压 |
| 设备频繁断连 | autosuspend/供电不足 | 禁用 autosuspend, 检查电流 |
| USB3 降速为 USB2 | USB3 线缆/PHY/信号完整性 | 换 USB3 线, 检查 PHY 配置 |
| Gadget 主机端不识别 | UDC 未绑定/configfs 配置 | 检查 UDC, configfs |
| OTG 不自动切换 | ID pin 配置/中断 | 检查 ID GPIO, dr_mode |
| 供电不足 (过流) | 负载过大/VBUS regulator | dmesg overcurrent, 电流 |
| HUB 下设备不工作 | HUB 供电/TT 问题 | 直连测试, 换有源 HUB |

---

## Reference Index

| 参考文件 | 内容概要 |
|---------|---------|
| [usb_enumeration.md](references/usb_enumeration.md) | USB 枚举完整流程, 描述符解析, 错误码大全, 常见芯片问题 |
| [usb_gadget_guide.md](references/usb_gadget_guide.md) | USB Gadget 开发完整指南, ConfigFS 详解, 复合设备, 常用 function 配置 |
| [usb_phy_debug.md](references/usb_phy_debug.md) | USB PHY 调试, 信号质量, 眼图分析, 常见 PHY 芯片配置, 时钟树 |

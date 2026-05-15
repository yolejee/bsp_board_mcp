# USB Gadget 开发完整指南

## 1. USB Gadget 框架

### 1.1 框架层次
```
应用层 (用户空间)
    ↓
ConfigFS / Legacy gadget API
    ↓
Composite Framework (USB 复合设备)
    ↓
USB Function 驱动 (ACM/ECM/Mass Storage/HID/UVC...)
    ↓
UDC (USB Device Controller) 驱动
    ↓
USB PHY → USB 连接器 → Host
```

### 1.2 UDC 驱动
```bash
# UDC (USB Device Controller) 是 SoC 的 USB 控制器在 Device 模式下的驱动
# 常见 UDC:
# - dwc2 → DWC2 OTG 控制器
# - dwc3 → DWC3 OTG 控制器
# - musb-hdrc → TI MUSB 控制器
# - ci_hdrc → NXP ChipIdea 控制器

# 查看可用 UDC:
ls /sys/class/udc/
# 例: fe800000.usb (DWC2) 或 fe900000.dwc3 (DWC3)

# UDC 对应的 DTS:
# dr_mode = "peripheral" 或 "otg"
```

## 2. ConfigFS 详细配置

### 2.1 USB ACM (虚拟串口)
```bash
cd /sys/kernel/config/usb_gadget
mkdir g1 && cd g1

# 设备描述符:
echo 0x1d6b > idVendor
echo 0x0104 > idProduct
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

# 字符串:
mkdir strings/0x409
echo "Serial Gadget" > strings/0x409/product
echo "0123456789" > strings/0x409/serialnumber
echo "Linux" > strings/0x409/manufacturer

# 配置:
mkdir configs/c.1
mkdir configs/c.1/strings/0x409
echo "ACM Config" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower

# Function:
mkdir functions/acm.usb0
ln -s functions/acm.usb0 configs/c.1/

# 激活:
echo $(ls /sys/class/udc/) > UDC

# 使用: 板端出现 /dev/ttyGS0, 主机端出现 /dev/ttyACM0
# 板端: echo "Hello" > /dev/ttyGS0
# 主机: cat /dev/ttyACM0
```

### 2.2 USB ECM (虚拟网卡)
```bash
mkdir functions/ecm.usb0
ln -s functions/ecm.usb0 configs/c.1/
echo $(ls /sys/class/udc/) > UDC

# 板端:
ifconfig usb0 192.168.7.2 netmask 255.255.255.0 up

# 主机端:
ifconfig usb0 192.168.7.1 netmask 255.255.255.0 up
ping 192.168.7.2
```

### 2.3 USB RNDIS (Windows 兼容网卡)
```bash
mkdir functions/rndis.usb0
# Windows 会自动识别为网络适配器
ln -s functions/rndis.usb0 configs/c.1/
echo $(ls /sys/class/udc/) > UDC
```

### 2.4 USB Mass Storage (U 盘模式)
```bash
mkdir functions/mass_storage.usb0

# 使用文件作为存储:
dd if=/dev/zero of=/tmp/disk.img bs=1M count=64
mkfs.vfat /tmp/disk.img
echo /tmp/disk.img > functions/mass_storage.usb0/lun.0/file
echo 0 > functions/mass_storage.usb0/lun.0/removable
echo 0 > functions/mass_storage.usb0/lun.0/cdrom

# 或使用真实块设备:
# echo /dev/mmcblk0p3 > functions/mass_storage.usb0/lun.0/file

ln -s functions/mass_storage.usb0 configs/c.1/
echo $(ls /sys/class/udc/) > UDC
```

### 2.5 USB HID (键盘/鼠标模拟)
```bash
mkdir functions/hid.usb0
echo 1 > functions/hid.usb0/protocol      # 1=键盘, 2=鼠标
echo 1 > functions/hid.usb0/subclass      # Boot Interface
echo 8 > functions/hid.usb0/report_length  # 报告长度

# 需要写入 HID Report Descriptor (二进制):
# 这是一个标准键盘描述符的简化示例
echo -ne '\x05\x01\x09\x06\xa1\x01...' > functions/hid.usb0/report_desc

ln -s functions/hid.usb0 configs/c.1/
echo $(ls /sys/class/udc/) > UDC

# 发送按键: echo -ne '\x00\x00\x04\x00\x00\x00\x00\x00' > /dev/hidg0
```

## 3. 复合设备 (多功能)

```bash
# 同时提供串口 + 网卡:
mkdir functions/acm.usb0
mkdir functions/ecm.usb0
ln -s functions/acm.usb0 configs/c.1/
ln -s functions/ecm.usb0 configs/c.1/
echo $(ls /sys/class/udc/) > UDC

# 主机端会看到一个复合设备, 同时有 ACM 和 ECM 接口
```

## 4. Legacy Gadget 模块

```bash
# 不使用 ConfigFS, 直接加载预配好的 gadget 模块:

# 串口:
modprobe g_serial

# 网卡:
modprobe g_ether

# U 盘:
modprobe g_mass_storage file=/tmp/disk.img

# 多功能:
modprobe g_multi file=/tmp/disk.img

# 注意: Legacy 方式和 ConfigFS 方式不能同时使用
```

## 5. Gadget 故障排查

```bash
# 1. UDC 未绑定:
cat /sys/kernel/config/usb_gadget/g1/UDC
# 应显示 UDC 名称, 如果为空则未绑定

# 2. 主机端看不到设备:
dmesg | grep -i gadget          # 板端
dmesg | grep -i usb             # 主机端
# 检查 USB 线是否是数据线 (非充电线)
# 检查 dr_mode 是否为 peripheral 或 otg

# 3. 功能无法使用:
# 检查相关内核模块是否编译:
# CONFIG_USB_CONFIGFS=y
# CONFIG_USB_CONFIGFS_ACM=y
# CONFIG_USB_CONFIGFS_ECM=y
# CONFIG_USB_CONFIGFS_MASS_STORAGE=y
# CONFIG_USB_CONFIGFS_F_HID=y
```

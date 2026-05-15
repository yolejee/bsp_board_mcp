# USB 枚举完整流程

## 1. 枚举步骤详解

### 1.1 标准枚举流程
```
Step 1: 设备连接检测
  → Host 检测 D+/D- 上的电压变化 (设备上拉电阻)
  → 确定设备速率: Low-Speed (D-上拉), Full/High-Speed (D+上拉)

Step 2: 总线复位 (Bus Reset)
  → Host 驱动 D+/D- 为 SE0 (两线都低) 至少 10ms
  → 设备进入默认状态, 地址为 0

Step 3: 速率检测 (High-Speed Chirp)
  → Full-Speed 设备复位后就确定了
  → High-Speed: 复位期间进行 Chirp 握手协商

Step 4: 获取设备描述符 (部分)
  GET_DESCRIPTOR (Device, 64 bytes max)
  → Host 获取设备的 bMaxPacketSize0 (最大控制传输包大小)

Step 5: 再次总线复位
  → 某些 Host 会再复位一次

Step 6: 分配设备地址
  SET_ADDRESS (1-127)
  → 设备从此使用新地址响应

Step 7: 获取完整设备描述符
  GET_DESCRIPTOR (Device, 18 bytes)
  → 获取 VID, PID, bNumConfigurations 等

Step 8: 获取配置描述符
  GET_DESCRIPTOR (Configuration)
  → 包含接口描述符, 端点描述符

Step 9: 获取字符串描述符 (可选)
  GET_DESCRIPTOR (String)
  → 制造商, 产品名, 序列号

Step 10: 设置配置
  SET_CONFIGURATION (1)
  → 设备进入工作状态
  → 内核加载对应驱动
```

### 1.2 dmesg 中的枚举过程
```
# 正常枚举日志 (对应上述步骤):
[  12.345] usb 1-1: new high-speed USB device number 2 using xhci-hcd  ← Step 1-3
[  12.567] usb 1-1: New USB device found, idVendor=0781, idProduct=5567 ← Step 7
[  12.567] usb 1-1: New USB device strings: Mfr=1, Product=2, SerialNumber=3
[  12.567] usb 1-1: Product: Cruzer Blade                              ← Step 9
[  12.567] usb 1-1: Manufacturer: SanDisk
[  12.567] usb 1-1: SerialNumber: 4C530001234
[  12.678] usb-storage 1-1:1.0: USB Mass Storage device detected       ← 驱动绑定
[  12.789] scsi host0: usb-storage 1-1:1.0
[  13.800] scsi 0:0:0:0: Direct-Access     SanDisk  Cruzer Blade ...
[  13.801] sd 0:0:0:0: [sda] 15633408 512-byte logical blocks
[  13.802] sd 0:0:0:0: [sda] Attached SCSI removable disk
```

## 2. USB 描述符解析

### 2.1 设备描述符
```
bLength:            18       (固定)
bDescriptorType:    1        (DEVICE)
bcdUSB:             0x0200   (USB 2.0)
bDeviceClass:       0x00     (接口级定义类)
bDeviceSubClass:    0x00
bDeviceProtocol:    0x00
bMaxPacketSize0:    64       (控制端点最大包大小)
idVendor:           0x0781   (SanDisk)
idProduct:          0x5567   (Cruzer Blade)
bcdDevice:          0x0100   (设备版本)
iManufacturer:      1        (字符串索引)
iProduct:           2
iSerialNumber:      3
bNumConfigurations: 1
```

### 2.2 常用 lsusb 分析
```bash
# 查看详细描述符:
lsusb -v -d 0781:5567 2>/dev/null

# 重点关注:
# 1. bcdUSB → 设备支持的 USB 版本
# 2. bDeviceClass → 设备类别
# 3. Endpoint 描述符中的:
#    - bmAttributes → 传输类型 (Bulk/Interrupt/Isochronous)
#    - wMaxPacketSize → 最大包大小
#    - bInterval → 轮询间隔

# 常见设备类 (bInterfaceClass):
# 0x01 → Audio
# 0x02 → CDC (通信)
# 0x03 → HID (键盘/鼠标)
# 0x06 → Still Image (PTP)
# 0x08 → Mass Storage
# 0x09 → Hub
# 0x0E → Video (UVC)
# 0xFF → Vendor-Specific
```

## 3. 枚举错误码大全

```
错误码    常量           含义                    常见原因
─────────────────────────────────────────────────────────────
-2       -ENOENT       No such file/dir        设备已移除
-6       -ENXIO        No such device/addr     地址不存在
-11      -EAGAIN       Try again               资源临时不可用
-12      -ENOMEM       Out of memory           内存不足
-19      -ENODEV       No such device          设备不存在/已拔出
-22      -EINVAL       Invalid argument        参数无效
-32      -EPIPE        Broken pipe (STALL)     端点 STALL (请求被拒)
-62      -ETIME        Timer expired           设备无响应
-71      -EPROTO       Protocol error          信号/协议错误
-75      -EOVERFLOW    Value too large         数据溢出
-84      -EILSEQ       Illegal sequence        CRC/比特填充错误
-104     -ECONNRESET   Connection reset        连接被重置
-108     -ESHUTDOWN    No EHCI shutdown        控制器关闭
-110     -ETIMEDOUT    Connection timed out    超时
-121     -EREMOTEIO    Remote I/O error        传输被远端终止

最常见的枚举失败组合:
-62 (ETIME):  设备完全没响应 → VBUS/PHY/线缆
-71 (EPROTO): 从设备收到了信号但解析失败 → 信号质量/兼容性
-32 (EPIPE):  设备拒绝了请求 → 协议/描述符问题
```

## 4. 常见 USB 芯片问题

### 4.1 USB Hub 芯片
```
GL850G / GL852G (Genesys Logic):
- 4 端口 USB 2.0 Hub
- 常见问题: 供电不足时下挂设备枚举失败

FE1.1s (Terminus):
- 4 端口 USB 2.0 Hub
- 需要外部 12MHz 晶振

VL817 (VIA Labs):
- USB 3.0 Hub
- 需要正确的固件

排查 Hub 问题:
1. 直连 Host 端口测试 (绕过 Hub)
2. 换有源 Hub (外供电)
3. lsusb -t 查看 Hub 拓扑
```

### 4.2 USB-Serial 芯片
```
CH340/CH341:
- 低成本 USB 转串口
- Linux 驱动: ch341.ko
- 某些克隆芯片可能不兼容

CP2102/CP2104 (Silicon Labs):
- Linux 驱动: cp210x.ko
- 支持更高波特率

FT232R/FT2232H (FTDI):
- Linux 驱动: ftdi_sio.ko
- 专业级, 支持 MPSSE (JTAG/SPI)

PL2303 (Prolific):
- Linux 驱动: pl2303.ko
- 注意区分正品和克隆芯片
```

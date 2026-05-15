# MIPI CSI-2 错误诊断与 V4L2 调试

## 1. MIPI CSI-2 协议概要

### 1.1 信号结构

```
MIPI CSI-2 信号:
├── Clock Lane (1对差分线)
│   └── 提供同步时钟
├── Data Lane 0 (1对差分线)
│   └── 必须的数据通道
├── Data Lane 1-3 (可选)
│   └── 额外带宽
└── 传输模式:
    ├── LP (Low Power): 低速控制信令
    └── HS (High Speed): 高速数据传输
```

### 1.2 一帧数据传输时序

```
LP → HS → SOT → [Packet Header] → [Payload] → [CRC] → EOT → LP
         ↑                                               ↑
     Start of        Frame Data                      End of
    Transmission                                   Transmission
```

### 1.3 MIPI 4 要素

在 Sensor 与 ISP 之间进行 MIPI 通讯，必须正确设置：

| 要素 | 说明 | 确认方式 |
|-----|------|---------|
| 分辨率 | Sensor 输出宽×高 | Sensor datasheet / 寄存器配置 |
| 格式 | RAW8/10/12, YUV422 | mbus-code |
| link_freq | MIPI CLK 实际频率 | 公式计算或原厂确认 |
| lane 数 | 使用的 data lane 数量 | DTS data-lanes (sensor + dphy 两端) |

## 2. MIPI 错误详解

### 2.1 RK3288/RK3399/RK3368 ERR0 寄存器

| Bit | 简称 | 描述 | 严重度 |
|-----|------|------|-------|
| 25 | ADD_DATA_OVFLW | Additional data FIFO 溢出 | 中 |
| 24 | FRAME_END | 正常收到一帧 (**非错误**) | — |
| 23 | ERR_CS | Checksum 校验错误 | 高 |
| 22 | ERR_ECC1 | 1-bit ECC 错误 (可纠正) | 低 |
| 21 | ERR_ECC2 | 2-bit ECC 错误 (不可纠正) | 高 |
| 20 | ERR_PROTOCOL | 当前包内检测到新包起始 | 高 |
| 19:16 | ERR_CONTROL | PPI 接口控制错误, per lane | 高 |
| 15:12 | ERR_EOT_SYNC | EOT 同步错误, per lane | 中 |
| 11:8 | ERR_SOT_SYNC | SOT 同步错误, per lane | 高 |
| 7:4 | ERR_SOT | SOT 错误, per lane | 高 |
| 3:0 | SYNC_FIFO_OVFLW | 同步 FIFO 溢出, per lane | 高 |

### 2.2 RK3326/PX30/RK1808 ERR1 寄存器

| Bit | 简称 | 描述 |
|-----|------|------|
| 28 | ERR_ECC | ECC 错误 |
| 27:24 | ERR_CRC | CRC 错误 |
| 23:20 | ERR_FRAME_DATA | 帧含CRC错误 |
| 19:16 | ERR_F_SEQ | Frame Number 不连续 |
| 15:12 | ERR_F_BNDRY | Frame Start/End 不匹配 |
| 11:8 | ERR_SOT_SYNC | PHY SOT 同步错误 |
| 7:4 | ERR_EOT_SYNC | PHY EOT 同步错误 |

### 2.3 ERR2 寄存器

| Bit | 简称 |
|-----|------|
| 7:4 | ERR_SOTHS | PHY SOTHS 错误 |
| 3:0 | ERR_ESC | PHY ESC 错误 |

## 3. 错误诊断决策树

```
MIPI 报错
├── SOT / SOT_SYNC 错误
│   ├── 确认 link_freq 是否正确 (影响 Ths-settle 配置)
│   ├── 确认 Sensor 是否在其他平台验证过 MIPI
│   ├── 多 lane → 尝试减少到 1 lane
│   └── 参考 MIPI D-PHY Specification: HS Data Transmission Burst
│
├── ECC / CRC / CheckSum 错误
│   ├── 排查硬件信号完整性
│   │   ├── PCB 走线长度匹配
│   │   ├── 阻抗匹配 (100Ω差分)
│   │   └── 干扰源排查
│   ├── 多 lane → 尝试 1 lane (排除 lane 间同步问题)
│   └── 检查 Sensor 寄存器初始化是否完整
│
├── ERR_PROTOCOL / ERR_F_BNDRY
│   ├── SOT/EOT 未正确配对
│   └── 实测波形检查
│
├── SYNC_FIFO_OVFLW
│   ├── DDR 带宽不足
│   │   └── echo performance > /sys/class/devfreq/dmc/governor
│   └── 数据率超过接收能力
│
├── 仅开机初始报错 (后续正常)
│   ├── 原因: Sensor 上电过程中 MIPI 信号不符合协议
│   └── 修复:
│       1. 完整寄存器初始化放到 s_power()
│       2. s_power() 末尾 stop_stream()
│       3. s_stream() 仅控制输出开关
│
└── 持续大量报错 / 死机
    ├── 可能是电平中断导致中断风暴
    ├── 尝试上述 s_power/s_stream 分离方案
    └── 硬件排查 MIPI 信号质量
```

## 4. PIC_SIZE_ERROR 诊断

```
ISP PIC_SIZE_ERROR (未收到预期行列数)
├── 1. 先解决 MIPI 报错 (如有)
├── 2. DDR 频率
│   └── echo performance > /sys/class/devfreq/dmc/governor
├── 3. 链路分辨率检查
│   └── media-ctl -p -d /dev/media0
│       Sensor ≥ MIPI_DPHY ≥ ISP_input ≥ ISP_output
├── 4. Sensor 配置大小可能超过实际输出
│   └── 尝试缩小 mode 的 width/height (不改寄存器)
└── 5. 多 ISP 虚拟设备时注意 max-input 配置
```

## 5. V4L2 Media Framework 调试

### 5.1 查看完整拓扑

```bash
# 列出所有 media 设备
ls /dev/media*

# 打印拓扑结构
media-ctl -p -d /dev/media0

# 输出解读示例:
# - entity 9: m00_b_ov5695 2-0036 (1 pad, 1 link)
#             type V4L2 subdev subtype Sensor flags 0
#             device node name /dev/v4l-subdev2
#         pad0: Source
#                 [fmt:SBGGR10_1X10/2592x1944@10000/300000 field:none]
#                 -> "rockchip-mipi-dphy-rx":0 [ENABLED,DYNAMIC]
#
# 解读:
#   m00 = module-index 0
#   _b_ = back (facing)
#   ov5695 = sensor 名称
#   2-0036 = i2c bus 2, addr 0x36
#   SBGGR10_1X10 = 10bit Bayer BGGR
#   2592x1944 = 分辨率
#   @10000/300000 = 时间间隔 (10000/300000 秒 = 30fps)
#   ENABLED = 当前活跃链路
#   DYNAMIC = 可动态切换
```

### 5.2 Entity 名称编码规则

```
m{module-index}_{facing首字母}_{sensor_name} {i2c_bus}-{i2c_addr}

示例:
  m00_b_ov5695 2-0036
  │   │  │       │  └─ I2C address 0x36
  │   │  │       └──── I2C bus 2
  │   │  └──────────── sensor name
  │   └─────────────── b=back, f=front
  └─────────────────── module index 0
```

### 5.3 切换 Sensor (多摄分时复用)

```bash
# 停止当前 pipeline (必须先停止)
# 禁用 entity 9
media-ctl -d /dev/media0 \
    -l '"m00_b_ov5695 2-0036":0->"rockchip-mipi-dphy-rx":0[0]'

# 使能 entity 10
media-ctl -d /dev/media0 \
    -l '"m01_f_ov2685 2-003c":0->"rockchip-mipi-dphy-rx":0[1]'

# 命令格式: media-ctl -l '"entity":pad->"entity":pad[status]'
# status: 0 = inactive, 1 = active
# entity name 用双引号 (含空格)
# 整个 link 用单引号 (含特殊字符 > [ ])
```

### 5.4 修改分辨率

```bash
# 修改 sensor 输出分辨率
media-ctl -d /dev/media0 \
    --set-v4l2 '"m00_b_ov5695 2-0036":0[fmt:SBGGR10_1X10/1920x1080]'

# 注意: 修改 sensor 后，后级 ISP subdev 也要相应调整
# ISP input >= ISP output, 后级不能大于前级
```

### 5.5 查找 Video 设备对应的 Entity

```bash
# 方法 1: 通过 media-ctl
media-ctl -p -d /dev/media0 | grep -A3 "entity.*mainpath\|entity.*selfpath"

# 方法 2: 通过 sysfs
for v in /sys/class/video4linux/video*/; do
    echo "$(basename $v): $(cat ${v}name)"
done

# 方法 3: grep
grep "" /sys/class/video4linux/video*/name
```

## 6. v4l2-ctl 详细用法

### 6.1 列出设备信息

```bash
# 设备能力
v4l2-ctl -d /dev/video0 --all

# 支持的格式
v4l2-ctl -d /dev/video0 --list-formats-ext

# 列出 controls
v4l2-ctl -d /dev/v4l-subdev2 --list-ctrls
```

### 6.2 抓图命令集

```bash
# NV12 YUV 抓图
v4l2-ctl -d /dev/video0 \
    --set-fmt-video=width=1920,height=1080,pixelformat=NV12 \
    --stream-mmap=4 --stream-to=nv12.yuv --stream-count=10

# 10-bit RAW Bayer 抓图 (仅 MP 支持)
v4l2-ctl -d /dev/video0 \
    --set-fmt-video=width=2592,height=1944,pixelformat=BG10 \
    --stream-mmap=4 --stream-to=raw10.bin --stream-count=1

# 连续抓帧 (测帧率)
v4l2-ctl -d /dev/video0 \
    --set-fmt-video=width=640,height=480,pixelformat=NV12 \
    --stream-mmap=4 --stream-count=100 --stream-skip=10

# FourCC 对照表
# NV12 = YUV420sp     NV16 = YUV422sp
# NV21 = YVU420sp     YUYV = YUV422 packed
# BG10 = Bayer BGGR 10bit   BA10 = Bayer RGGB 10bit
# GREY = 8bit灰度     XR24 = XRGB8888
```

### 6.3 Control 操作

```bash
# 查看当前值
v4l2-ctl -d /dev/v4l-subdev2 --get-ctrl exposure
v4l2-ctl -d /dev/v4l-subdev2 --get-ctrl analogue_gain

# 设置曝光 (手动曝光)
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl exposure=2000

# 设置增益
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl analogue_gain=200

# 设置 VBlank (改帧率)
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl vblank=1000

# 使能 test pattern (检查 ISP 链路)
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl test_pattern=1
```

## 7. 常用调试命令汇总

### 7.1 驱动 Debug 开关

```bash
# RKISP 驱动 (bit mask, 0xff 全开)
echo 0xff > /sys/module/video_rkisp/parameters/debug

# RKCIF 驱动
echo 0xff > /sys/module/video_rkcif/parameters/debug

# MIPI DPHY
echo 1 > /sys/module/phy_rockchip_csi2_dphy/parameters/debug

# Sensor 驱动 (dynamic debug)
echo 'file drivers/media/i2c/ov5695.c +p' > /sys/kernel/debug/dynamic_debug/control

# V4L2 核心
echo 0x3 > /sys/module/videobuf2_core/parameters/debug
```

### 7.2 中断和帧率统计

```bash
# 查看 ISP 中断计数
cat /proc/interrupts | grep -i isp

# 查看 VICAP/CIF 中断
cat /proc/interrupts | grep -i cif

# 实时帧率 (rkisp)
cat /sys/devices/platform/*/rkisp*/stream_fps

# dmesg 中的帧率信息
dmesg | grep -i "fps\|frame"
```

### 7.3 内存与 Buffer 调试

```bash
# DMA buffer 使用情况
cat /proc/dma_heap/dma_heap_info

# IOMMU 映射
cat /sys/kernel/debug/iommu/*/mappings

# CMA 使用
cat /proc/meminfo | grep Cma
```

### 7.4 GStreamer 调试

```bash
# 基本预览
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1 ! \
    waylandsink

# 编码录制
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=300 ! \
    video/x-raw,format=NV12,width=1920,height=1080 ! \
    mpph264enc ! h264parse ! mp4mux ! filesink location=out.mp4

# 截图
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=1 ! \
    video/x-raw,format=NV12,width=1920,height=1080 ! \
    jpegenc ! filesink location=photo.jpg

# USB UVC 模拟
# SDK 中 external/uvc_app/ 提供了将板卡模拟成 UVC Camera 的功能
# 适用于无屏板卡远程调试
```

## 8. ISP 拓扑结构图

### 8.1 RK3568 典型拓扑

```
Sensor (m00_b_ov5695)
    └─ pad0:Source [SBGGR10_1X10/2592x1944]
         → "rockchip-csi2-dphy0":0 [ENABLED]
              └─ pad1:Source
                   → "rkisp-isp-subdev":0 [ENABLED]
                        ├─ pad1:Source [Crop 0,0/2592x1944]
                        │    → "rkisp_mainpath" (MP) /dev/video0
                        └─ pad2:Source [Crop 0,0/1920x1080]
                             → "rkisp_selfpath" (SP) /dev/video1
```

### 8.2 RK3588 典型拓扑

```
Sensor → csi2_dphy → mipiX_csi2 → rkcif_mipi_lvdsX → sditf → rkispX_virY
                                       ↓ (可直出)
                                  rkcif_mipi_lvdsX 的 video 节点
```

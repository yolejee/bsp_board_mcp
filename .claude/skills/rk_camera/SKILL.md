---
name: rk_camera
description: "Rockchip 瑞芯微平台 Camera 摄像头子系统技能。覆盖 RK3588/RK3568/RK3566/RV1126/RV1106 等全系列芯片的 Camera Sensor 驱动开发、MIPI CSI-2 接口调试、DVP/LVDS 接口、VICAP/CIF 驱动、V4L2/Media Controller 框架、camera DTS 配置、多摄方案、HDR 模式。触发关键词：摄像头、camera、sensor、MIPI CSI、DPHY、DVP、CIF、VICAP、RKISP、V4L2、v4l2-ctl、media-ctl、/dev/video、link_freq、pixel_rate、data-lanes、sensor driver、上电时序、chip id、stream on、不出图、花屏、绿屏、帧率低、MIPI 报错、PIC_SIZE_ERROR、OV5695、IMX415、多摄、csi2_dphy、split mode、camera-module-index。当用户提到 Rockchip 平台的摄像头采集、sensor 驱动、MIPI CSI 接口问题时触发。ISP 图像调优请使用 rk_isp 技能。"
---

# Rockchip Camera 子系统技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| Sensor 识别不到/I2C 失败 | §6.1 |
| 不出图/黑屏 | §6.2 |
| MIPI 报错 (SOT/ECC/CRC) | §6.3 |
| PIC_SIZE_ERROR | §6.4 |
| 颜色异常/偏暗偏亮 | §6.5 |
| Sensor 驱动移植 | §2 |
| Camera DTS 配置 | §3 |
| 多摄方案 | §4 |
| media-ctl/v4l2-ctl 使用 | §5 |
| HDR/8K 配置 | §4.2-4.3 |

---

## 1. Camera 子系统架构

### 1.1 硬件通路

```
                        ┌─ RKISP ─→ MP (MainPath, 高分辨率/RAW)
Sensor ─→ MIPI DPHY ──→│           SP (SelfPath, ≤1080p/YUV/RGB)
          (或 DVP)      └─ RKCIF ──→ Video (直通DDR, 无ISP处理)
                             ↓
                        VICAP sditf ──→ RKISP (经ISP处理)
```

### 1.2 各平台 VI 特性概览

| 平台 | ISP | VICAP | MIPI DPHY | 最大 Bayer 分辨率 | HDR |
|------|-----|-------|-----------|-----------------|-----|
| RK3588 | ISP30×2 | 1 | 4×2L 或 2×4L + 2×DCPHY | 单ISP 4672×3504, 双ISP 8K | 3帧 |
| RK3568 | ISP21×1 | 1 | 2×2L 或 1×4L | 4096×2304 | 2帧 |
| RK3566 | ISP21 Lite×1 | 1 | 2×2L 或 1×4L | 4096×2304 | 无 |
| RV1126 | ISP20(+ISPP)×1 | Full+Lite | 2×4L DPHY + 2×4L LVDS | 4416×3312 | 3帧 |
| RV1106 | ISP32-Lite×1 | 1 | 1×4L 或 2×2L | 2688×1520 | 2帧 |
| RK3399 | ISP1×2 | 无 | 1×4L | 4416×3312 | 无 |

### 1.3 驱动源码目录

```
drivers/media/
├── platform/rockchip/
│   ├── cif/           # RKCIF (VICAP) 驱动
│   ├── isp/           # RKISP 驱动
│   │   ├── dev.c      # probe, 异步注册, pipeline
│   │   ├── capture.c  # MP/SP 输出, vb2, 帧中断
│   │   ├── isp_params.c  # 3A 参数下发
│   │   └── isp_stats.c   # 3A 统计上报
│   └── ispp/          # RKISPP 驱动 (RV1126)
├── i2c/               # Sensor 驱动 (ov5695.c, imx415.c ...)
└── phy/rockchip/      # MIPI DPHY 驱动
    ├── phy-rockchip-mipi-rx.c
    ├── phy-rockchip-csi2-dphy-hw.c
    └── phy-rockchip-csi2-dphy.c
```

---

## 2. Sensor 驱动开发移植

### 2.1 驱动结构概述

Sensor 驱动位于 `drivers/media/i2c/`，作为 V4L2 Sub Device 异步注册，通过 `remote-endpoint` 与 ISP/CIF 建立连接。

**驱动开发 5 步骤：**

1. **上电时序** — 按 datasheet 配置 vdd/reset/powerdown/clk
2. **寄存器列表** — 配置 mode (分辨率/帧率/格式)
3. **v4l2_subdev_ops** — 实现 set_fmt/get_fmt/s_stream/s_power 等回调
4. **V4L2 controls** — exposure/gain/blanking/test pattern
5. **Probe 函数** — media_entity_init + v4l2_async_register_subdev

### 2.2 v4l2_subdev_ops 必须实现的回调

| 回调函数 | 说明 |
|---------|------|
| `.open()` | subdev 节点打开，设置 control 时必须 |
| `.s_power()` | 上电/下电，配置 regulator + gpio + clk |
| `.s_stream()` | Stream on/off，配置寄存器使 sensor 输出图像 |
| `.enum_mbus_code()` | 枚举支持的 mbus_code |
| `.enum_frame_size()` | 枚举支持的分辨率 |
| `.get_fmt()` / `.set_fmt()` | 获取/设置 format 和 size |

### 2.3 上电时序示例 (OV5695)

```c
static int __ov5695_power_on(struct ov5695 *ov5695)
{
    /* 1. 提供 xvclk (24MHz) */
    clk_set_rate(ov5695->xvclk, OV5695_XVCLK_FREQ);
    clk_prepare_enable(ov5695->xvclk);
    /* 2. Reset pin 使能 */
    gpiod_set_value_cansleep(ov5695->reset_gpio, 1);
    /* 3. 各路 vdd 上电 (avdd/dovdd/dvdd) */
    regulator_bulk_enable(OV5695_NUM_SUPPLIES, ov5695->supplies);
    /* 4. 释放 reset/powerdown */
    gpiod_set_value_cansleep(ov5695->reset_gpio, 0);
    gpiod_set_value_cansleep(ov5695->pwdn_gpio, 0);
    /* 5. 等待 8192 clk cycles */
    usleep_range(delay_us, delay_us * 2);
    return 0;
}
```

### 2.4 link_freq 与 pixel_rate 计算

```
link_freq(Hz) ≥ width × height × fps × bits_per_pixel / lanes / 2
pixel_rate = link_freq × 2 × lanes / bits_per_pixel
```

> **注意**：link_freq 是 MIPI clk 实际频率，不是 24M mclk。优先从 Sensor 原厂获取。

### 2.5 mode 结构与寄存器列表

```c
struct ov5695_mode {
    u32 width;          /* 输出宽度 */
    u32 height;         /* 输出高度 */
    struct v4l2_fract max_fps;  /* 最大帧率 */
    u32 hts_def;        /* H Total Size 默认值 */
    u32 vts_def;        /* V Total Size 默认值 */
    u32 exp_def;        /* Exposure 默认值 */
    const struct regval *reg_list;  /* 寄存器初始化列表 */
};
```

> hts_def/vts_def/exp_def 从 Sensor datasheet 对应寄存器地址的初始化值中查找。

---

## 3. Camera DTS 配置

### 3.1 MIPI Sensor DTS 模板

```dts
/* ===== Sensor 节点 (I2C 总线下) ===== */
&i2c4 {
    status = "okay";

    ov5695: ov5695@36 {
        compatible = "ovti,ov5695";
        reg = <0x36>;                              /* I2C 7-bit 地址 */

        /* 时钟 */
        clocks = <&cru CLK_MIPI_CAMARAOUT_M4>;    /* RK3588 mclk 源 */
        clock-names = "xvclk";
        pinctrl-names = "default";
        pinctrl-0 = <&mipim0_camera4_clk>;         /* mclk pinmux */

        /* 电源 */
        avdd-supply = <&vcc_avdd>;                 /* 模拟电源 2.8V */
        dovdd-supply = <&vcc_dovdd>;               /* IO电源 1.8V */
        dvdd-supply = <&vdd_dvdd>;                 /* 核心电源 1.2/1.5V */

        /* GPIO */
        reset-gpios = <&gpio2 RK_PA4 GPIO_ACTIVE_LOW>;
        pwdn-gpios = <&gpio2 RK_PA5 GPIO_ACTIVE_HIGH>;

        /* Rockchip 模组信息 (3A IQ 匹配用) */
        rockchip,camera-module-index = <0>;        /* 模组编号,不可重复 */
        rockchip,camera-module-facing = "back";    /* back 或 front */
        rockchip,camera-module-name = "CMK-OT1607-FV1";
        rockchip,camera-module-lens-name = "M12-4IR-4MP-F16";

        port {
            sensor_out: endpoint {
                remote-endpoint = <&dphy_in>;
                data-lanes = <1 2 3 4>;            /* MIPI lane 数 */
            };
        };
    };
};
```

### 3.2 各平台 MIPI DPHY 链接方式

#### RK356X (单 DPHY, Full/Split Mode)

```
Full Mode:  sensor → csi2_dphy0 (4L) → rkisp_vir0
Split Mode: sensor1 → csi2_dphy1 (2L, lane0/1) ─→ rkisp_vir0
            sensor2 → csi2_dphy2 (2L, lane2/3) ─→ rkisp_vir1
```

- `csi2_dphy0` 与 `csi2_dphy1/csi2_dphy2` **互斥**
- 需要使能 `csi2_dphy_hw` 物理节点

**DTS 要点 (RK3568 Full Mode)**:
```dts
&csi2_dphy_hw { status = "okay"; };
&csi2_dphy0 {
    status = "okay";
    ports {
        port@0 { dphy_in: endpoint { remote-endpoint = <&sensor_out>; data-lanes = <1 2 3 4>; }; };
        port@1 { dphy_out: endpoint { remote-endpoint = <&isp0_in>; }; };
    };
};
&rkisp { status = "okay"; };
&rkisp_vir0 {
    status = "okay";
    port { isp0_in: endpoint { remote-endpoint = <&dphy_out>; }; };
};
```

#### RK3588 (2×DCPHY + 2×DPHY_HW, 经 VICAP 中转)

```
sensor → csi2_dphy3 → mipi4_csi2 → rkcif_mipi_lvds4 → sditf → rkisp0_vir0
         (逻辑节点)    (CSI Host)    (VICAP逻辑节点)    (桥接)    (ISP虚拟设备)
```

**RK3588 DPHY 编号规则：**

| 物理 HW | Full Mode | Split Mode (2L+2L) |
|---------|-----------|-------------------|
| dphy0_hw | csi2_dphy0 (4L) | csi2_dphy1 (L0/1) + csi2_dphy2 (L2/3) |
| dphy1_hw | csi2_dphy3 (4L) | csi2_dphy4 (L0/1) + csi2_dphy5 (L2/3) |
| dcphy0 | csi2_dcphy0 (DPHY/CPHY) | — |
| dcphy1 | csi2_dcphy1 (DPHY/CPHY) | — |

> Full Mode 时需用 Split Mode 链路配置，但将节点名改为 Full Mode 名称（如 csi2_dphy1→csi2_dphy0），驱动通过 PHY 序号区分模式。

**RK3588 DTS 模板 (imx464 → dphy1_hw full mode)**:
```dts
&csi2_dphy1_hw { status = "okay"; };
&csi2_dphy3 {                              /* dphy1_hw full mode */
    status = "okay";
    ports {
        port@0 { mipi_in: endpoint { remote-endpoint = <&imx464_out>; data-lanes = <1 2 3 4>; }; };
        port@1 { dphy3_out: endpoint { remote-endpoint = <&mipi4_csi2_input>; }; };
    };
};
&mipi4_csi2 {
    status = "okay";
    ports {
        port@0 { mipi4_csi2_input: endpoint { remote-endpoint = <&dphy3_out>; }; };
        port@1 { mipi4_csi2_output: endpoint { remote-endpoint = <&cif_mipi_in4>; }; };
    };
};
&rkcif { status = "okay"; };
&rkcif_mmu { status = "okay"; };
&rkcif_mipi_lvds4 {
    status = "okay";
    port { cif_mipi_in4: endpoint { remote-endpoint = <&mipi4_csi2_output>; }; };
};
&rkcif_mipi_lvds4_sditf {
    status = "okay";
    port { mipi4_lvds_sditf: endpoint { remote-endpoint = <&isp0_vir0>; }; };
};
&rkisp0 { status = "okay"; };
&isp0_mmu { status = "okay"; };
&rkisp0_vir0 {
    status = "okay";
    port { isp0_vir0: endpoint@0 { reg = <0>; remote-endpoint = <&mipi4_lvds_sditf>; }; };
};
```

### 3.3 DVP Sensor DTS 要点

```
链接关系: sensor → rkcif_dvp → rkcif_dvp_sditf → rkisp
```

- **BT601**: 必须配置 `hsync-active`/`vsync-active`，否则识别为 BT656
- **BT656/BT1120**: 不配置 hsync/vsync，自动识别
- Sensor 驱动 `g_mbus_config()` 必须正确返回极性标志
- 需要正确配置 pinctrl iomux

### 3.4 电源配置建议

- 多摄时 **dvdd 建议独立供电**，避免瞬态电流不足导致图像异常
- avdd/dovdd 可共用
- 使用 GPIO 控制的 LDO 可配置为 `regulator-fixed` 节点

---

## 4. 多摄方案与特殊模式

### 4.1 多 Sensor 分时复用

单个 ISP 可分时复用多路 Sensor，通过 `media-ctl` 切换：

```bash
# 禁用当前 sensor
media-ctl -d /dev/media0 -l '"m00_b_ov5695 2-0036":0->"rockchip-mipi-dphy-rx":0[0]'
# 使能目标 sensor
media-ctl -d /dev/media0 -l '"m01_b_gc8034 2-0037":0->"rockchip-mipi-dphy-rx":0[1]'
```

> **注意**：切换 Sensor 必须在 pipeline 停止时操作。

**RK3588 ISP 复用限制：**

| 复用路数 | 最大分辨率 |
|---------|-----------|
| 2 路 | 3840×2160 |
| 3-4 路 | 2560×1536 |

### 4.2 HDR 模式

ISP2x/ISP30 支持 2帧/3帧 HDR，硬件通过多路 DMATX 采集→DDR→DMARX 读回 ISP 合成：

```
Sensor HDR Output → CSI → rawwr0 (短帧) ──→ DDR
                        → rawwr1 (中帧) ──→ DDR  → rawrd → ISP 合成
                        → rawwr2 (长帧) ──→ DDR
```

Sensor 驱动需正确配置 `rkmodule_hdr_cfg` 和多 pad 格式输出。

### 4.3 RK3588 双 ISP 合成 8K

- 分辨率 >16M（4672×3504）时需启用双 ISP
- 关闭 `rkisp0`/`rkisp1`，使能 `rkisp_unite` 及对应 IOMMU
- 仅支持单摄

```dts
&rkisp0 { status = "disabled"; };
&rkisp1 { status = "disabled"; };
&rkisp_unite { status = "okay"; };
&rkisp_unite_mmu { status = "okay"; };
&rkisp0_vir0 {
    rockchip,hw = <&rkisp_unite>;
    /* ... endpoint 配置 ... */
};
```

---

## 5. 调试工具与常用命令

### 5.1 media-ctl (拓扑查看与配置)

```bash
# 查看拓扑结构 (确认 sensor 是否注册成功)
media-ctl -p -d /dev/media0

# 查看 sensor entity 信息 (名称格式: m{module-index}_{facing首字母}_{sensor} {bus}-{addr})
# 示例输出:
# - entity 9: m00_b_ov5695 2-0036 (1 pad, 1 link)
#             type V4L2 subdev subtype Sensor
#             device node name /dev/v4l-subdev2
#         pad0: Source [fmt:SBGGR10_1X10/2592x1944]
#             -> "rockchip-mipi-dphy-rx":0 [ENABLED]

# 修改 sensor 输出分辨率
media-ctl -d /dev/media0 --set-v4l2 '"m00_b_ov5695 2-0036":0[fmt:SBGGR10_1X10/1920x1080]'
```

### 5.2 v4l2-ctl (抓图与参数设置)

```bash
# 查找 video 设备对应的 entity
grep "" /sys/class/video4linux/video*/name

# 抓帧 (YUV NV12, 640x480, 4帧)
v4l2-ctl -d /dev/video0 \
    --set-fmt-video=width=640,height=480,pixelformat=NV12 \
    --stream-mmap=4 --stream-to=out.yuv --stream-count=4

# 抓 RAW 图 (仅 MP 支持)
v4l2-ctl -d /dev/video0 \
    --set-fmt-video=width=2592,height=1944,pixelformat=BG10 \
    --stream-mmap=4 --stream-to=raw.bin --stream-count=1

# 设置曝光/gain
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl exposure=1000
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl analogue_gain=100
```

### 5.3 常用 mbus-code 与 FourCC

| Mbus Code | 简称 | 类型 | BPP |
|-----------|------|------|-----|
| MEDIA_BUS_FMT_SBGGR8_1X8 | SBGGR8 | Bayer Raw | 8 |
| MEDIA_BUS_FMT_SBGGR10_1X10 | SBGGR10 | Bayer Raw | 10 |
| MEDIA_BUS_FMT_SBGGR12_1X12 | SBGGR12 | Bayer Raw | 12 |
| MEDIA_BUS_FMT_YUYV8_2X8 | YUYV8 | YUV | 16 |
| MEDIA_BUS_FMT_UYVY8_2X8 | UYVY8 | YUV | 16 |

| FourCC | V4L2 宏 | 说明 |
|--------|---------|------|
| NV12 | V4L2_PIX_FMT_NV12 | YUV420 Semi-Planar |
| NV16 | V4L2_PIX_FMT_NV16 | YUV422 Semi-Planar |
| BG10 | V4L2_PIX_FMT_SBGGR10 | 10-bit Bayer BGGR |
| GREY | V4L2_PIX_FMT_GREY | 8-bit 灰度 |
| XR24 | V4L2_PIX_FMT_XBGR32 | 32-bit XRGB (仅SP) |

### 5.4 GStreamer 采集

```bash
# 预览
gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-raw,format=NV12,width=640,height=480 \
    ! waylandsink

# 编码保存
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=100 ! videoconvert \
    ! mpph264enc ! h264parse ! mp4mux ! filesink location=test.mp4
```

### 5.5 打开调试开关

```bash
# ISP 驱动 debug
echo 0xff > /sys/module/video_rkisp/parameters/debug

# CIF 驱动 debug
echo 0xff > /sys/module/video_rkcif/parameters/debug

# MIPI DPHY debug
echo 1 > /sys/module/phy_rockchip_csi2_dphy/parameters/debug

# Sensor I2C trace
echo 'file drivers/media/i2c/ov5695.c +p' > /sys/kernel/debug/dynamic_debug/control

# VB2 buffer 轮转 log (reqbuf/qbuf/dqbuf 状态, 注意: 全局开关, VPU/ISP 等均受影响)
echo 0xff > /sys/module/videobuf2_core/parameters/debug

# V4L2 ioctl 调用 log
echo 0xff > /sys/module/v4l2_common/parameters/debug
# 按 bit 开启: 定义见 include/media/v4l2-ioctl.h
```

### 5.7 抓帧后查看 YUV 图片

```bash
# 将板子上 out.yuv 拉到 PC, 用 ffplay 查看
ffplay -f rawvideo -pix_fmt nv12 -s 3264x2448 out.yuv
# 注意: 直接抓 ISP 输出不经 3A 处理, 画面可能偏绿 — 属正常现象
```

### 5.6 MP 与 SP 区别

| 特性 | MainPath (MP) | SelfPath (SP) |
|------|-------------|-------------|
| 最大分辨率 | Sensor 原始分辨率 | 1920×1080 |
| RAW 输出 | 支持 | 不支持 |
| RGB 输出 | 不支持 | 支持 (XR24/RGB565) |
| YUV 输出 | 支持 | 支持 |
| 同时使用 | MP+SP 可同时输出 (均为 YUV/RGB 时) |

---

## 6. 常见问题排查

### 6.1 Sensor 识别不到 / I2C 通讯失败

```
排查流程:
1. 检查 I2C 地址 → dmesg | grep -i "sensor\|chip.id\|i2c"
   ├─ 7-bit 地址 (reg 属性除以2)
   └─ 确认 I2C 总线号 → i2cdetect -y <bus>
2. 检查 mclk → 示波器测量 24M，确认电压幅度匹配 IO 电源域
   └─ io_domains 可能晚于 sensor probe → 返回 -EPROBE_DEFER 重试
3. 检查电源 → 测量 avdd (2.8V), dovdd (1.8V), dvdd (1.2/1.5V)
4. 检查 reset/pwdn GPIO 极性 → 对照 datasheet active level
5. 检查上电时序 → 示波器验证各电源和 clk 的时序间隔
```

### 6.2 不出图 (无帧数据)

```
排查流程:
1. dmesg | grep -i "mipi\|isp\|cif" → 有无报错
2. 确认 sensor I2C 寄存器写入无报错
3. 示波器量 MIPI clk/data lane → 有无信号输出
4. 检查 MIPI 4 参数: 分辨率/格式/link_freq/lane数
5. 确认 s_stream() 中才使能 MIPI 输出 (s_power 阶段不要输出)
6. 尝试 clock lane: continue → non-continues 模式
```

### 6.3 MIPI 报错处理

| 错误类型 | 含义 | 排查方向 |
|---------|------|---------|
| SOT / SOT_SYNC | 起始信号异常 | 确认 link_freq (影响 Ths-settle)；测波形 |
| ECC / ECC1 / ECC2 | 数据包头纠错失败 | 硬件信号完整性；尝试减少 lane 数 |
| CRC / CheckSum | 数据 CRC 校验失败 | 硬件信号完整性 |
| ERR_PROTOCOL / F_BNDRY | SOT/EOT 未配对 | 测波形 |
| SYNC_FIFO_OVFLW | 同步 FIFO 溢出 | DDR 带宽不足 |

**仅开机初始有 MIPI 错误的处理：**

1. 将寄存器初始化放到 `s_power()` (此时 MIPI 接收端未准备好，忽略数据)
2. `s_power()` 末尾调用 `stop_stream()`
3. `start_stream()` / `stop_stream()` 仅控制 MIPI 输出开关

### 6.4 PIC_SIZE_ERROR

```
排查:
1. 先解决 MIPI 报错 (如有)
2. DDR 定频到最高: echo performance > /sys/class/devfreq/dmc/governor
3. 检查链路分辨率: Sensor ≥ MIPI_DPHY ≥ ISP_input ≥ ISP_output
   → media-ctl -p -d /dev/media0
4. 尝试缩小 sensor 输出分辨率 (不改寄存器，仅改 mode 宽高值)
```

### 6.5 颜色异常/偏暗偏亮

- **RAW Sensor**: 需要 3A 正常运行 → 检查 `rkisp_3A_server` 进程和 IQ xml
- **YUV Sensor**: ISP bypass → 联系 Sensor 原厂确认格式配置
- 检查 UV 分量是否反序

### 6.6 抓图格式注意事项

- RAW 图仅 MP 支持，SP 不出 RAW
- 10/12-bit RAW 输出时，每像素低位补 0 到 16bit
- RGB 格式仅 SP 支持 (XR24, RGB565)
- GREY 灰度格式：Y8 源可直接用 `V4L2_PIX_FMT_GREY`

### 6.7 I2C 正常但无图像数据

```
现象: Sensor probe 成功, chip id 读取到, 但 v4l2-ctl 抓图 0KB / App 闪退
dmesg 可能报: MIPI 通信异常、包异常

诊断: I2C (低速控制) 正常 + MIPI data (高速数据) 异常 → 硬件信号问题
排查:
1. 确认排线/连接器接触良好 (重新插拔)
2. 更换已知好的 Sensor 模组对比
3. 示波器测 MIPI clk/data lane 有无差分信号输出
→ 如上述排查后仍无数据, 高概率为模组 MIPI PHY 损坏
```

---

## 7. 3A Server 部署

### 7.1 rkisp_3A_server 使用

```bash
# 检查进程
ps aux | grep rkisp_3A_server

# 手动启动
rkisp_3A_server --mmedia=/dev/media0 &

# 开启 log
export persist_camera_engine_log=0xff
rkisp_3A_server --mmedia=/dev/media0 &

# IQ xml 文件路径 (自动匹配规则)
# /etc/iqfiles/{sensor}_{module-name}_{lens-name}.xml
```

### 7.2 IQ XML 匹配规则

IQ 文件名由 sensor DTS 中的三个属性决定：
- `rockchip,camera-module-name` → 模组名
- `rockchip,camera-module-lens-name` → 镜头名
- sensor 名称 (compatible 字段)

---

## 8. 深入参考

| 主题 | 参考文件 |
|------|---------|
| Sensor 驱动移植详解 + DTS 完整示例 | → [sensor_driver_porting.md](references/sensor_driver_porting.md) |
| RK3588 多摄方案 + DPHY/DCPHY 链路配置 | → [rk3588_multi_camera.md](references/rk3588_multi_camera.md) |
| MIPI CSI-2 错误诊断 + V4L2 调试命令 | → [mipi_v4l2_debug.md](references/mipi_v4l2_debug.md) |

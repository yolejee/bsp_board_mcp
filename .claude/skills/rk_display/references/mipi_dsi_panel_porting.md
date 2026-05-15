# MIPI DSI 面板完整移植参考

## 目录

1. [MIPI DSI 基础](#1-mipi-dsi-基础)
2. [面板移植完整流程](#2-面板移植完整流程)
3. [init-sequence 编写详解](#3-init-sequence-编写详解)
4. [常见面板驱动 IC](#4-常见面板驱动-ic)
5. [DSI 调试方法](#5-dsi-调试方法)
6. [RK3588 DSI2 特性](#6-rk3588-dsi2-特性)
7. [常见问题 FAQ](#7-常见问题-faq)

---

## 1. MIPI DSI 基础

### 1.1 DSI 模式

| 模式 | 标志 | 说明 |
|------|------|------|
| Video Mode - Burst | `MIPI_DSI_MODE_VIDEO \| MIPI_DSI_MODE_VIDEO_BURST` | 高效, 适合大分辨率 |
| Video Mode - Non-Burst Sync Event | `MIPI_DSI_MODE_VIDEO` | 精确时序控制 |
| Video Mode - Non-Burst Sync Pulse | `MIPI_DSI_MODE_VIDEO \| MIPI_DSI_MODE_VIDEO_SYNC_PULSE` | 兼容性好 |
| Command Mode | 无 `MIPI_DSI_MODE_VIDEO` | OLED 常用 |

### 1.2 DSI 数据格式

| 格式 | 值 | 说明 |
|------|---|------|
| `MIPI_DSI_FMT_RGB888` | 0 | 24bpp, 最常用 |
| `MIPI_DSI_FMT_RGB666` | 1 | 18bpp |
| `MIPI_DSI_FMT_RGB666_PACKED` | 2 | 18bpp 压缩 |
| `MIPI_DSI_FMT_RGB565` | 3 | 16bpp |

### 1.3 Lane Rate 计算

```
lane_rate = pixel_clock × bpp / lanes

例: 1920×1080@60Hz, RGB888 (24bpp), 4lanes
pixel_clock = (1920+80+40+80) × (1080+10+4+20) × 60 ≈ 141MHz
lane_rate = 141 × 24 / 4 = 846 Mbps

# 实际需要: lane_rate × 1.1 (预留 10% overhead)
# DTS 中可不设, 驱动会自动计算
```

---

## 2. 面板移植完整流程

### 2.1 准备工作

```
1. 获取面板规格书 (Datasheet)
   → 提取: 分辨率, timing 参数, 初始化序列, 接口电气参数
2. 获取面板驱动 IC datasheet
   → 提取: DCS command set, 寄存器定义
3. 确认硬件连接
   → 确认: lanes 数量, reset/enable GPIO, 背光 PWM, 供电
4. 确认显示通路
   → 选择: VP → DSI controller → Panel
```

### 2.2 DTS 编写步骤

```
Step 1: 选择 VOP 通路 (route_dsi0)
Step 2: 配置 DSI controller (&dsi0)
Step 3: 在 DSI 下添加 panel 节点
Step 4: 填写 timing 参数 (从规格书)
Step 5: 编写 init-sequence (从规格书或模组厂)
Step 6: 配置 GPIO (reset, enable, backlight)
Step 7: 配置 Pinctrl (DSI data/clock lanes)
Step 8: 编写 backlight 节点
```

---

## 3. init-sequence 编写详解

### 3.1 命令格式

```
panel-init-sequence = [
    <data_type> <delay> <len> <payload...>
];

data_type (1 byte):
  05 = DCS Short Write, no parameter
  15 = DCS Short Write, 1 parameter
  39 = DCS Long Write (Generic Long Write)
  29 = Generic Long Write (等同 39)

delay (1 byte): 命令发送后延迟, 单位 ms
  00 = 不延迟
  0A = 10ms
  14 = 20ms
  78 = 120ms

len (1 byte): payload 长度 (包括 DCS command byte)
```

### 3.2 常用 DCS 命令速查

| 命令 | 名称 | 用法 |
|------|------|------|
| 0x01 | Soft Reset | `05 78 01 01` |
| 0x10 | Sleep In | `05 78 01 10` |
| 0x11 | Sleep Out | `05 78 01 11` (必须延迟 ≥120ms) |
| 0x28 | Display Off | `05 14 01 28` |
| 0x29 | Display On | `05 14 01 29` (Sleep Out 之后) |
| 0x36 | Set Address Mode | `15 00 02 36 <mode>` |
| 0x3A | Set Pixel Format | `15 00 02 3A 77` (RGB888) |
| 0x51 | Set Brightness | `15 00 02 51 FF` |
| 0xB0 | Manufacturer Command Access | IC 厂商特定 |

### 3.3 从规格书转换示例

```
规格书中的初始化序列 (常见格式):

  送 FF, 98, 81, 03               →  39 00 04 FF 98 81 03
  送 01 = 00                       →  15 00 02 01 00
  送 02 = 01                       →  15 00 02 02 01
  送 Sleep Out                     →  05 78 01 11
  送 Display On                    →  05 14 01 29

如果规格书给的是 C 代码:
  dsi_dcs_write_seq(ctx, 0xFF, 0x98, 0x81, 0x03);
  → 39 00 04 FF 98 81 03
  
  mipi_dsi_dcs_set_display_on(dsi);
  → 05 14 01 29
```

---

## 4. 常见面板驱动 IC

| IC | 厂商 | 典型分辨率 | 特点 |
|-----|------|----------|------|
| ILI9881C/D | 奕力 Ilitek | 720×1280~1080×1920 | 手机屏常用 |
| HX8394F | 海信微 Himax | 720×1280 | 低分辨率 |
| NT35596 | 联咏 Novatek | 1080×1920 | 高分辨率手机屏 |
| ST7701S | Sitronix | 480×854~720×1280 | 小屏 SPI+RGB |
| JD9365DA | 集创北方 | 800×1280 | 平板常用 |
| EK79007 | 奕力 | 1024×600 | 7 寸屏 |
| ICN6211 | 集创 | - | MIPI-DSI 转 RGB 桥片 |

---

## 5. DSI 调试方法

### 5.1 基本检查

```bash
# 查看 DSI connector 状态
cat /sys/class/drm/card0-DSI-1/status

# 查看 VOP summary
cat /sys/kernel/debug/dri/0/summary

# DSI 相关日志
dmesg | grep -i "dsi\|panel\|mipi\|backlight"

# DRM debug 日志
echo 0x1f > /sys/module/drm/parameters/debug
dmesg | grep -i drm
```

### 5.2 逐步调试

```
1. 先确认背光 → 背光亮=供电OK, GPIO OK
2. 确认 reset 信号 → 测量 reset GPIO 波形
3. 确认 DSI controller probe → dmesg 中 "dsi" 相关
4. 确认 panel probe → dmesg 中 "panel" / "simple-panel-dsi"
5. 确认 init-sequence 发送 → 开 DRM debug
6. 确认 timing → pixel clock 和实际时钟源匹配
```

---

## 6. RK3588 DSI2 特性

```
RK3588 使用 DSI-2 (MIPI DSI v2.0):
- 支持 D-PHY 和 C-PHY
- D-PHY: 最高 4.5 Gbps/lane
- C-PHY: 最高 2.5 Gsps/trio
- 向下兼容 DSI v1.x

DTS 中的差异:
&dsi0 → 使用 dsi2 节点 (&dsi0 in RK3588 = DSI2)
panel compatible 不变: "simple-panel-dsi"

需要注意:
- RK3588 DSI2 和 RK3568 DSI1 的 DTS 节点名不同
- C-PHY 配置需要额外参数
```

---

## 7. 常见问题 FAQ

### 7.1 屏幕白屏

```
原因: DSI controller 已输出信号, 但 panel 未初始化
排查:
1. init-sequence 是否正确执行 (检查 DCS 命令)
2. Sleep Out + Display On 延迟是否足够
3. Reset GPIO 时序是否满足规格
```

### 7.2 屏幕花屏/条纹

```
原因: timing 参数不匹配 或 DSI 信号质量差
排查:
1. 核对 display-timings 所有参数
2. 检查 dsi,lanes 数量
3. 降低 lane-rate 测试
4. 检查 DSI 走线长度和阻抗
```

### 7.3 屏幕颜色不对

```
原因: 像素格式或颜色空间设置错误
排查:
1. dsi,format 是否正确 (RGB888 vs RGB666)
2. Set Address Mode (0x36) 的 RGB/BGR 位
3. display-timings 中 de-active 极性
```

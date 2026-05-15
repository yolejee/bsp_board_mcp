---
name: rk_display
description: "Rockchip 瑞芯微平台显示子系统技能。覆盖 RK3588/RK3568/RK3566/RK3399/RK3288/PX30 等全系列芯片的 DRM 显示驱动开发、VOP/VOP2 配置、MIPI DSI 面板移植、HDMI 输出调试、DisplayPort/eDP 调试、LVDS 配置、多屏显示、显示通路选择。触发关键词包括但不限于：显示、display、屏幕、LCD、面板、panel、VOP、VOP2、video port、VP0、VP1、VP2、VP3、MIPI DSI、MIPI DSI2、dsi0、dsi1、HDMI、hdmi_in、DP、DisplayPort、eDP、LVDS、DRM、libdrm、modetest、connector、CRTC、encoder、plane、display-timings、lane-rate、dsi-panel、panel-init-sequence、panel-simple、route_hdmi、route_dsi0、route_dsi1、route_edp、route_lvds、backlight、PWM 背光、HDCP、CEC、HPD、热插拔、花屏、闪屏、黑屏、不亮、分辨率、timing、pixel clock、baseparameter、RK628、BT656、BT1120。当用户提到 Rockchip 平台的任何显示相关问题时触发本技能。"
---

# Rockchip 显示子系统技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| 屏幕不亮/黑屏 | §7 排查流程 |
| MIPI DSI 面板移植 | §3 |
| HDMI 不显示/异常 | §4 |
| DP/eDP 问题 | §5 |
| 多屏显示配置 | §6 |
| VOP 显示通路选择 | §2 |
| display-timings 参数 | §3.2 |
| 花屏/闪屏/撕裂 | §7 |

---

## 1. Rockchip 显示子系统架构

### 1.1 显示通路

```
                    ┌─→ MIPI DSI0 → Panel
                    ├─→ MIPI DSI1 → Panel
Video Port (VP) ──→ ├─→ HDMI → Monitor
                    ├─→ eDP → Panel
                    ├─→ DP → Monitor
                    └─→ LVDS → Panel
```

### 1.2 DRM 组件对应关系

| DRM 概念 | Rockchip 实体 | 说明 |
|---------|-------------|------|
| CRTC | VOP / Video Port | 显示控制器,生成时序 |
| Encoder | DSI/HDMI/DP/eDP/LVDS controller | 信号编码器 |
| Connector | Panel/Monitor 连接器 | 物理接口 |
| Plane | VOP 图层 (win) | Cluster/Esmart/Smart |

### 1.3 各平台 VOP 特性概览

| 平台 | VOP 类型 | VP 数量 | 最大输出 | 支持接口 |
|------|---------|--------|---------|---------|
| RK3588 | VOP2 | 4 (VP0-3) | 4K@120/8K@30 | HDMI×2+DP×2+DSI×2+eDP×2 |
| RK3568 | VOP2 | 3 (VP0-2) | 4K@60 | HDMI+DSI×2+eDP+LVDS |
| RK3566 | VOP2 | 3 (VP0-2) | 4K@60 | HDMI+DSI+eDP+LVDS |
| RK3399 | VOP | 2 (Big+Lit) | 4K@60 | HDMI+DSI×2+eDP+DP |
| RK3288 | VOP | 2 (Big+Lit) | 4K@30 | HDMI+DSI+eDP+LVDS |
| PX30 | VOP | 2 | 1920×1080 | DSI+LVDS |

---

## 2. VOP2 显示通路配置

### 2.1 RK3568/RK3566 VP 连接关系

```
VP0 ──→ HDMI / eDP / DSI0 (4K@60 capable)
VP1 ──→ HDMI / eDP / DSI0 / LVDS (2K capable)
VP2 ──→ LVDS / DSI1 (1080p capable)
```

### 2.2 RK3588 VP 连接关系

```
VP0 ──→ HDMI0 / eDP0 / DP0     (8K@30 / 4K@120)
VP1 ──→ HDMI1 / eDP1 / DP1     (4K@60)
VP2 ──→ HDMI1 / eDP1 / DSI0 / DP1  (4K@60)
VP3 ──→ DSI1 / DP1             (2K capable)
```

### 2.3 DTS 显示通路配置

```dts
// 方法1: route 节点 (推荐)
&route_hdmi {
    status = "okay";
    connect = <&vp0_out_hdmi>;     // 指定 VP0 输出到 HDMI
};

&route_dsi0 {
    status = "okay";
    connect = <&vp1_out_dsi0>;     // VP1 输出到 DSI0
};

// 方法2: 直接操作 endpoint
&vp0 {
    cursor-win-id = <ROCKCHIP_VOP2_CLUSTER0>;
};

&vp0_out_hdmi {
    status = "okay";
};

&hdmi {
    status = "okay";
};

&hdmi_in_vp0 {
    status = "okay";
};
```

### 2.4 图层 (Plane) 分配

```
RK3568/RK3566 VOP2 图层:
  Cluster0, Cluster1     → 支持 AFBC, 4K 缩放
  Esmart0, Esmart1       → 多格式, 缩放
  Smart0, Smart1         → 基础图层

VP 与图层的关系:
  VP0: Cluster0 + Esmart0 + Smart0 (默认)
  VP1: Cluster1 + Esmart1 + Smart1

  可通过 DTS 调整图层分配策略
```

---

## 3. MIPI DSI 面板移植

### 3.1 DTS 配置模板

```dts
&dsi0 {
    status = "okay";

    panel@0 {
        compatible = "simple-panel-dsi";
        reg = <0>;                          // DSI virtual channel
        backlight = <&backlight>;
        power-supply = <&vcc_3v3>;
        reset-gpios = <&gpio0 RK_PC2 GPIO_ACTIVE_LOW>;
        enable-gpios = <&gpio0 RK_PB5 GPIO_ACTIVE_HIGH>;

        // 初始化前延迟
        prepare-delay-ms = <120>;
        reset-delay-ms = <20>;
        init-delay-ms = <20>;
        enable-delay-ms = <120>;
        unprepare-delay-ms = <20>;
        disable-delay-ms = <20>;

        // DSI 参数
        dsi,flags = <(MIPI_DSI_MODE_VIDEO |
                      MIPI_DSI_MODE_VIDEO_BURST |
                      MIPI_DSI_MODE_LPM |
                      MIPI_DSI_MODE_EOT_PACKET)>;
        dsi,format = <MIPI_DSI_FMT_RGB888>;
        dsi,lanes = <4>;

        // 面板初始化序列 (从面板规格书获取)
        panel-init-sequence = [
            39 00 04 FF 98 81 03    // DCS Long Write
            15 00 02 01 00          // DCS Short Write (1 param)
            05 78 01 11             // DCS Short Write (no param) + delay 120ms
            05 14 01 29             // Display ON + delay 20ms
        ];

        panel-exit-sequence = [
            05 00 01 28             // Display OFF
            05 78 01 10             // Sleep IN + delay 120ms
        ];

        // 显示时序
        display-timings {
            native-mode = <&timing0>;
            timing0: timing0 {
                clock-frequency = <65000000>;
                hactive = <1024>;
                vactive = <600>;
                hfront-porch = <160>;
                hsync-len = <20>;
                hback-porch = <140>;
                vfront-porch = <12>;
                vsync-len = <3>;
                vback-porch = <20>;
                hsync-active = <0>;
                vsync-active = <0>;
                de-active = <0>;
                pixelclk-active = <0>;
            };
        };

        ports {
            #address-cells = <1>;
            #size-cells = <0>;
            port@0 {
                reg = <0>;
                panel_in_dsi: endpoint {
                    remote-endpoint = <&dsi_out_panel>;
                };
            };
        };
    };

    ports {
        #address-cells = <1>;
        #size-cells = <0>;
        port@1 {
            reg = <1>;
            dsi_out_panel: endpoint {
                remote-endpoint = <&panel_in_dsi>;
            };
        };
    };
};
```

### 3.2 display-timings 参数说明

```
              hback  hsync  hfront
              porch  len    porch
           ├───────┤├────┤├────────┤
  ─────────┤                       ├──────
           │  hactive (有效像素)    │
  ─────────┤                       ├──────
           ├───────┤├────┤├────────┤
              vback  vsync  vfront
              porch  len    porch

pixel clock = (hactive + hfp + hsync + hbp) × (vactive + vfp + vsync + vbp) × fps
```

### 3.3 panel-init-sequence 格式

```
每条命令格式: <data_type> <delay_ms> <payload_len> <payload...>

data_type:
  05 → DCS Short Write (no parameter)       例: 05 00 01 28 (Display Off)
  15 → DCS Short Write (1 parameter)        例: 15 00 02 51 FF (Set brightness)
  39 → DCS Long Write                       例: 39 00 04 FF 98 81 03

delay_ms:
  00 → 无延迟
  78 → 120ms (0x78 = 120)
  14 → 20ms

常用 DCS 命令:
  0x11 → Sleep Out
  0x29 → Display On
  0x10 → Sleep In
  0x28 → Display Off
  0x51 → Set Brightness
```

### 3.4 背光配置

```dts
backlight: backlight {
    compatible = "pwm-backlight";
    pwms = <&pwm0 0 25000 0>;        // <phandle channel period_ns polarity>
    brightness-levels = <
        0  20  20  21  21  22  22  23
       23  24  24  25  25  26  26  27
      ... (0~255 映射表)
      255>;
    default-brightness-level = <200>;
    enable-gpios = <&gpio0 RK_PB7 GPIO_ACTIVE_HIGH>;
};
```

---

## 4. HDMI 配置与调试

### 4.1 HDMI DTS 配置

```dts
&hdmi {
    status = "okay";
    // rockchip,phy-table = <...>;  // PHY 信号强度 (特殊需求)
};

&hdmi_in_vp0 {
    status = "okay";
};

// RK3588 双 HDMI
&hdmi0 {
    status = "okay";
};
&hdmi0_in_vp0 {
    status = "okay";
};
```

### 4.2 HDMI 调试命令

```bash
# 查看 connector 状态
cat /sys/class/drm/card0-HDMI-A-1/status     # connected/disconnected
cat /sys/class/drm/card0-HDMI-A-1/modes       # 支持的分辨率列表

# 查看当前分辨率
cat /sys/class/drm/card0-HDMI-A-1/mode

# 使用 modetest 查看完整 DRM 信息
modetest -M rockchip

# modetest 测试显示
modetest -M rockchip -s <conn_id>@<crtc_id>:<WxH>
# 例: modetest -M rockchip -s 175@67:1920x1080

# 查看 VOP 状态
cat /sys/kernel/debug/dri/0/summary

# 调整 DRM 日志等级
echo 0x1f > /sys/module/drm/parameters/debug
# 0x01=CORE 0x02=DRIVER 0x04=KMS 0x08=PRIME 0x10=ATOMIC
```

### 4.3 HDMI 常见问题

```bash
# 4K 显示异常:
# → 检查 VP 是否支持 4K (VP0 通常支持, VP2 可能不够)
# → 检查 pixel clock 是否足够
# → HDMI 2.0 需要 TMDS > 340MHz

# HDCP 不工作:
# → CONFIG_ROCKCHIP_HDMI_HDCP=y
# → 需要烧录 HDCP key

# CEC 不工作:
# → CONFIG_ROCKCHIP_HDMI_CEC=y
# → 检查 CEC 引脚连接

# HPD (热插拔) 不检测:
# → 检查 HPD 引脚, 部分需要上拉
```

---

## 5. DP / eDP 配置

### 5.1 DisplayPort (Type-C)

```dts
// RK3588 DP (Type-C Alt Mode)
&dp0 {
    status = "okay";
};

&dp0_in_vp0 {
    status = "okay";
};

// 需要 Type-C PHY 支持
&usbdp_phy0 {
    status = "okay";
};
```

### 5.2 eDP

```dts
&edp {
    status = "okay";

    panel {
        compatible = "simple-panel";
        backlight = <&backlight>;
        power-supply = <&vcc_3v3>;
        prepare-delay-ms = <20>;
        enable-delay-ms = <20>;

        display-timings {
            native-mode = <&edp_timing>;
            edp_timing: timing0 {
                clock-frequency = <148500000>;
                hactive = <1920>;
                vactive = <1080>;
                // ... timing 参数
            };
        };
    };
};

&edp_in_vp0 {
    status = "okay";
};
```

### 5.3 DP 调试

```bash
# 查看 DP connector 状态
cat /sys/class/drm/card0-DP-1/status

# DPCD 读写 (DP Configuration Data)
cat /sys/kernel/debug/dri/0/dp-*/dpcd    # 如果有

# 查看 Link Training 状态
dmesg | grep -i "dp\|link training"
# "Link training passed" → 成功
# "Link training failed" → 信号/PHY 问题
```

### 5.4 LVDS

LVDS 仅在 RK3568/RK3566/PX30 等部分平台支持，通常复用 DSI DPHY。

```dts
// RK3568 LVDS
&video_phy0 { status = "okay"; };
&lvds { status = "okay";
    ports { port@1 { reg = <1>;
        lvds_out_panel: endpoint { remote-endpoint = <&panel_in_lvds>; };
    }; };
};
&lvds_in_vp1 { status = "okay"; };
&route_lvds { status = "okay"; connect = <&vp1_out_lvds>; };

/ {
    lvds_panel: lvds-panel {
        compatible = "panel-lvds";
        backlight = <&backlight>;
        power-supply = <&vcc_3v3>;
        data-mapping = "vesa-24";    // 或 "jeida-24"/"jeida-18", 查面板规格书
        width-mm = <217>; height-mm = <136>;
        display-timings {
            native-mode = <&lvds_timing>;
            lvds_timing: timing0 {
                clock-frequency = <71100000>;
                hactive = <1280>; vactive = <800>;
                hback-porch = <50>; hfront-porch = <32>; hsync-len = <10>;
                vback-porch = <5>; vfront-porch = <3>; vsync-len = <5>;
            };
        };
        port { panel_in_lvds: endpoint { remote-endpoint = <&lvds_out_panel>; }; };
    };
};
```

> **data-mapping**: `vesa-24` (最常用) vs `jeida-24`(日系面板多见)，选错会偏色/花屏。

---

## 6. 多屏显示

### 6.1 双屏异显 (不同内容)

```dts
// VP0 → HDMI, VP1 → DSI0
&route_hdmi {
    status = "okay";
    connect = <&vp0_out_hdmi>;
};

&route_dsi0 {
    status = "okay";
    connect = <&vp1_out_dsi0>;
};
```

### 6.2 双屏同显 (镜像)

```bash
# 运行时配置
# 使用 weston.ini 或应用层控制
# 需要两个 VP 输出相同分辨率和时序
```

### 6.3 多屏注意事项

```
- 每个显示接口只能连接一个 VP
- VP 的能力不同 (VP0 通常最强)
- 4K 输出需要高带宽 VP
- 多 4K 同时输出可能超出 DDR 带宽
- RK3588 最多支持 4 个独立显示输出
```

---

## 7. 显示问题排查流程

### 7.1 屏幕不亮诊断

```
屏幕不亮
├── 背光亮不亮?
│   ├── 不亮 → 检查 PWM backlight / enable-gpio / 供电
│   └── 亮但无图像 ↓
├── HDMI/DP 有信号?
│   ├── connector status = disconnected → HPD/线缆/接口
│   └── connected 但无画面 → Link Training / 分辨率不支持
├── MIPI DSI 排查
│   ├── 检查 reset/enable GPIO 时序
│   ├── 检查 init-sequence (从规格书核对)
│   ├── 检查 lane 数量和 lane-rate
│   └── 检查 display-timings (pixel clock)
└── VOP 状态检查
    ├── cat /sys/kernel/debug/dri/0/summary
    ├── VP 是否 enable
    └── plane 是否有 buffer 绑定
```

### 7.2 常用调试命令汇总

```bash
# DRM 状态总览
modetest -M rockchip
cat /sys/kernel/debug/dri/0/summary
cat /sys/kernel/debug/dri/0/state

# Connector 信息
for f in /sys/class/drm/card0-*/status; do echo "$f: $(cat $f)"; done

# 时钟检查
cat /sys/kernel/debug/clk/clk_summary | grep -i "vop\|hdmi\|dsi\|edp\|dp"

# VOP display buffer dump (需要内核开启 CONFIG_ROCKCHIP_DRM_DEBUG)
echo 1 > /sys/kernel/debug/dri/0/ff900000.vop/dump
# buffer 保存到 /data/vop_buf/，可 pull 出来用图像工具分析

# EDID 获取 (HDMI/DP)
cat /sys/class/drm/card0-HDMI-A-1/edid | edid-decode

# GEM buffer 占用
cat /sys/kernel/debug/dri/0/gem

# 暂停显示进程 (修改 VOP 寄存器前必须停掉用户态进程，否则会被覆盖)
# Android:  stop surfaceflinger / start surfaceflinger
# Weston:   killall -STOP weston / killall -CONT weston
# Xserver:  killall -STOP Xorg / killall -CONT Xorg
```

### 7.3 花屏/闪屏/撕裂

```bash
# 花屏:
# → MIPI: lane-rate 不匹配 / 信号完整性 / init-sequence 错误
# → HDMI: PHY 信号强度 / TMDS 时钟不稳定

# 闪屏:
# → U-Boot 到 Kernel 过渡: 显示通路不一致
# → 分辨率切换过程中

# 撕裂 (Tearing):
# → 没有启用 Vsync
# → DRM atomic commit 配置
```

### 7.4 VOP POST_BUF_EMPTY (常见)

```
报错 log: "POST_BUF_EMPTY" 或 "POST_EMPTY" — VOP 来不及从 DDR 取到数据

原因与处理:
1. DDR 带宽不足 → 固定 DDR 最高频率测试; 加大屏的消隐期 (blanking)
2. IOMMU pagefault → dmesg 检查 iommu 报错，更新到最新内核代码
3. Logic 电压太低 → 尝试提高 vdd_logic 100mV 测试
4. AFBDC 对齐 → 屏分辨率非 16pixel 对齐时关闭 AFBDC
   (PX30/RK3326/RK3368/RK3399/RK356X/RK3588)
```

### 7.5 显示效果调节 (BCSH)

```bash
# VOP 内部 BCSH 模块支持亮度/对比度/饱和度/色度调节
# 通过 modetest 设置 connector 属性:
modetest -M rockchip -w <conn_id>:brightness:<0-100>
modetest -M rockchip -w <conn_id>:contrast:<0-100>
modetest -M rockchip -w <conn_id>:saturation:<0-100>
# 默认值 50, 步进 1
```

---

## References

> 以下参考文件在需要深入信息时由 AI 自动加载：

| 文件 | 内容 |
|------|------|
| `references/mipi_dsi_panel_porting.md` | MIPI DSI 面板完整移植流程、init-sequence 编写、调试方法、常见面板驱动 IC |
| `references/hdmi_dp_debug.md` | HDMI/DP/eDP 深入调试、Link Training 分析、PHY 配置、CEC/HDCP、4K/8K 配置 |
| `references/vop2_multi_display.md` | VOP2 架构详解、图层分配策略、多屏配置、baseparameter、DRM 调试接口 |

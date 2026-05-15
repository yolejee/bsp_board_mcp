# Rockchip 显示子系统 DTS 配置参考

## VOP2 架构 (RK3566/RK3568)

RK3566/RK3568 使用 VOP2 (Video Output Processor 2nd gen) 驱动显示输出。

### Video Port 架构

```
VOP2
├── VP0 (主输出, 支持最高 4K)
│   ├── vp0_out_hdmi
│   ├── vp0_out_dsi0
│   ├── vp0_out_dsi1
│   ├── vp0_out_edp
│   └── vp0_out_lvds
│
└── VP1 (副输出, 最高 2K)
    ├── vp1_out_hdmi
    ├── vp1_out_dsi0
    ├── vp1_out_dsi1
    ├── vp1_out_edp
    └── vp1_out_lvds
```

### 显示通路配置规则

1. **一个 VP 只能连接一个显示接口**
2. **HDMI 通常使用 VP0** (支持 4K)
3. **双屏时**：HDMI=VP0, DSI/eDP=VP1
4. **需要同时配置**：VP 选择 + route 节点 + PHY 使能

### HDMI 配置详解

```dts
// 1. 使能 HDMI 控制器
&hdmi {
    status = "okay";
    // PHY 参数表 (频率 → 寄存器值)
    rockchip,phy-table =
        <92812500  0x8009 0x0000 0x0270>,
        <165000000 0x800b 0x0000 0x026d>,
        <185625000 0x800b 0x0000 0x01ed>,
        <297000000 0x800b 0x0000 0x01ad>,
        <594000000 0x8029 0x0000 0x0088>,
        <000000000 0x0000 0x0000 0x0000>;
};

// 2. 选择 VP
&hdmi_in_vp0 { status = "okay"; };
&hdmi_in_vp1 { status = "disabled"; };

// 3. 配置 route
&route_hdmi {
    status = "okay";
    connect = <&vp0_out_hdmi>;
};

// 4. I2S 音频 (HDMI 需要 I2S0)
&i2s0_8ch { status = "okay"; };

// 5. HDMI 音频声卡
/ {
    hdmi_sound: hdmi-sound {
        compatible = "simple-audio-card";
        simple-audio-card,format = "i2s";
        simple-audio-card,mclk-fs = <128>;
        simple-audio-card,name = "rockchip,hdmi";

        simple-audio-card,cpu {
            sound-dai = <&i2s0_8ch>;
        };
        simple-audio-card,codec {
            sound-dai = <&hdmi>;
        };
    };
};
```

### MIPI DSI 配置详解

#### 分层结构

```
通用 DSI 模板 (rk3568-lubancat-dsi.dtsi)
  └── 定义 dsi0 控制器、面板框架、触摸框架
      └── 屏幕特定 dtsi (如 rk3568-lubancat-dsi0-7.0-1024x600.dtsi)
          └── 填入 panel-init-sequence, display-timings
              └── 板级适配 dtsi (如 rk3566-lubancat-dsi0-7.0-1024x600.dtsi)
                  └── 配置 VP 选择, 板级 GPIO
```

#### 核心参数

| 参数 | 含义 | 示例 |
|------|------|------|
| `dsi,lanes` | MIPI 数据通道数 | `<2>` 或 `<4>` |
| `dsi,format` | 像素格式 | `<MIPI_DSI_FMT_RGB888>` |
| `dsi,flags` | 传输模式标志 | VIDEO_MODE \| BURST \| LPM \| EOT |
| `clock-frequency` | 像素时钟频率 (Hz) | `<51669000>` for 1024x600 |
| `hactive` / `vactive` | 有效显示分辨率 | `<1024>` / `<600>` |
| `hsync-len` | 水平同步脉冲宽度 | `<10>` |
| `hback-porch` | 水平后沿 | `<160>` |
| `hfront-porch` | 水平前沿 | `<160>` |
| `vsync-len` | 垂直同步脉冲宽度 | `<1>` |
| `vback-porch` | 垂直后沿 | `<23>` |
| `vfront-porch` | 垂直前沿 | `<12>` |

#### 像素时钟计算

```
pixel_clock = (hactive + hsync + hbp + hfp) × (vactive + vsync + vbp + vfp) × fps
例: (1024+10+160+160) × (600+1+23+12) × 60 ≈ 51.6 MHz
```

#### panel-init-sequence 格式

```
panel-init-sequence = [
    <type> <delay_ms> <len> <data...>
];

type: 05 = DCS short write 0 参数
      15 = DCS short write 1 参数  
      39 = DCS long write
delay_ms: 命令发送后的延时 (毫秒)
len: 数据长度
data: 寄存器地址 + 数据

例:
15 00 02 80 AC    → 写寄存器 0x80, 值 0xAC, 0ms 延时
05 78 01 28       → 命令 0x28 (Display OFF), 120ms 延时
05 00 01 10       → 命令 0x10 (Sleep In), 0ms 延时
```

### 背光 PWM 配置

```dts
backlight: backlight {
    compatible = "pwm-backlight";
    pwms = <&pwm4 0 25000 0>;
    // pwm4: PWM 控制器
    // 0: PWM 通道
    // 25000: 周期 (ns) → 40kHz
    // 0: 极性 (0=正常, PWM_POLARITY_INVERTED=反转)

    brightness-levels = <0 1 2 ... 255>;
    default-brightness-level = <200>;
    status = "okay";
};
```

### eDP 配置

```dts
&edp {
    status = "okay";

    edp_panel: edp-panel {
        compatible = "simple-panel";
        backlight = <&backlight>;
        power-supply = <&edp_power>;
        // display-timings 与 DSI 类似
    };
};

&edp_phy {
    status = "okay";
};

&edp_in_vp0 { status = "okay"; };
&edp_in_vp1 { status = "disabled"; };
&route_edp {
    status = "okay";
    connect = <&vp0_out_edp>;
};
```

### LVDS 配置 (通过 DSI 转 LVDS)

Rockchip 部分芯片没有原生 LVDS，通过 DSI-to-LVDS 桥接芯片 (如 rk618, sn65dsi84) 实现：

```dts
&dsi0 {
    status = "okay";

    ports {
        port@1 {
            dsi0_out_bridge: endpoint {
                remote-endpoint = <&bridge_in_dsi0>;
            };
        };
    };
};

// LVDS 桥接芯片
&i2c4 {
    lvds_bridge: sn65dsi84@2c {
        compatible = "ti,sn65dsi84";
        reg = <0x2c>;
        // ...
    };
};
```

## 多屏配置示例

### HDMI + MIPI 双屏

```dts
// HDMI 走 VP0
&hdmi_in_vp0 { status = "okay"; };
&hdmi_in_vp1 { status = "disabled"; };
&route_hdmi { status = "okay"; connect = <&vp0_out_hdmi>; };

// MIPI DSI0 走 VP1
&dsi0_in_vp0 { status = "disabled"; };
&dsi0_in_vp1 { status = "okay"; };
&route_dsi0 { status = "okay"; connect = <&vp1_out_dsi0>; };
&video_phy0 { status = "okay"; };
```

### 双 MIPI 双屏

```dts
// DSI0 走 VP0
&dsi0_in_vp0 { status = "okay"; };
&dsi0_in_vp1 { status = "disabled"; };
&route_dsi0 { status = "okay"; connect = <&vp0_out_dsi0>; };
&video_phy0 { status = "okay"; };

// DSI1 走 VP1
&dsi1_in_vp0 { status = "disabled"; };
&dsi1_in_vp1 { status = "okay"; };
&route_dsi1 { status = "okay"; connect = <&vp1_out_dsi1>; };
&video_phy1 { status = "okay"; };
```

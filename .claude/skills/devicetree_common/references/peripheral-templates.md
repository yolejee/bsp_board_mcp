# 通用外设 DTS 节点模板

本文件包含常见外设的设备树节点模板，适用于所有 Linux 嵌入式平台。
模板中的 GPIO bank、时钟 ID、pinctrl 配置需根据具体 SoC 平台替换。

## 目录

- [通用外设 DTS 节点模板](#通用外设-dts-节点模板)
  - [目录](#目录)
  - [GPIO LED](#gpio-led)
  - [GPIO Keys](#gpio-keys)
  - [固定电压 Regulator](#固定电压-regulator)
  - [I2C 总线与设备](#i2c-总线与设备)
  - [SPI 总线与设备](#spi-总线与设备)
  - [UART](#uart)
  - [以太网 Ethernet](#以太网-ethernet)
  - [eMMC / SD 卡](#emmc--sd-卡)
    - [eMMC](#emmc)
    - [SD 卡](#sd-卡)
  - [PWM 与 PWM 背光/风扇](#pwm-与-pwm-背光风扇)
  - [USB](#usb)
  - [PCIe](#pcie)
  - [MIPI DSI 屏幕](#mipi-dsi-屏幕)
  - [HDMI](#hdmi)
  - [音频 (I2S + Codec)](#音频-i2s--codec)
  - [固定时钟](#固定时钟)
  - [Watchdog](#watchdog)
  - [display-timings 像素时钟计算](#display-timings-像素时钟计算)

---

## GPIO LED

```dts
leds {
    compatible = "gpio-leds";

    heartbeat {
        label = "board:green:heartbeat";
        gpios = <&gpio1 5 GPIO_ACTIVE_HIGH>;
        linux,default-trigger = "heartbeat";
        default-state = "on";
    };

    user {
        label = "board:blue:user";
        gpios = <&gpio1 6 GPIO_ACTIVE_LOW>;
        linux,default-trigger = "none";
    };
};
```

## GPIO Keys

```dts
gpio-keys {
    compatible = "gpio-keys";
    autorepeat;

    power {
        label = "Power Button";
        linux,code = <KEY_POWER>;
        gpios = <&gpio0 5 GPIO_ACTIVE_LOW>;
        debounce-interval = <100>;
        wakeup-source;
    };

    volume-up {
        label = "Volume Up";
        linux,code = <KEY_VOLUMEUP>;
        gpios = <&gpio0 6 GPIO_ACTIVE_LOW>;
    };
};
```

## 固定电压 Regulator

```dts
reg_3v3: regulator-3v3 {
    compatible = "regulator-fixed";
    regulator-name = "vcc3v3";
    regulator-min-microvolt = <3300000>;
    regulator-max-microvolt = <3300000>;
    regulator-always-on;
    regulator-boot-on;
    // 可选：GPIO 控制使能
    gpio = <&gpio2 6 GPIO_ACTIVE_HIGH>;
    enable-active-high;
    vin-supply = <&reg_5v>;  // 输入电源链
};
```

## I2C 总线与设备

```dts
&i2c0 {
    status = "okay";
    clock-frequency = <400000>;   // 100000 / 400000 / 1000000
    pinctrl-names = "default";
    pinctrl-0 = <&i2c0_pins>;

    // 温湿度传感器
    sht3x@44 {
        compatible = "sensirion,sht3x";
        reg = <0x44>;
    };

    // RTC
    rtc@68 {
        compatible = "dallas,ds1307";
        reg = <0x68>;
        interrupt-parent = <&gpio1>;
        interrupts = <3 IRQ_TYPE_EDGE_FALLING>;
    };

    // 触摸屏
    touchscreen@5d {
        compatible = "goodix,gt911";
        reg = <0x5d>;
        interrupt-parent = <&gpio3>;
        interrupts = <1 IRQ_TYPE_LEVEL_LOW>;
        reset-gpios = <&gpio3 2 GPIO_ACTIVE_LOW>;
        irq-gpios = <&gpio3 1 GPIO_ACTIVE_HIGH>;
        touchscreen-inverted-x;
        touchscreen-inverted-y;
    };
};
```

⚠️ I2C 地址在 DTS 中使用 **7 位**格式。如果 datasheet 给的是 8 位地址 (如 0xBA)，需右移 1 位 (0x5D)。

## SPI 总线与设备

```dts
&spi0 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&spi0_pins &spi0_cs0>;
    cs-gpios = <&gpio0 10 GPIO_ACTIVE_LOW>;

    flash@0 {
        compatible = "jedec,spi-nor";
        reg = <0>;
        spi-max-frequency = <50000000>;
        #address-cells = <1>;
        #size-cells = <1>;

        partition@0 {
            label = "bootloader";
            reg = <0x0 0x100000>;
        };
    };
};
```

## UART

```dts
&uart1 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&uart1_pins>;
    // 可选硬件流控
    // uart-has-rtscts;
};
```

## 以太网 Ethernet

```dts
&ethernet0 {
    status = "okay";
    phy-mode = "rgmii-id";      // rgmii / rgmii-id / rgmii-rxid / rgmii-txid / rmii
    phy-handle = <&phy0>;
    pinctrl-names = "default";
    pinctrl-0 = <&rgmii_pins>;

    mdio {
        #address-cells = <1>;
        #size-cells = <0>;

        phy0: ethernet-phy@0 {
            compatible = "ethernet-phy-ieee802.3-c22";
            reg = <0>;           // PHY MDIO 地址
            reset-gpios = <&gpio4 0 GPIO_ACTIVE_LOW>;
            reset-assert-us = <10000>;
            reset-deassert-us = <50000>;
        };
    };
};
```

## eMMC / SD 卡

### eMMC

```dts
&sdhci0 {
    status = "okay";
    bus-width = <8>;
    non-removable;
    cap-mmc-highspeed;
    mmc-hs200-1_8v;
    // mmc-hs400-1_8v;
    // mmc-hs400-enhanced-strobe;
    vmmc-supply = <&reg_3v3>;
    vqmmc-supply = <&reg_1v8>;
};
```

### SD 卡

```dts
&sdmmc {
    status = "okay";
    bus-width = <4>;
    cap-sd-highspeed;
    sd-uhs-sdr50;
    sd-uhs-sdr104;
    disable-wp;
    vmmc-supply = <&reg_3v3>;
    vqmmc-supply = <&reg_vccio_sd>;
    cd-gpios = <&gpio0 7 GPIO_ACTIVE_LOW>;  // 卡检测
    pinctrl-names = "default";
    pinctrl-0 = <&sdmmc_bus4 &sdmmc_clk &sdmmc_cmd &sdmmc_cd>;
};
```

## PWM 与 PWM 背光/风扇

```dts
&pwm2 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&pwm2_pin>;
};

// PWM 背光
backlight: backlight {
    compatible = "pwm-backlight";
    pwms = <&pwm2 0 25000 0>;  // <控制器 通道 周期ns 极性>
    brightness-levels = <0 4 8 16 32 64 128 255>;
    default-brightness-level = <6>;
    power-supply = <&reg_3v3>;
};

// PWM 风扇
fan: pwm-fan {
    compatible = "pwm-fan";
    pwms = <&pwm0 0 50000 0>;
    cooling-levels = <0 102 170 230 255>;
    #cooling-cells = <2>;
};
```

## USB

```dts
// USB 2.0 Host
&usb_host {
    status = "okay";
    phys = <&usb2phy_host>;
    phy-names = "usb2-phy";
};

// USB OTG / DRD
&usb_otg {
    status = "okay";
    dr_mode = "otg";  // "host" / "peripheral" / "otg"
};
```

## PCIe

```dts
&pcie {
    status = "okay";
    reset-gpios = <&gpio2 6 GPIO_ACTIVE_HIGH>;
    vpcie3v3-supply = <&reg_pcie_3v3>;
    // num-lanes = <1>;
    // max-link-speed = <2>;  // Gen2
};
```

## MIPI DSI 屏幕

```dts
&dsi {
    status = "okay";

    panel@0 {
        compatible = "simple-panel-dsi";
        reg = <0>;
        backlight = <&backlight>;
        power-supply = <&reg_lcd>;
        reset-gpios = <&gpio3 4 GPIO_ACTIVE_LOW>;

        enable-delay-ms = <35>;
        prepare-delay-ms = <6>;
        reset-delay-ms = <10>;
        init-delay-ms = <20>;

        dsi,flags = <(MIPI_DSI_MODE_VIDEO | MIPI_DSI_MODE_VIDEO_BURST
                    | MIPI_DSI_MODE_LPM | MIPI_DSI_MODE_EOT_PACKET)>;
        dsi,format = <MIPI_DSI_FMT_RGB888>;
        dsi,lanes = <4>;

        panel-init-sequence = [
            // 由屏幕供应商提供
        ];

        display-timings {
            native-mode = <&timing0>;
            timing0: timing0 {
                clock-frequency = <148500000>;
                hactive = <1920>;
                vactive = <1080>;
                hsync-len = <44>;
                hback-porch = <148>;
                hfront-porch = <88>;
                vsync-len = <5>;
                vback-porch = <36>;
                vfront-porch = <4>;
                hsync-active = <0>;
                vsync-active = <0>;
                de-active = <0>;
                pixelclk-active = <0>;
            };
        };

        port {
            panel_in: endpoint {
                remote-endpoint = <&dsi_out>;
            };
        };
    };

    port {
        dsi_out: endpoint {
            remote-endpoint = <&panel_in>;
        };
    };
};
```

## HDMI

```dts
&hdmi {
    status = "okay";
};

// HDMI 音频
hdmi_sound: hdmi-sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "HDMI";
    simple-audio-card,format = "i2s";
    simple-audio-card,mclk-fs = <128>;

    simple-audio-card,cpu {
        sound-dai = <&i2s0>;
    };
    simple-audio-card,codec {
        sound-dai = <&hdmi>;
    };
};
```

## 音频 (I2S + Codec)

```dts
/ {
    sound {
        compatible = "simple-audio-card";
        simple-audio-card,name = "Board Audio";
        simple-audio-card,format = "i2s";
        simple-audio-card,mclk-fs = <256>;
        simple-audio-card,widgets =
            "Microphone", "Mic",
            "Headphone", "Headphone";
        simple-audio-card,routing =
            "Mic", "MICBIAS",
            "IN1_L", "Mic",
            "Headphone", "HPL",
            "Headphone", "HPR";

        simple-audio-card,cpu {
            sound-dai = <&i2s1>;
        };
        simple-audio-card,codec {
            sound-dai = <&codec>;
        };
    };
};
```

## 固定时钟

```dts
osc_26m: oscillator-26m {
    compatible = "fixed-clock";
    #clock-cells = <0>;
    clock-frequency = <26000000>;
    clock-output-names = "osc_26m";
};
```

## Watchdog

```dts
&wdt {
    status = "okay";
    timeout-sec = <30>;
};
```

## display-timings 像素时钟计算

```
pixel_clock = H_total × V_total × refresh_rate

H_total = hactive + hsync-len + hback-porch + hfront-porch
V_total = vactive + vsync-len + vback-porch + vfront-porch

例 (1920x1080@60Hz):
H_total = 1920 + 44 + 148 + 88 = 2200
V_total = 1080 + 5 + 36 + 4 = 1125
pixel_clock = 2200 × 1125 × 60 = 148,500,000 Hz
```

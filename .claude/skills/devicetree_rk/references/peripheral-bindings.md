# 常见外设 DTS 绑定属性参考

## I2C 控制器与设备

### I2C 控制器
```dts
&i2c1 {
    status = "okay";
    clock-frequency = <400000>;  // 标准: 100000, 快速: 400000, 高速: 1000000
    pinctrl-names = "default";
    pinctrl-0 = <&i2c1m0_xfer>;  // mux 组选择
};
```

### I2C 设备通用属性
| 属性 | 必须 | 说明 |
|------|------|------|
| `compatible` | 是 | 驱动匹配字符串 |
| `reg` | 是 | I2C 从设备地址 (7位) |
| `interrupt-parent` | 否 | 中断控制器 phandle |
| `interrupts` | 否 | 中断描述 |
| `*-supply` | 否 | 电源 regulator |
| `*-gpios` | 否 | GPIO 引脚 |

### 常见 I2C 设备 compatible

| 设备类型 | compatible | 典型地址 |
|----------|-----------|---------|
| GT911 触摸屏 | `"goodix,gt911"` | 0x5d 或 0x14 |
| GT928 触摸屏 | `"goodix,gt928"` | 0x5d |
| FT5x06 触摸屏 | `"edt,edt-ft5406"` | 0x38 |
| RK809 PMIC | `"rockchip,rk809"` | 0x20 |
| RK817 PMIC | `"rockchip,rk817"` | 0x20 |
| TCS4525 调压器 | `"tcs,tcs452x"` | 0x1c |
| OV5648 摄像头 | `"ovti,ov5648"` | 0x36 |
| OV5647 摄像头 | `"ovti,ov5647"` | 0x36 |
| OV8858 摄像头 | `"ovti,ov8858"` | 0x36 |
| DW9714 VCM | `"dongwoon,dw9714"` | 0x0c |
| DS1307 RTC | `"dallas,ds1307"` | 0x68 |
| PCF8563 RTC | `"nxp,pcf8563"` | 0x51 |
| AT24C32 EEPROM | `"atmel,24c32"` | 0x50 |

## SPI 控制器与设备

### SPI 控制器
```dts
&spi1 {
    status = "okay";
    max-freq = <48000000>;
    pinctrl-names = "default";
    pinctrl-0 = <&spi1m1_cs0 &spi1m1_pins>;
    // dma-names = "tx", "rx";  // 启用 DMA
};
```

### SPI 设备通用属性
| 属性 | 必须 | 说明 |
|------|------|------|
| `compatible` | 是 | 驱动匹配 |
| `reg` | 是 | 片选编号 (0, 1, ...) |
| `spi-max-frequency` | 是 | 最大 SPI 时钟频率 (Hz) |
| `spi-cpha` | 否 | 时钟相位 |
| `spi-cpol` | 否 | 时钟极性 |
| `spi-cs-high` | 否 | 片选高有效 |

## UART

```dts
&uart3 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&uart3m1_xfer>;           // 基本收发
    // pinctrl-0 = <&uart3m1_xfer &uart3m1_ctsn &uart3m1_rtsn>;  // 带硬件流控
};
```

### Rockchip UART mux 映射 (RK3566/RK3568)

| UART | m0 引脚 | m1 引脚 | 备注 |
|------|---------|---------|------|
| uart0 | GPIO0_C1/C0 | — | 通常不用 |
| uart1 | GPIO2_PB4/B5 | — | — |
| uart2 | GPIO0_D1/D0 | — | 默认 Debug |
| uart3 | GPIO1_A1/A0 | GPIO3_PB7/C0 | 双 mux |
| uart4 | GPIO1_A6/A4 | GPIO3_PB1/B2 | 双 mux |
| uart5 | GPIO2_PA6/A5 | GPIO3_PC2/PC3 | 双 mux |
| uart7 | GPIO2_PA2/A3 | GPIO4_PA2/PA3 | 双 mux |
| uart8 | GPIO2_PA4/A6 | GPIO3_PD4/PD5 | 双 mux |
| uart9 | GPIO2_PA0/A1 | GPIO4_PC5/PC6 | 双 mux |

## PWM

```dts
&pwm4 {
    status = "okay";
    pinctrl-names = "active";
    pinctrl-0 = <&pwm4_pins>;
};

// 用作背光
backlight: backlight {
    compatible = "pwm-backlight";
    pwms = <&pwm4 0 25000 0>;
    // 参数: <&控制器 通道 周期(ns) 极性>
    brightness-levels = <0 1 2 ... 255>;
    default-brightness-level = <200>;
};

// 用作风扇
fan: fan {
    compatible = "pwm-fan";
    pwms = <&pwm0 0 50000 0>;
    cooling-levels = <0 50 100 150 200 255>;
};
```

## GPIO

### GPIO 属性格式
```dts
gpios = <&gpioX PIN_MACRO FLAGS>;
// gpioX: gpio0 ~ gpio4
// PIN_MACRO: RK_PA0 ~ RK_PD7 (见 dt-bindings/pinctrl/rockchip.h)
// FLAGS: GPIO_ACTIVE_HIGH (0) 或 GPIO_ACTIVE_LOW (1)
```

### GPIO 用作中断
```dts
interrupt-parent = <&gpio3>;
interrupts = <RK_PA1 IRQ_TYPE_LEVEL_LOW>;
// IRQ 类型: IRQ_TYPE_LEVEL_LOW, IRQ_TYPE_LEVEL_HIGH
//           IRQ_TYPE_EDGE_RISING, IRQ_TYPE_EDGE_FALLING, IRQ_TYPE_EDGE_BOTH
```

### GPIO LED
```dts
leds {
    compatible = "gpio-leds";
    led0 {
        gpios = <&gpio0 RK_PC5 GPIO_ACTIVE_LOW>;
        linux,default-trigger = "heartbeat";
        // 可选 trigger: "heartbeat", "timer", "default-on", "none",
        //              "mmc0", "mmc1", "cpu", "activity"
    };
};
```

### GPIO Keys
```dts
gpio-keys {
    compatible = "gpio-keys";
    power-key {
        label = "Power";
        gpios = <&gpio0 RK_PA5 GPIO_ACTIVE_LOW>;
        linux,code = <KEY_POWER>;
        debounce-interval = <100>;
        wakeup-source;
    };
};
```

## 时钟 (Clock)

### 固定时钟
```dts
ext_26m: external-26m-clock {
    compatible = "fixed-clock";
    #clock-cells = <0>;
    clock-frequency = <26000000>;
    clock-output-names = "ext_26m";
};
```

### assigned-clocks (时钟重新配置)
```dts
&gmac1 {
    assigned-clocks = <&cru SCLK_GMAC1_RX_TX>, <&cru SCLK_GMAC1>;
    assigned-clock-parents = <&cru SCLK_GMAC1_RGMII_SPEED>;
    assigned-clock-rates = <0>, <125000000>;
};
```

## 电源管理 (Regulator)

### 固定电压调节器
```dts
vcc3v3: vcc3v3-regulator {
    compatible = "regulator-fixed";
    regulator-name = "vcc3v3";
    regulator-min-microvolt = <3300000>;
    regulator-max-microvolt = <3300000>;
    regulator-always-on;
    regulator-boot-on;
    vin-supply = <&vcc5v0>;      // 输入电源
    enable-active-high;           // GPIO 使能极性
    gpio = <&gpio2 RK_PB6 GPIO_ACTIVE_HIGH>;
    startup-delay-us = <5000>;    // 启动延时
};
```

### PMIC 可调节器
```dts
regulators {
    vdd_logic: DCDC_REG1 {
        regulator-always-on;
        regulator-boot-on;
        regulator-min-microvolt = <500000>;
        regulator-max-microvolt = <1350000>;
        regulator-init-microvolt = <900000>;
        regulator-ramp-delay = <6001>;
        regulator-initial-mode = <0x2>;  // PWM 模式
        regulator-name = "vdd_logic";
        regulator-state-mem {
            regulator-off-in-suspend;     // 休眠时关闭
        };
    };
};
```

## 网络 (Ethernet)

### RGMII 模式
```dts
&gmac1 {
    phy-mode = "rgmii";
    clock_in_out = "output";     // SoC 输出时钟给 PHY

    snps,reset-gpio = <&gpio4 RK_PC0 GPIO_ACTIVE_LOW>;
    snps,reset-active-low;
    snps,reset-delays-us = <0 100000 100000>;  // 前延时 拉低时间 后延时

    tx_delay = <0x16>;           // 需根据 PCB 信号完整性调试
    rx_delay = <0x06>;

    phy-handle = <&rgmii_phy>;
    status = "okay";
};

&mdio1 {
    rgmii_phy: phy@0 {
        compatible = "ethernet-phy-ieee802.3-c22";
        reg = <0x0>;             // PHY 地址 (MDIO)
    };
};
```

### RMII 模式
```dts
&gmac1 {
    phy-mode = "rmii";
    clock_in_out = "output";
    phy-handle = <&rmii_phy>;
    status = "okay";
};
```

## USB

### USB 2.0
```dts
// PHY
&usb2phy0 { status = "okay"; };
&u2phy0_host { status = "okay"; };
&u2phy0_otg {
    status = "okay";
    // rockchip,vbus-always-on;  // OTG 始终提供 VBUS
};

// 控制器
&usb_host0_ehci { status = "okay"; };  // USB 2.0
&usb_host0_ohci { status = "okay"; };  // USB 1.1

// OTG (USB 2.0 only on RK3566)
&usbdrd_dwc3 {
    dr_mode = "otg";  // "host" / "peripheral" / "otg"
    status = "okay";
};
```

### USB 3.0
```dts
&combphy1_usq { status = "okay"; };  // Combo PHY
&usbhost30 { status = "okay"; };
&usbhost_dwc3 {
    dr_mode = "host";
    status = "okay";
};
```

### USB 电源控制
```dts
vcc5v0_usb: vcc5v0-usb-regulator {
    compatible = "regulator-fixed";
    enable-active-high;
    gpio = <&gpio2 RK_PB6 GPIO_ACTIVE_HIGH>;
    regulator-name = "vcc5v0_usb";
    regulator-always-on;
};
```

## PCIe

```dts
// PCIe 2.0 x1 (RK3566)
&combphy2_psq { status = "okay"; };  // Combo PHY

&pcie2x1 {
    reset-gpios = <&gpio0 RK_PB6 GPIO_ACTIVE_HIGH>;
    vpcie3v3-supply = <&pcie2_3v3>;
    status = "okay";
};

// PCIe 3.0 x2 (RK3568)
&pcie30phy { status = "okay"; };
&pcie3x2 {
    reset-gpios = <&gpio2 RK_PD6 GPIO_ACTIVE_HIGH>;
    vpcie3v3-supply = <&pcie30_3v3>;
    status = "okay";
};
```

## SATA

```dts
&combphy1_usq { status = "okay"; };  // 与 USB3 互斥

&sata1 {
    status = "okay";
};
```

## WiFi / BT (SDIO)

```dts
&sdmmc1 {
    max-frequency = <150000000>;
    supports-sdio;
    bus-width = <4>;
    disable-wp;
    cap-sd-highspeed;
    cap-sdio-irq;
    keep-power-in-suspend;
    pinctrl-names = "default";
    pinctrl-0 = <&sdmmc1_bus4 &sdmmc1_cmd &sdmmc1_clk>;
    sd-uhs-sdr104;
    status = "okay";
};

// 蓝牙 UART
&uart1 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&uart1m0_xfer &uart1m0_ctsn>;
};
```

## eMMC / SD 卡

### eMMC
```dts
&sdhci {
    bus-width = <8>;
    supports-emmc;
    non-removable;
    max-frequency = <200000000>;
    status = "okay";
};
```

### SD 卡
```dts
&sdmmc0 {
    bus-width = <4>;
    cap-mmc-highspeed;
    cap-sd-highspeed;
    disable-wp;
    sd-uhs-sdr104;
    vqmmc-supply = <&vccio_sd>;
    pinctrl-names = "default";
    pinctrl-0 = <&sdmmc0_bus4 &sdmmc0_clk &sdmmc0_cmd &sdmmc0_det>;
    status = "okay";
};
```

## Thermal / DVFS

```dts
&cpu0 {
    cpu-supply = <&vdd_cpu>;
};

&gpu {
    mali-supply = <&vdd_gpu>;
    status = "okay";
};

// BUS/NPU/RKVDEC 频率调节
&dfi { status = "okay"; };
&dmc {
    center-supply = <&vdd_logic>;
    status = "okay";
};

&rknpu {
    rknpu-supply = <&vdd_npu>;
    status = "okay";
};
```

## 音频 (I2S + Codec)

### 板载 Codec (RK809 内置)
```dts
/ {
    rk809_sound: rk809-sound {
        compatible = "simple-audio-card";
        simple-audio-card,format = "i2s";
        simple-audio-card,name = "rockchip,rk809-codec";
        simple-audio-card,mclk-fs = <256>;
        simple-audio-card,widgets =
            "Microphone", "Mic Jack",
            "Headphone", "Headphone Jack";
        simple-audio-card,routing =
            "Mic Jack", "MICBIAS1",
            "IN1P", "Mic Jack",
            "Headphone Jack", "HPOL",
            "Headphone Jack", "HPOR";

        simple-audio-card,cpu {
            sound-dai = <&i2s1_8ch>;
        };
        simple-audio-card,codec {
            sound-dai = <&rk809_codec>;
        };
    };
};
```

### 耳机检测
```dts
rk_headset: rk-headset {
    compatible = "rockchip_headset";
    headset_gpio = <&gpio0 RK_PC1 GPIO_ACTIVE_HIGH>;
    pinctrl-names = "default";
    pinctrl-0 = <&hp_det>;
    io-channels = <&saradc 1>;
};
```

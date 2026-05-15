# 多平台 pinctrl Binding 对比参考

设备树中 pinctrl (引脚复用控制) 的语法和属性名称因 SoC 厂商不同而差异很大。本文档汇总主流平台的 pinctrl binding 写法，帮助跨平台开发。

---

## 1. 通用框架

所有平台在设备节点中引用 pinctrl 的方式是统一的：

```dts
&uart0 {
    pinctrl-names = "default", "sleep";  // 状态名
    pinctrl-0 = <&uart0_default>;        // default 状态引用
    pinctrl-1 = <&uart0_sleep>;          // sleep 状态引用
    status = "okay";
};
```

差异只在于 pinctrl 组自身的定义方式。

---

## 2. Rockchip

**文件位置：** `arch/arm64/boot/dts/rockchip/rkXXX-pinctrl.dtsi`

```dts
&pinctrl {
    uart0 {
        uart0_xfer: uart0-xfer {
            rockchip,pins =
                // <bank pin_num function &pull_config>
                <2 RK_PA1 1 &pcfg_pull_up>,     // TX
                <2 RK_PA0 1 &pcfg_pull_up>;      // RX
        };

        uart0_cts: uart0-cts {
            rockchip,pins =
                <2 RK_PA2 1 &pcfg_pull_none>;
        };
    };

    i2c0 {
        i2c0_xfer: i2c0-xfer {
            rockchip,pins =
                <0 RK_PB1 1 &pcfg_pull_none>,
                <0 RK_PB2 1 &pcfg_pull_none>;
        };
    };
};
```

**关键：**
- `rockchip,pins` 属性
- 格式：`<bank pin function &config_phandle>`
- pin 用 `RK_PAx` ~ `RK_PDx` 宏
- function 数字对应复用功能 (0=GPIO, 1/2/3/...=复用功能)
- config phandle 引用预定义的 `pcfg_pull_xxx` / `pcfg_output_xxx`

---

## 3. 全志 Allwinner

**文件位置：** SoC dtsi 中 `&pio` 节点

```dts
&pio {
    uart0_ph_pins: uart0-ph-pins {
        pins = "PH0", "PH1";
        function = "uart0";
    };

    i2c0_pins: i2c0-pins {
        pins = "PI5", "PI6";
        function = "i2c0";
        bias-pull-up;
    };

    mmc0_pins: mmc0-pins {
        pins = "PF0", "PF1", "PF2", "PF3", "PF4", "PF5";
        function = "mmc0";
        drive-strength = <30>;
        bias-pull-up;
    };
};
```

**关键：**
- `pins` = 引脚名称字符串 (PXN 格式)
- `function` = 复用功能名称字符串
- 标准 pinconf 属性：`bias-pull-up`, `bias-pull-down`, `drive-strength` 等
- 前缀 P 后面是 port 字母和引脚号

---

## 4. NXP i.MX

**文件位置：** SoC dtsi 中 `&iomuxc` 节点

```dts
&iomuxc {
    pinctrl_uart1: uart1grp {
        fsl,pins = <
            MX8MQ_IOMUXC_UART1_RXD_UART1_DCE_RX  0x140
            MX8MQ_IOMUXC_UART1_TXD_UART1_DCE_TX  0x140
        >;
    };

    pinctrl_i2c1: i2c1grp {
        fsl,pins = <
            MX8MQ_IOMUXC_I2C1_SCL_I2C1_SCL  0x400001c3
            MX8MQ_IOMUXC_I2C1_SDA_I2C1_SDA  0x400001c3
        >;
    };

    pinctrl_usdhc1: usdhc1grp {
        fsl,pins = <
            MX8MQ_IOMUXC_SD1_CLK_USDHC1_CLK       0x83
            MX8MQ_IOMUXC_SD1_CMD_USDHC1_CMD       0xc3
            MX8MQ_IOMUXC_SD1_DATA0_USDHC1_DATA0   0xc3
            MX8MQ_IOMUXC_SD1_DATA1_USDHC1_DATA1   0xc3
            MX8MQ_IOMUXC_SD1_DATA2_USDHC1_DATA2   0xc3
            MX8MQ_IOMUXC_SD1_DATA3_USDHC1_DATA3   0xc3
        >;
    };
};
```

**关键：**
- `fsl,pins` 属性
- 每行：`<MUX_PAD_CTRL_MACRO  pad_config_value>`
- mux 宏 = `MX{series}_IOMUXC_{PAD_NAME}_{FUNCTION}`
- pad_config_value 是位字段 (drive/pull/slew/...)，查芯片手册

---

## 5. TI (AM335x / AM62x / Sitara)

### AM335x

```dts
&am33xx_pinmux {
    uart0_pins: uart0-pins {
        pinctrl-single,pins = <
            AM33XX_PADCONF(AM335X_PIN_UART0_RXD, PIN_INPUT_PULLUP, MUX_MODE0)
            AM33XX_PADCONF(AM335X_PIN_UART0_TXD, PIN_OUTPUT_PULLDOWN, MUX_MODE0)
        >;
    };

    i2c0_pins: i2c0-pins {
        pinctrl-single,pins = <
            AM33XX_PADCONF(AM335X_PIN_I2C0_SDA, PIN_INPUT_PULLUP, MUX_MODE0)
            AM33XX_PADCONF(AM335X_PIN_I2C0_SCL, PIN_INPUT_PULLUP, MUX_MODE0)
        >;
    };
};
```

### AM62x

```dts
&main_pmx0 {
    main_uart0_pins_default: main-uart0-default-pins {
        pinctrl-single,pins = <
            AM62X_IOPAD(0x01c8, PIN_INPUT, 0)   /* UART0_RXD */
            AM62X_IOPAD(0x01cc, PIN_OUTPUT, 0)   /* UART0_TXD */
        >;
    };
};
```

**关键：**
- 使用 `pinctrl-single` 驱动
- `pinctrl-single,pins` 属性
- 每行：`<offset config_value>`
- TI 提供宏来简化：`AM33XX_PADCONF()`, `AM62X_IOPAD()` 等
- `MUX_MODE0` ~ `MUX_MODE7` 表示复用功能

---

## 6. Qualcomm

```dts
&tlmm {
    uart0_default: uart0-default-state {
        tx-pins {
            pins = "gpio0";
            function = "qup0";
            drive-strength = <2>;
            bias-disable;
        };

        rx-pins {
            pins = "gpio1";
            function = "qup0";
            drive-strength = <2>;
            bias-pull-up;
        };
    };

    i2c1_default: i2c1-default-state {
        pins = "gpio2", "gpio3";
        function = "qup1";
        drive-strength = <2>;
        bias-pull-up;
    };
};
```

**关键：**
- 使用 `&tlmm` (Top Level Mode Mux) 节点
- `pins = "gpioN"` 引脚名
- `function` = 复用功能名
- 可以用子节点分组 (tx-pins, rx-pins)
- 标准 pinconf 属性

---

## 7. Samsung Exynos

```dts
&pinctrl_0 {
    uart0_data: uart0-data-pins {
        samsung,pins = "gpa0-0", "gpa0-1";
        samsung,pin-function = <EXYNOS_PIN_FUNC_2>;
        samsung,pin-pud = <EXYNOS_PIN_PULL_NONE>;
        samsung,pin-drv = <EXYNOS5420_PIN_DRV_LV1>;
    };
};
```

**关键：**
- `samsung,pins` = 引脚名 (gpXY-N 格式)
- `samsung,pin-function` = 复用功能编号
- `samsung,pin-pud` = 上下拉
- `samsung,pin-drv` = 驱动强度

---

## 8. STM32MP

```dts
&pinctrl {
    uart4_pins_a: uart4-0 {
        pins1 {
            pinmux = <STM32_PINMUX('G', 11, AF6)>;  /* TX */
            bias-disable;
            drive-push-pull;
            slew-rate = <0>;
        };
        pins2 {
            pinmux = <STM32_PINMUX('B', 2, AF8)>;   /* RX */
            bias-disable;
        };
    };
};
```

**关键：**
- `pinmux = <STM32_PINMUX(port, pin, af)>`
- port 是字母 ('A' ~ 'K')
- af 是 Alternate Function 编号 (AF0 ~ AF15)
- 每组引脚用子节点 (pins1, pins2) 分别配置

---

## 9. Broadcom (Raspberry Pi)

```dts
&gpio {
    uart0_pins: uart0-pins {
        brcm,pins = <14 15>;
        brcm,function = <BCM2835_FSEL_ALT0>;
        brcm,pull = <BCM2835_PUD_OFF BCM2835_PUD_UP>;
    };

    i2c1_pins: i2c1-pins {
        brcm,pins = <2 3>;
        brcm,function = <BCM2835_FSEL_ALT0>;
    };
};
```

**关键：**
- `brcm,pins` = GPIO 编号
- `brcm,function` = 复用功能 (ALT0 ~ ALT5)
- `brcm,pull` = 上下拉配置

---

## 10. Xilinx / AMD Zynq

```dts
&pinctrl0 {
    pinctrl_uart0_default: uart0-default {
        mux {
            groups = "uart0_0_grp";
            function = "uart0";
        };

        conf {
            groups = "uart0_0_grp";
            slew-rate = <SLEW_RATE_SLOW>;
            power-source = <IO_STANDARD_LVCMOS33>;
        };
    };
};
```

**关键：**
- `groups` + `function` 模式
- 分 mux 和 conf 子节点
- Zynq UltraScale+ 使用不同的引脚控制器

---

## 11. RISC-V (StarFive JH71x0)

```dts
&sysgpio {
    uart0_pins: uart0-pins {
        tx-pin {
            starfive,pins = <PAD_GPIO5>;
            starfive,pinmux = <PAD_GPIO5_FUNC_SEL 0>;
            starfive,pin-ioconfig = <IO(GPIO_IE(1))>;
            starfive,pin-gpio-dout = <GPO_UART0_SOUT>;
            starfive,pin-gpio-doen = <OEN_LOW>;
        };

        rx-pin {
            starfive,pins = <PAD_GPIO6>;
            starfive,pinmux = <PAD_GPIO6_FUNC_SEL 0>;
            starfive,pin-ioconfig = <IO(GPIO_IE(1) | GPIO_PU(1))>;
            starfive,pin-gpio-din = <GPI_UART0_SIN>;
        };
    };
};
```

---

## 12. 快速查找表

| 平台 | pinctrl 节点 | 核心属性 | 引脚表示 |
|------|-------------|---------|---------|
| Rockchip | `&pinctrl` | `rockchip,pins` | `<bank RK_PXn func &config>` |
| Allwinner | `&pio` | `pins` + `function` | `"PXN"` 字符串 |
| NXP i.MX | `&iomuxc` | `fsl,pins` | 宏 + pad config |
| TI AM335x | `&am33xx_pinmux` | `pinctrl-single,pins` | `AM33XX_PADCONF()` |
| TI AM62x | `&main_pmx0` | `pinctrl-single,pins` | `AM62X_IOPAD()` |
| Qualcomm | `&tlmm` | `pins` + `function` | `"gpioN"` 字符串 |
| Samsung | `&pinctrl_0` | `samsung,pins` | `"gpXY-N"` |
| STM32MP | `&pinctrl` | `pinmux` | `STM32_PINMUX()` |
| Broadcom | `&gpio` | `brcm,pins` + `brcm,function` | GPIO 编号 |
| Xilinx | `&pinctrl0` | `groups` + `function` | 组名字符串 |
| StarFive | `&sysgpio` | `starfive,pins` etc. | `PAD_GPIOx` 宏 |

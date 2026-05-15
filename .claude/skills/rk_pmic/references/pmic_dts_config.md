# PMIC DTS 配置完整参考

本文档提供 Rockchip 各型号 PMIC 的完整 DTS 配置模板。

---

## 1. RK806 完整 DTS 模板 (RK3588, SPI, kernel 5.10)

### 1.1 单 PMIC 配置

```dts
&pinctrl {
    rk806 {
        rk806_dvs1_null: rk806_dvs1_null { rockchip,pins = <0 RK_PB1 RK_FUNC_GPIO &pcfg_pull_none>; };
        rk806_dvs2_null: rk806_dvs2_null { rockchip,pins = <0 RK_PB2 RK_FUNC_GPIO &pcfg_pull_none>; };
        rk806_dvs3_null: rk806_dvs3_null { rockchip,pins = <0 RK_PB3 RK_FUNC_GPIO &pcfg_pull_none>; };
    };
};

&spi2 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&spi2m0_csn0 &spi2m0_pins>;
    num-cs = <1>;

    rk806_master: rk806@0 {
        compatible = "rockchip,rk806";
        spi-max-frequency = <1000000>;      /* 1MHz SPI */
        reg = <0x0>;

        interrupt-parent = <&gpio0>;
        interrupts = <7 IRQ_TYPE_LEVEL_LOW>;
        pinctrl-names = "default";
        pinctrl-0 = <&rk806_dvs1_null>, <&rk806_dvs2_null>, <&rk806_dvs3_null>;

        /* 输入电源 */
        vcc1-supply = <&vcc5v0_sys>;
        vcc2-supply = <&vcc5v0_sys>;
        vcc3-supply = <&vcc5v0_sys>;
        vcc4-supply = <&vcc5v0_sys>;
        vcc5-supply = <&vcc5v0_sys>;
        vcc6-supply = <&vcc5v0_sys>;
        vcc7-supply = <&vcc5v0_sys>;
        vcc8-supply = <&vcc5v0_sys>;
        vcc9-supply = <&vcc5v0_sys>;
        vcc10-supply = <&vcc5v0_sys>;
        vcc11-supply = <&vcc5v0_sys>;
        vcc12-supply = <&vcc5v0_sys>;
        vcc13-supply = <&vcc5v0_sys>;
        vcc14-supply = <&vcc5v0_sys>;

        regulators {
            vdd_gpu_s0: DCDC_REG1 {
                regulator-always-on;
                regulator-boot-on;
                regulator-min-microvolt = <550000>;
                regulator-max-microvolt = <1050000>;
                regulator-ramp-delay = <12500>;
                regulator-name = "vdd_gpu_s0";
                regulator-state-mem {
                    regulator-off-in-suspend;
                };
            };
            vdd_cpu_lit_s0: DCDC_REG2 {
                regulator-always-on;
                regulator-boot-on;
                regulator-min-microvolt = <550000>;
                regulator-max-microvolt = <1150000>;
                regulator-ramp-delay = <12500>;
                regulator-name = "vdd_cpu_lit_s0";
                regulator-state-mem {
                    regulator-off-in-suspend;
                };
            };
            vdd_log_s0: DCDC_REG3 {
                regulator-always-on;
                regulator-boot-on;
                regulator-min-microvolt = <675000>;
                regulator-max-microvolt = <750000>;
                regulator-ramp-delay = <12500>;
                regulator-name = "vdd_log_s0";
                regulator-state-mem {
                    regulator-off-in-suspend;
                    regulator-suspend-microvolt = <750000>;
                };
            };
            /* DCDC_REG4 ~ DCDC_REG10: 按实际需求配置 */
            /* NLDO_REG1 ~ NLDO_REG5: 按实际需求配置 */
            /* PLDO_REG1 ~ PLDO_REG6: 按实际需求配置 */
        };
    };
};
```

### 1.2 双 PMIC 配置 (Master + Slave)

```dts
&spi2 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&spi2m0_csn0 &spi2m0_csn1 &spi2m0_pins>;
    num-cs = <2>;          /* 两个片选 */

    rk806_master: rk806@0 {
        compatible = "rockchip,rk806";
        spi-max-frequency = <1000000>;
        reg = <0x0>;       /* CS0 = Master */
        /* ... interrupt, pinctrl, vcc supplies ... */
        regulators { /* Master 侧 regulator */ };
    };

    rk806_slave: rk806@1 {
        compatible = "rockchip,rk806";
        spi-max-frequency = <1000000>;
        reg = <0x1>;       /* CS1 = Slave */
        /* ... interrupt, pinctrl, vcc supplies ... */
        regulators { /* Slave 侧 regulator */ };
    };
};
```

**关键点：**
- Master 通过 EXT_EN 控制 Slave 上下电时序
- 两片 RK806 的中断可共用同一 GPIO 或分开配置
- regulator-name 建议与原理图一致以区分 master/slave 侧

---

## 2. RK809 完整 DTS 模板 (RK3568/RK3566, I2C, kernel 4.4/4.19)

```dts
&pinctrl {
    pmic {
        pmic_int: pmic_int {
            rockchip,pins = <0 RK_PA7 RK_FUNC_GPIO &pcfg_pull_up>;
        };
        soc_slppin_gpio: soc_slppin_gpio {
            rockchip,pins = <0 RK_PA4 RK_FUNC_GPIO &pcfg_output_low>;
        };
        soc_slppin_slp: soc_slppin_slp {
            rockchip,pins = <0 RK_PA4 RK_FUNC_1 &pcfg_pull_none>;
        };
        soc_slppin_rst: soc_slppin_rst {
            rockchip,pins = <0 RK_PA4 RK_FUNC_2 &pcfg_pull_none>;
        };
    };
};

&i2c1 {
    status = "okay";
    rk809: pmic@20 {
        compatible = "rockchip,rk809";
        reg = <0x20>;
        interrupt-parent = <&gpio0>;
        interrupts = <7 IRQ_TYPE_LEVEL_LOW>;

        /* Sleep 引脚 4 种功能复用 */
        pinctrl-names = "default", "pmic-sleep", "pmic-power-off", "pmic-reset";
        pinctrl-0 = <&pmic_int>;
        pinctrl-1 = <&soc_slppin_slp>, <&rk817_slppin_slp>;
        pinctrl-2 = <&soc_slppin_gpio>, <&rk817_slppin_pwrdn>;
        pinctrl-3 = <&soc_slppin_rst>, <&rk817_slppin_rst>;

        rockchip,system-power-controller;
        wakeup-source;
        #clock-cells = <1>;
        clock-output-names = "rk808-clkout1", "rk808-clkout2";
        pmic-reset-func = <1>;  /* 1: rst regs (default), 0: rst the pmic */

        /* 输入电源 (vcc1~vcc9 对应 DCDC/LDO 输入) */
        vcc1-supply = <&vcc5v0_sys>;
        vcc2-supply = <&vcc5v0_sys>;
        vcc3-supply = <&vcc5v0_sys>;
        vcc4-supply = <&vcc5v0_sys>;
        vcc5-supply = <&vcc3v3_sys>;
        vcc6-supply = <&vcc3v3_sys>;
        vcc7-supply = <&vcc3v3_sys>;
        vcc8-supply = <&vcc3v3_sys>;
        vcc9-supply = <&vcc5v0_sys>;

        pwrkey { status = "okay"; };

        /* PMIC 内部 pinctrl (sleep 脚 4 功能) */
        pinctrl_rk8xx: pinctrl_rk8xx {
            gpio-controller;
            #gpio-cells = <2>;
            rk817_slppin_null: rk817_slppin_null { pins = "gpio_slp"; function = "pin_fun0"; };
            rk817_slppin_slp: rk817_slppin_slp   { pins = "gpio_slp"; function = "pin_fun1"; };
            rk817_slppin_pwrdn: rk817_slppin_pwrdn { pins = "gpio_slp"; function = "pin_fun2"; };
            rk817_slppin_rst: rk817_slppin_rst   { pins = "gpio_slp"; function = "pin_fun3"; };
        };

        regulators {
            vdd_logic: DCDC_REG1 {
                regulator-always-on;
                regulator-boot-on;
                regulator-min-microvolt = <950000>;
                regulator-max-microvolt = <1350000>;
                regulator-ramp-delay = <6001>;
                regulator-initial-mode = <0x2>;
                regulator-name = "vdd_logic";
                regulator-state-mem {
                    regulator-on-in-suspend;
                    regulator-suspend-microvolt = <950000>;
                };
            };
            vdd_arm: DCDC_REG2 {
                regulator-always-on;
                regulator-boot-on;
                regulator-min-microvolt = <950000>;
                regulator-max-microvolt = <1350000>;
                regulator-ramp-delay = <6001>;
                regulator-initial-mode = <0x2>;
                regulator-name = "vdd_arm";
                regulator-state-mem {
                    regulator-off-in-suspend;
                    regulator-suspend-microvolt = <950000>;
                };
            };
            vcc_ddr: DCDC_REG3 {
                regulator-always-on;
                regulator-boot-on;
                regulator-name = "vcc_ddr";
                /* DCDC3 电压只能通过外部电阻调节，不配 min/max */
                regulator-state-mem {
                    regulator-on-in-suspend;
                };
            };
            /* DCDC_REG4, DCDC_REG5, LDO_REG1 ~ LDO_REG9, SWITCH_REG1/2 按需配置 */
        };

        /* RK809 内置 CODEC (可选) */
        rk809_codec: codec {
            #sound-dai-cells = <0>;
            compatible = "rockchip,rk809-codec", "rockchip,rk817-codec";
            clocks = <&cru SCLK_I2S1_OUT>;
            clock-names = "mclk";
            pinctrl-names = "default";
            pinctrl-0 = <&i2s1_2ch_mclk>;
            hp-volume = <20>;
            spk-volume = <3>;
            status = "okay";
        };
    };
};
```

---

## 3. RK817 完整 DTS 模板 (RK3326/PX30, I2C, kernel 4.4/4.19)

与 RK809 结构几乎完全相同，差异点：
- `compatible = "rockchip,rk817";`
- RK817 额外含 battery 和 charger 子节点
- RK817 有 gpio_ts 和 gpio_gt 两个额外 GPIO 引脚

```dts
&i2c1 {
    status = "okay";
    rk817: pmic@20 {
        compatible = "rockchip,rk817";
        reg = <0x20>;
        /* ... interrupt, pinctrl 同 RK809 ... */

        /* RK817 额外 GPIO: ts 和 gt 引脚 */
        pinctrl_rk8xx: pinctrl_rk8xx {
            gpio-controller;
            #gpio-cells = <2>;
            rk817_ts_gpio1: rk817_ts_gpio1  { pins = "gpio_ts"; function = "pin_fun1"; };
            rk817_gt_gpio2: rk817_gt_gpio2  { pins = "gpio_gt"; function = "pin_fun1"; };
            rk817_pin_ts: rk817_pin_ts      { pins = "gpio_ts"; function = "pin_fun0"; };
            rk817_pin_gt: rk817_pin_gt      { pins = "gpio_gt"; function = "pin_fun0"; };
            /* sleep pin 4 功能同 RK809 */
            rk817_slppin_null: rk817_slppin_null { pins = "gpio_slp"; function = "pin_fun0"; };
            rk817_slppin_slp: rk817_slppin_slp   { pins = "gpio_slp"; function = "pin_fun1"; };
            rk817_slppin_pwrdn: rk817_slppin_pwrdn { pins = "gpio_slp"; function = "pin_fun2"; };
            rk817_slppin_rst: rk817_slppin_rst   { pins = "gpio_slp"; function = "pin_fun3"; };
        };

        regulators {
            /* DCDC_REG1 ~ DCDC_REG4, LDO_REG1 ~ LDO_REG9, BOOST, SWITCH 按需配置 */
        };

        /* 电池管理 (RK817 特有) */
        battery {
            compatible = "rk817,battery";
            ocv_table = <3500 3625 3685 3697 3718 3735 3748
                         3760 3774 3788 3802 3816 3834 3853
                         3877 3908 3946 3975 4018 4071 4106>;
            design_capacity = <2500>;       /* mAh */
            design_qmax = <2750>;
            bat_res = <100>;                /* mΩ */
            sleep_enter_current = <300>;
            sleep_exit_current = <300>;
            sleep_filter_current = <100>;
            power_off_thresd = <3500>;      /* 关机电压 mV */
            zero_algorithm_vol = <3850>;
            max_soc_offset = <60>;
            monitor_sec = <5>;
            sample_res = <10>;              /* 采样电阻 mΩ */
            virtual_power = <1>;            /* 1=虚拟电源(调试), 0=真实电池 */
        };

        /* 充电管理 (RK817 特有) */
        charger {
            compatible = "rk817,charger";
            min_input_voltage = <4500>;     /* mV */
            max_input_current = <1500>;     /* mA */
            max_chrg_current = <2000>;      /* mA */
            max_chrg_voltage = <4200>;      /* mV */
            chrg_term_mode = <0>;
            chrg_finish_cur = <300>;        /* mA */
            virtual_power = <0>;
            dc_det_adc = <0>;
            extcon = <&u2phy>;
        };

        /* CODEC (RK817 特有) */
        rk817_codec: codec {
            #sound-dai-cells = <0>;
            compatible = "rockchip,rk817-codec";
            clocks = <&cru SCLK_I2S1_OUT>;
            clock-names = "mclk";
            hp-volume = <20>;
            spk-volume = <3>;
            status = "okay";
        };
    };
};
```

---

## 4. RK808 完整 DTS 模板 (RK3399, I2C, kernel 4.4/4.19)

### 4.4/4.19 内核配置

```dts
&i2c1 {
    status = "okay";
    rk808: pmic@1b {
        compatible = "rockchip,rk808";
        reg = <0x1b>;
        interrupt-parent = <&gpio1>;
        interrupts = <21 IRQ_TYPE_LEVEL_LOW>;
        pinctrl-names = "default";
        pinctrl-0 = <&pmic_int_l &pmic_dvs2>;

        rockchip,system-power-controller;
        wakeup-source;
        #clock-cells = <1>;
        clock-output-names = "rk808-clkout1", "rk808-clkout2";

        vcc1-supply = <&vcc3v3_sys>;
        vcc2-supply = <&vcc3v3_sys>;
        vcc3-supply = <&vcc3v3_sys>;
        vcc4-supply = <&vcc3v3_sys>;
        vcc6-supply = <&vcc3v3_sys>;
        vcc7-supply = <&vcc3v3_sys>;
        vcc8-supply = <&vcc3v3_sys>;
        vcc9-supply = <&vcc3v3_sys>;
        vcc10-supply = <&vcc3v3_sys>;
        vcc11-supply = <&vcc3v3_sys>;
        vcc12-supply = <&vcc3v3_sys>;
        vddio-supply = <&vcc1v8_pmu>;

        regulators {
            vdd_log: DCDC_REG1 {
                regulator-always-on;
                regulator-boot-on;
                regulator-min-microvolt = <750000>;
                regulator-max-microvolt = <1350000>;
                regulator-ramp-delay = <6001>;
                regulator-name = "vdd_log";
                regulator-state-mem {
                    regulator-on-in-suspend;
                    regulator-suspend-microvolt = <900000>;
                };
            };
            vdd_cpu_l: DCDC_REG2 {
                regulator-always-on;
                regulator-boot-on;
                regulator-min-microvolt = <750000>;
                regulator-max-microvolt = <1350000>;
                regulator-ramp-delay = <6001>;
                regulator-name = "vdd_cpu_l";
                regulator-state-mem {
                    regulator-off-in-suspend;
                };
            };
            vcc_ddr: DCDC_REG3 {
                regulator-always-on;
                regulator-boot-on;
                regulator-name = "vcc_ddr";
                regulator-state-mem {
                    regulator-on-in-suspend;
                };
            };
            /* DCDC_REG4, LDO_REG1 ~ LDO_REG8, SWITCH_REG1/2 按需配置 */
        };
    };
};
```

### 3.10 内核配置 (旧版)

```dts
&i2c1 {
    rk808: rk808@1b {
        reg = <0x1b>;
        status = "okay";
    };
};
/include/ "rk808.dtsi"

&rk808 {
    gpios = <&gpio0 GPIO_A4 GPIO_ACTIVE_HIGH>,  /* pmic_int */
            <&gpio0 GPIO_B3 GPIO_ACTIVE_LOW>;   /* pmic_sleep */
    rk808,system-power-controller;
    regulators {
        rk808_dcdc1_reg: regulator@0 {
            regulator-always-on;
            regulator-boot-on;
            regulator-min-microvolt = <750000>;
            regulator-max-microvolt = <1400000>;
            regulator-init-microvolt = <1300000>;
            regulator-name = "vdd_arm";
            regulator-state-mem { regulator-off-in-suspend; };
        };
        /* ... */
    };
};
```

**注意：** 3.10 内核使用 `regulator-state-enabled/regulator-state-disabled` 和 `regulator-state-uv` 替代 4.4+ 的 `regulator-on-in-suspend/regulator-off-in-suspend` 和 `regulator-suspend-microvolt`。

---

## 5. CLK 引用方式

所有 RK8xx PMIC 都提供两个 32.768KHz 时钟输出，引用方式：

```dts
clocks = <&rk809 1>;
/* 第一个参数: &rk809 (对应 PMIC 节点标签)
 * 第二个参数: 0 = clkout1, 1 = clkout2
 */
```

---

## 6. GPIO 引用方式 (4.19 内核)

4.19 内核不再需要 gpio 子节点，但其他模块可直接引用 PMIC GPIO：

```dts
gpios = <&rk809 0 GPIO_ACTIVE_LOW>;
/* 第一个参数: PMIC 节点标签
 * 第二个参数: GPIO 引脚编号
 * 第三个参数: 极性
 */
```

---

## 7. Regulator DTS 属性完整参考

### 7.1 通用属性

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `regulator-name` | string | 推荐 | 电源名字，与原理图一致 |
| `regulator-compatible` | string | 驱动需要 | 驱动注册匹配名，不可改动 |
| `regulator-min-microvolt` | u32 | 是 | 运行时最小电压 (uV) |
| `regulator-max-microvolt` | u32 | 是 | 运行时最大电压 (uV) |
| `regulator-init-microvolt` | u32 | 否 | U-Boot 初始化电压 (kernel 忽略) |
| `regulator-always-on` | bool | 否 | 不允许关闭，注册时 enable |
| `regulator-boot-on` | bool | 否 | 注册时立即 enable |
| `regulator-initial-mode` | u32 | 否 | 运行时 DCDC 模式：1=PWM, 2=AUTO |
| `regulator-ramp-delay` | u32 | 否 | 电压变化速率 (uV/us)，通常 12500 |

### 7.2 休眠属性 (regulator-state-mem 子节点)

| 属性 | 类型 | 说明 |
|------|------|------|
| `regulator-on-in-suspend` | bool | 休眠保持上电 |
| `regulator-off-in-suspend` | bool | 休眠关闭 |
| `regulator-suspend-microvolt` | u32 | 休眠电压 (仅 on-in-suspend 有效) |
| `regulator-mode` | u32 | 休眠 DCDC 模式：1=PWM, 2=AUTO (一般 2) |
| `regulator-initial-state` | u32 | suspend 模式，必须 = 3 |

### 7.3 电压设置行为总结

| 条件 | 行为 |
|------|------|
| `min == max` | 注册时自动设置该电压并 enable |
| `min != max` + `boot-on` 或 `always-on` | enable，电压为硬件默认值 |
| `min != max` + 无 `boot-on` | 不自动 enable，需驱动调用 |

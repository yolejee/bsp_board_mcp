---
name: rk_pmic
description: "Rockchip 瑞芯微平台 PMIC 电源管理与 DVFS 调频调压技能。覆盖 RK806/RK809/RK817/RK808/RK805 等全系列 PMIC 的 regulator 配置、DTS 编写、电源树设计、休眠唤醒功耗管理，以及 CPUFreq/Devfreq/OPP Table 动态调频调压框架、功耗分析与优化。适用于 RK3588/RK3568/RK3566/RK3399/PX30 等全系列芯片。触发关键词：PMIC、电源管理、RK806、RK809、RK817、regulator、DCDC、LDO、BUCK、电源树、vdd_cpu、vdd_gpu、vdd_logic、vcc_ddr、regulator-always-on、regulator-state-mem、pmic_sleep、pwrkey、休眠电压、上电时序、CPUFreq、Devfreq、DVFS、OPP、opp-table、operating-points-v2、cpu-supply、governor、schedutil、定频测试、leakage、PVTM、功耗分析、功耗优化、电源纹波、regulator_summary、power domain。当用户在 Rockchip 平台遇到 PMIC 配置、电源供电、regulator 调试、DVFS 调频调压、功耗分析等问题时触发。"
---

# Rockchip PMIC 电源管理与 DVFS 技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| PMIC 芯片选型与对比 | §1 |
| PMIC 基础概念 | §2 |
| DTS 配置要点 | §3 |
| Regulator DTS 属性参考 | §4 |
| 内核驱动与 Menuconfig | §5 |
| Regulator 内核 API | §6 |
| CPUFreq 动态调频 | §7 |
| Devfreq 动态调频 | §8 |
| OPP Table 配置 | §9 |
| 功耗分析与优化 | §10 |
| 调试方法 | §11 |
| 常见故障排查 | §12 |

> **深度参考**：DTS 完整模板见 `references/pmic_dts_config.md`；DVFS 与功耗调优见 `references/dvfs_power_tuning.md`。

---

## 1. PMIC 芯片选型与对比

### 1.1 芯片一览表

| PMIC | 总线 | I2C 地址 | DCDC | LDO | 其他 | 典型搭配 SoC | 内核版本 |
|------|------|---------|------|-----|------|-------------|---------|
| RK806 | SPI (1MHz) | - | 10 | 5 NLDO + 6 PLDO | GPIO/Pinctrl | RK3588 | 5.10 |
| RK809 | I2C | 0x20 | 5 | 9 | 2 SWITCH + RTC + CODEC | RK3568/RK3566/PX30 | 4.4/4.19 |
| RK817 | I2C | 0x20 | 4 | 9 | SWITCH + BOOST + RTC + CODEC + 充电 + 库仑计 | RK3326/PX30 | 4.4/4.19 |
| RK808 | I2C | 0x1b | 4 | 8 | 2 SWITCH + RTC | RK3399/RK3288/RK3368 | 3.10/4.4/4.19 |
| RK805 | I2C | 0x18 | 4 | 3 | RTC | RK3328 | 4.4/4.19 |

### 1.2 DCDC 与 LDO 特性

| 类型 | 效率 | 纹波 | 成本 | 适用场景 |
|------|------|------|------|---------|
| DCDC | 高 (80%-90%) | 较大 | 高 | 大压差、大电流 (VDD_CPU, VDD_GPU, VCC_DDR) |
| LDO | 低 (= Vout/Vin) | 小 | 低 | 小电流、低噪声 (PLL, PHY, IO) |

- DCDC 两种模式：**PWM** (force PWM, 纹波好) / **PFM** (效率高, 负载能力差)
- 实际使用 **AUTO** 模式 = 动态切换 PWM/PFM；运行时 PWM，休眠时 AUTO

### 1.3 RK806 双 PMIC 架构 (RK3588)

RK3588 需要两片 RK806 (master + slave) 通过 SPI 通信：
- Master: SPI CS0 (`spi2@0`), 通过 EXT_EN 控制 Slave 上下电
- Slave: SPI CS1 (`spi2@1`)
- DTS 中分别配置 `rk806_master` 和 `rk806_slave`

---
## 2. PMIC 基础概念

### 2.1 三种工作模式

| 模式 | pmic_sleep 电平 | 说明 |
|------|----------------|------|
| Normal | 低 | 系统正常运行 |
| Sleep | 高 (配置为 sleep) | 降压/关闭部分电源以降低待机功耗 |
| Shutdown | 高 (配置为 shutdown) | 完成整个系统下电 |

### 2.2 关键引脚

| 引脚 | 功能 |
|------|------|
| pmic_sleep | 控制 sleep/shutdown 模式切换；RK809/RK817 支持 pinctrl 复用 (sleep/shutdown/reset/idle) |
| pmic_int | 中断输出，常态高，有中断时低 |
| pmic_pwron (PWRON) | 电源按键检测 |
| EN | 使能引脚，控制 PMIC 上电 |

### 2.3 上电条件

满足以下任一条件即可上电：
1. EN 信号从低→高
2. EN 高 + RTC 闹钟中断
3. EN 高 + PWRON 按键
4. EN 高 + 充电器插入 (部分型号)

### 2.4 DCDC3 / VCC_DDR 特殊说明

RK809/RK817/RK808 的 **DCDC3 不能通过寄存器调压**，只能通过外部分压电阻调节，通常作为 VCC_DDR 使用。

### 2.5 电压调节范围

**RK806:**

| 类型 | 范围 | 步进 |
|------|------|------|
| DCDC | 0.5V - 1.5V | 6.25mV |
| DCDC | 1.5V - 3.4V | 25mV |
| NLDO | 0.5V - 3.4V | 12.5mV |
| PLDO | 0.5V - 3.4V | 25mV |

**RK809/RK817:**

| 类型 | 范围 | 步进 |
|------|------|------|
| DCDC | 0.7125V - 1.5V | 12.5mV |
| DCDC | 1.6V - 2.4V | 100mV |
| LDO | 0.6V - 3.4V | 25mV (连续) |

**RK808:**

| 类型 | 范围 | 步进 |
|------|------|------|
| DCDC | 0.7125V - 1.45V | 12.5mV |
| DCDC | 1.8V - 3.3V | 100mV |
| LDO | 0.8V - 3.4V | 100mV |

---
## 3. DTS 配置要点

### 3.1 通用配置结构

所有 PMIC 的 DTS 配置都遵循相同结构 (I2C 系列)：

```dts
&i2c1 {
    status = "okay";
    pmic_name: pmic@ADDR {
        compatible = "rockchip,rkXXX";
        reg = <0xADDR>;
        interrupt-parent = <&gpioX>;
        interrupts = <PIN IRQ_TYPE_LEVEL_LOW>;
        pinctrl-names = "default";        /* RK809/RK817 可扩展 pmic-sleep/power-off/reset */
        pinctrl-0 = <&pmic_int>;
        rockchip,system-power-controller; /* 声明具备系统下电能力 */
        wakeup-source;
        #clock-cells = <1>;               /* 提供 32.768KHz CLK 输出 */
        clock-output-names = "rk808-clkout1", "rk808-clkout2";

        /* 输入电源配置 (vcc1~vcc12, 对应 DCDC/LDO 输入源) */
        vcc1-supply = <&vcc5v0_sys>;
        ...

        /* 子节点: pwrkey, rtc, gpio, codec, battery, charger */
        pwrkey { status = "okay"; };

        /* Regulator 子节点 */
        regulators {
            DCDC_REG1 { ... };
            LDO_REG1 { ... };
        };
    };
};
```

RK806 使用 SPI 接口，挂载在 `&spi2` 下，结构类似但用 `spi-max-frequency` 替代 `reg`。

### 3.2 RK809/RK817 Sleep Pin 配置

RK809/RK817 的 sleep 引脚支持 4 种功能复用：

```dts
pinctrl-names = "default", "pmic-sleep", "pmic-power-off", "pmic-reset";
pinctrl-0 = <&pmic_int>;
pinctrl-1 = <&soc_slppin_slp>, <&rk817_slppin_slp>;     /* sleep 功能 */
pinctrl-2 = <&soc_slppin_gpio>, <&rk817_slppin_pwrdn>;   /* 关机功能 */
pinctrl-3 = <&soc_slppin_rst>, <&rk817_slppin_rst>;      /* 复位功能 */
```

PMIC 内部 pinctrl：
```dts
pinctrl_rk8xx: pinctrl_rk8xx {
    gpio-controller;
    #gpio-cells = <2>;
    rk817_slppin_null: rk817_slppin_null { pins = "gpio_slp"; function = "pin_fun0"; };
    rk817_slppin_slp: rk817_slppin_slp   { pins = "gpio_slp"; function = "pin_fun1"; };
    rk817_slppin_pwrdn: rk817_slppin_pwrdn { pins = "gpio_slp"; function = "pin_fun2"; };
    rk817_slppin_rst: rk817_slppin_rst   { pins = "gpio_slp"; function = "pin_fun3"; };
};
```

### 3.3 不可修改 vs 可修改属性

**不可修改：**
- `compatible`, `reg` — 驱动匹配
- `rockchip,system-power-controller` — 系统电源控制器声明
- `wakeup-source` — 唤醒源
- `regulator-compatible` — 驱动注册匹配名

**可修改 (按 pinctrl 规则)：**
- `interrupt-parent` + `interrupts` — 中断引脚
- `pinctrl-0` — 引用 pmic_int 定义
- Regulator 节点中的电压/模式属性

### 3.4 子节点控制

```dts
/* 不需要某个功能时，显式 disabled */
rtc { status = "disabled"; };
pwrkey { status = "disabled"; };
/* 需要时设 okay 或直接删除该节点 */
```

---

## 4. Regulator DTS 属性参考

### 4.1 核心属性表

| 属性 | 说明 | 阶段 |
|------|------|------|
| `regulator-name` | 电源名字，建议与原理图一致，`regulator_get()` 匹配此名 | - |
| `regulator-min-microvolt` | 运行时可调最小电压 (uV) | kernel |
| `regulator-max-microvolt` | 运行时可调最大电压 (uV) | kernel |
| `regulator-init-microvolt` | U-Boot 阶段初始化电压，kernel 无效 | u-boot |
| `regulator-always-on` | 运行时不允许关闭，注册时自动 enable | kernel |
| `regulator-boot-on` | 注册时立即 enable | kernel |
| `regulator-initial-mode` | 运行时工作模式：1=force PWM, 2=auto PWM/PFM | kernel |
| `regulator-ramp-delay` | DCDC 电压上升时间，固定 12500 (RK809/RK817/RK808) | kernel |
| `regulator-state-mem` | 休眠时电源状态子节点 | kernel |

### 4.2 休眠状态属性 (regulator-state-mem 子节点)

| 属性 | 说明 |
|------|------|
| `regulator-on-in-suspend` | 休眠时保持上电 |
| `regulator-off-in-suspend` | 休眠时关闭 |
| `regulator-suspend-microvolt` | 休眠不断电时的待机电压 |
| `regulator-mode` | 休眠时 DCDC 模式：1=PWM, 2=AUTO (一般配 2) |
| `regulator-initial-state` | suspend 模式，必须配 3 |

### 4.3 电压设置规则

- `min == max` → 注册时自动设置该电压并 enable
- `min != max` + `boot-on/always-on` → enable 但电压为硬件默认值
- `min != max` + 无 `boot-on` → 不自动 enable，需驱动主动调用

### 4.4 Regulator 示例

```dts
vdd_logic: DCDC_REG1 {
    regulator-always-on;
    regulator-boot-on;
    regulator-min-microvolt = <950000>;
    regulator-max-microvolt = <1350000>;
    regulator-ramp-delay = <6001>;
    regulator-initial-mode = <0x2>;     /* AUTO */
    regulator-name = "vdd_logic";
    regulator-state-mem {
        regulator-on-in-suspend;        /* 休眠保持 */
        regulator-suspend-microvolt = <950000>;
    };
};
```

---

## 5. 内核驱动与 Menuconfig

### 5.1 RK806 (kernel 5.10)

| 驱动文件 | 功能 |
|---------|------|
| `drivers/mfd/rk806-core.c` | MFD 核心 |
| `drivers/mfd/rk806-spi.c` | SPI 通信 |
| `drivers/pinctrl/pinctrl-rk806.c` | GPIO/Pinctrl |
| `drivers/regulator/rk806-regulator.c` | Regulator |

Menuconfig: `CONFIG_MFD_RK806_SPI`, `CONFIG_REGULATOR_RK806`, `CONFIG_PINCTRL_RK806`

### 5.2 RK809/RK817/RK808 (kernel 4.4/4.19)

| 驱动文件 (4.4) | 驱动文件 (4.19) | 功能 |
|----------------|----------------|------|
| `drivers/mfd/rk808.c` | 同左 | MFD 核心 (所有 rk8xx 共用) |
| `drivers/input/misc/rk8xx-pwrkey.c` | `rk805-pwrkey.c` | 电源键 |
| `drivers/rtc/rtc-rk808.c` | 同左 | RTC |
| `drivers/gpio/gpio-rk8xx.c` | `drivers/pinctrl/pinctrl-rk805.c` | GPIO/Pinctrl |
| `drivers/regulator/rk808-regulator.c` | 同左 (API 有变) | Regulator |
| `drivers/clk/clk-rk808.c` | 同左 | 时钟输出 |

4.4 Menuconfig: `CONFIG_MFD_RK808`, `CONFIG_RTC_RK808`, `CONFIG_GPIO_RK8XX`, `CONFIG_REGULATOR_RK818`, `CONFIG_INPUT_RK8XX_PWRKEY`, `CONFIG_COMMON_CLK_RK808`

4.19 Menuconfig: `CONFIG_MFD_RK808`, `CONFIG_RTC_RK808`, `CONFIG_PINCTRL_RK805`, `CONFIG_REGULATOR_RK808`, `CONFIG_INPUT_RK805_PWRKEY`, `CONFIG_COMMON_CLK_RK808`

RK817 额外：`CONFIG_BATTERY_RK817`, `CONFIG_CHARGER_RK817`, `SND_SOC_RK817`

---

## 6. Regulator 内核 API

```c
/* 获取 regulator (id 对应 regulator-name) */
struct regulator *regulator_get(struct device *dev, const char *id);
struct regulator *devm_regulator_get(struct device *dev, const char *id);
struct regulator *devm_regulator_get_optional(struct device *dev, const char *id);

/* 使能/禁用 */
int regulator_enable(struct regulator *regulator);
int regulator_disable(struct regulator *regulator);

/* 电压获取/设置 (单位 uV，set 时保证 min_uV == max_uV) */
int regulator_get_voltage(struct regulator *regulator);
int regulator_set_voltage(struct regulator *regulator, int min_uV, int max_uV);

/* 释放 */
void regulator_put(struct regulator *regulator);
```

使用示例：
```c
struct regulator *rdev = regulator_get(NULL, "vdd_logic");
regulator_enable(rdev);
regulator_set_voltage(rdev, 1100000, 1100000);  // 设置 1.1V
regulator_disable(rdev);
regulator_put(rdev);
```

---

## 7. CPUFreq 动态调频

### 7.1 框架概述

CPUFreq = governor (决策) + core (封装) + driver (执行)。

### 7.2 Governor 一览

| Governor | 特点 | 适用场景 |
|----------|------|---------|
| interactive | 响应快，参数丰富 | Linux4.4 默认 |
| schedutil | EAS 专用，能耗感知调度 | Linux4.19+ |
| ondemand | 负载调频，幅度大 | 通用 |
| conservative | 负载调频，平滑升降 | 功耗敏感 |
| performance | 最高频 | 跑分/测试 |
| powersave | 最低频 | 极致省电 |
| userspace | 用户态设频 | 定频测试 |

### 7.3 DTS 关键配置

```dts
/* 1. CPU 节点配置 clock 和 supply */
&cpu0 {
    clocks = <&cru ARMCLK>;           /* 非大小核 */
    cpu-supply = <&vdd_arm>;          /* 指向 PMIC regulator */
    operating-points-v2 = <&cpu0_opp_table>;
};

/* 大小核平台 (RK3399) */
&cpu_l0 { clocks = <&cru ARMCLKL>; cpu-supply = <&vdd_cpu_l>; };
&cpu_b0 { clocks = <&cru ARMCLKB>; cpu-supply = <&vdd_cpu_b>; };
```

### 7.4 用户态接口

```bash
# 查看/切换 governor
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor

# 查看支持的频率
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_available_frequencies

# 定频 (userspace 模式下)
echo 1008000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed

# 查看当前频率/限制频率
cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq
echo 1200000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq
```

---

## 8. Devfreq 动态调频

### 8.1 框架概述

与 CPUFreq 类似，但用于 CPU 以外的模块 (GPU, DDR/DMC, BUS)。

### 8.2 GPU DVFS 配置

```dts
&gpu {
    operating-points-v2 = <&gpu_opp_table>;
    mali-supply = <&vdd_gpu>;     /* 指向 GPU regulator */
};
```

### 8.3 DMC (DDR) DVFS 配置

```dts
&dmc {
    operating-points-v2 = <&dmc_opp_table>;
    center-supply = <&vdd_logic>;  /* 或 vdd_center */
    devfreq-events = <&dfi>;       /* DDR 利用率监控 */
    upthreshold = <40>;            /* 负载>40% 调最高频 */
    downdifferential = <20>;       /* 负载<20% 降频 */
    auto-freq-en = <1>;            /* 使能负载变频 */
    auto-min-freq = <400000>;      /* 最低频率限制 */
    system-status-freq = <
        SYS_STATUS_NORMAL       800000
        SYS_STATUS_SUSPEND      200000
        SYS_STATUS_VIDEO_4K     600000
        SYS_STATUS_PERFORMANCE  800000
    >;
};
```

### 8.4 Devfreq 用户态接口

```bash
# GPU 示例
cat /sys/class/devfreq/ff400000.gpu/cur_freq
echo userspace > /sys/class/devfreq/ff400000.gpu/governor
echo 400000000 > /sys/class/devfreq/ff400000.gpu/userspace/set_freq

# DDR 示例
cat /sys/class/devfreq/dmc/cur_freq
cat /sys/class/devfreq/dmc/load
cat /sys/class/devfreq/dmc/system_status
```

---

## 9. OPP Table 配置

### 9.1 基本结构

```dts
cpu0_opp_table: opp-table0 {
    compatible = "operating-points-v2";
    opp-shared;

    opp-408000000 {
        opp-hz = /bits/ 64 <408000000>;
        opp-microvolt = <950000 950000 1350000>;  /* <target min max> */
        clock-latency-ns = <40000>;
        opp-suspend;   /* 休眠/关核时使用此频点 (仅一个 OPP 可含) */
    };
    opp-1296000000 {
        opp-hz = /bits/ 64 <1296000000>;
        opp-microvolt = <1350000 1350000 1350000>;
        clock-latency-ns = <40000>;
    };
};
```

### 9.2 删除 OPP 频点

```dts
/* 方法1: 直接 disable */
opp-1296000000 { status = "disabled"; };

/* 方法2: 板级 DTS 覆盖 */
&cpu0_opp_table {
    opp-1296000000 { status = "disabled"; };
};
```

### 9.3 电压调整策略

三种自动调压机制 (详见 `references/dvfs_power_tuning.md`)：

| 机制 | 原理 | DTS 属性 |
|------|------|---------|
| Leakage 调压 | 根据芯片静态电流分档选电压 | `rockchip,leakage-voltage-sel` |
| PVTM 调压 | 根据工艺-电压-温度监测值分档 | `rockchip,pvtm-voltage-sel` |
| IR-Drop 补偿 | 根据板级电源纹波补偿电压 | `rockchip,board-irdrop` |

### 9.4 宽温配置 (-40°C ~ 85°C)

```dts
&cpu0_opp_table {
    rockchip,temp-hysteresis = <5000>;           /* 迟滞 5°C */
    rockchip,low-temp = <0>;                     /* 低温阈值 0°C */
    rockchip,low-temp-min-volt = <900000>;       /* 低温最低电压 */
    rockchip,low-temp-adjust-volt = <0 1800 25000>; /* 低温加压 25mV */
    rockchip,high-temp = <85000>;                /* 高温阈值 85°C */
    rockchip,high-temp-max-volt = <1200000>;     /* 高温最高电压限制 */
    rockchip,max-volt = <1250000>;
};
```

---

## 10. 功耗分析与优化

### 10.1 电压域 (VD) 与电源域 (PD)

以 RK3399 为例：
- **VD_CORE_B**: 2× A72 大核 (独立供电，功耗大)
- **VD_CORE_L**: 4× A53 小核
- **VD_GPU**: GPU
- **VD_LOGIC**: USB/EMMC/GMAC/SPI/I2C/VOP 等外设
- **VD_CENTER**: VPU/VEPU/IEP/RGA + DDR 控制器
- **VD_PMU**: PMU/SRAM/GPIO/PVTM (待机唤醒模块)

### 10.2 功耗公式

```
动态功耗: P(d) = C × V² × F    (C=常量, V=电压, F=频率)
静态功耗: 随温度和电压升高而增大 (泄漏电流)
```

### 10.3 功耗测量方法

1. 串联小电阻 (0.01Ω)，电压表测两端压差 → I = U/R
2. 使用 PowerMeterage 工具同时采集 20 路
3. DCDC 按 80%-90% 效率折算到电池端，LDO 输入电流=输出电流
4. 记录温度：`cat /sys/class/thermal/thermal_zone0/temp`

### 10.4 优化策略速查

| 优化方向 | 方法 |
|---------|------|
| CPU | 调 cpufreq 参数 (hispeed_freq/target_loads)；关闭部分核；cpuset 绑核 |
| GPU | devfreq 调参 (upthreshold/downdifferential) |
| DDR | 场景变频 + 负载变频；sr_idle/pd_idle 低功耗配置 |
| 温控 | 改善散热；优化温控策略；高温限压限频 |
| 电源 | 大压差改用 DCDC；LDO 接到 DCDC 输出降低输入电压 |

---

## 11. 调试方法

### 11.1 Regulator 调试

```bash
# 查看所有 regulator 状态
cat /sys/kernel/debug/regulator/regulator_summary

# 查看特定 regulator 电压
cat /sys/kernel/debug/regulator/vdd_logic/voltage

# 设置电压 (debug 接口)
echo 950000 > /sys/kernel/debug/regulator/vdd_logic/voltage
```

### 11.2 PMIC 寄存器调试

```bash
# 4.4/4.19 内核
echo r [addr] > /sys/rk8xx/rk8xx_dbg     # 读寄存器
echo w [addr] [value] > /sys/rk8xx/rk8xx_dbg  # 写寄存器
```

### 11.3 OPP/DVFS 调试

```bash
# 查看频率电压表
cat /sys/kernel/debug/opp/opp_summary

# 查看时钟树
cat /sys/kernel/debug/clk/clk_summary

# 查看电源域状态
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary

# 查看 leakage / PVTM 档位
dmesg | grep leakage
dmesg | grep pvtm
```

### 11.4 单独调频调压 (注意升频先升压，降频先降频)

```bash
# 设置 CPU 频率
echo 408000000 > /sys/kernel/debug/clk/armclk/clk_rate
# 设置 CPU 电压
echo 950000 > /sys/kernel/debug/regulator/vdd_arm/voltage
```

---
## 12. 常见故障排查

### 12.1 Regulator 相关

| 故障现象 | 可能原因 | 排查方法 |
|---------|---------|---------|
| PMIC 驱动加载失败 | I2C/SPI 通信异常 | 检查总线 status、地址、中断配置 |
| regulator 注册失败 | `regulator-compatible` 名字错误 | 检查 DTS 中名字是否与驱动匹配 |
| 某路电源电压异常 | min/max 配置错误 | 对照原理图检查电压范围 |
| 休眠功耗高 | regulator-state-mem 未配置 | 检查各路 on/off-in-suspend |
| 关机失败 | sleep pin 功能配置错误 | 检查 pinctrl-2 (pmic-power-off) |

### 12.2 CPUFreq 相关

| 故障现象 | 可能原因 | 排查方法 |
|---------|---------|---------|
| cpufreq 初始化失败 | 缺少 clock/opp-table | `dmesg | grep cpufreq` 查看 -2/-19 错误 |
| 高频死机 | 电压偏低 / IR-Drop | 抬压或增加 board-irdrop 补偿 |
| 变频不生效 | governor 不对 | 检查 scaling_governor |

### 12.3 Devfreq 相关

| 故障现象 | 可能原因 | 排查方法 |
|---------|---------|---------|
| GPU 变频不起 | 缺少 mali-supply | 检查 GPU 节点 regulator 配置 |
| DDR 变频闪屏 | auto-min-freq 太低 | 提高最低频率或配置 vop-bw-dmc-freq |
| DMC probe 失败 | dfi 节点未使能 | 检查 devfreq-events 配置 |

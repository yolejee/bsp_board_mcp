# Rockchip 平台 Suspend/Resume 配置参考

> 本文件基于 Rockchip 官方文档整理，覆盖 RK3588/RK3399/RK3308 的待机配置和调试方法。

---

## 1. 通用架构

### 1.1 驱动文件

| SoC | 驱动文件 | 头文件 |
|-----|---------|--------|
| RK3588 | `drivers/soc/rockchip/rockchip_pm_config.c` | `include/dt-bindings/suspend/rockchip-rk3588.h` |
| RK3399 | `drivers/soc/rockchip/rockchip_pm_config.c` | `include/dt-bindings/suspend/rockchip-rk3399.h` |
| RK3308 | `drivers/soc/rockchip/rockchip_pm_config.c` | `include/dt-bindings/suspend/rockchip-rk3308.h` |
| 通用 | `drivers/firmware/rockchip_sip.c` | — |

### 1.2 DTS 节点

```dts
/* 所有 RK 平台的 PM 配置都在同一结构下 */
rockchip_suspend: rockchip-suspend {
    compatible = "rockchip,pm-rk3588";    /* 或 rk3399/rk3308 */
    status = "okay";
    rockchip,sleep-mode-config = <...>;   /* 休眠模式配置 */
    rockchip,wakeup-config = <...>;       /* 唤醒源配置 */
    rockchip,sleep-debug-en = <1>;        /* debug 开关 */
};
```

### 1.3 RK 平台 Suspend 特殊机制

```
Rockchip 平台的 suspend 与标准 Linux 的区别:

1. Trust Firmware (ATF) 接管
   Linux kernel suspend flow 完成后，控制权转交给 Trust/ATF
   ATF 负责: 关闭 PLL、断电 PD、配置 DDR 自刷新、控制 PMU 状态机

2. PMU 状态机
   PMU (Power Management Unit) 是硬件状态机
   负责按配置的 sleep-mode-config 逐步关闭电源域

3. Write-Enable 机制
   关键寄存器使用 bits_write_enable:
   高 16 bit 为 mask (写 1 使能对应低 bit 的写入)
   低 16 bit 为 value
```

---

## 2. RK3588 待机配置

### 2.1 Sleep Mode Config

| 宏定义 | Bit | 功能 | 功耗级别 |
|--------|-----|------|---------|
| `RKPM_SLP_ARMOFF` | BIT(1) | 断电 vdd_arm | 中 |
| `RKPM_SLP_ARMOFF_DDRPD` | BIT(2) | 断电 vdd_arm + DDR 控制器断电 | 中低 |
| `RKPM_SLP_ARMOFF_LOGOFF` | BIT(3) | 断电 vdd_arm + vdd_log | 低 |
| `RKPM_SLP_ARMOFF_PMUOFF` | BIT(4) | 断电 vdd_arm + vdd_log + PMU1 | 极低 |
| `RKPM_SLP_PMU_PMUALIVE_32K` | BIT(9) | 使用 32K 时钟源 | — |
| `RKPM_SLP_PMU_DIS_OSC` | BIT(10) | 关闭 24M 晶振 | 最低 |
| `RKPM_SLP_32K_EXT` | BIT(24) | 使用外部 32K 时钟源 | — |

**推荐配置（最低功耗）：**
```dts
rockchip,sleep-mode-config = <
    (0
    | RKPM_SLP_ARMOFF_LOGOFF
    | RKPM_SLP_PMU_PMUALIVE_32K
    | RKPM_SLP_PMU_DIS_OSC
    )>;
```

### 2.2 Wakeup Config

| 宏定义 | Bit | 功能 | 推荐 |
|--------|-----|------|------|
| `RKPM_CPU0_WKUP_EN` ~ `RKPM_CPU7_WKUP_EN` | BIT(0~7) | 各 CPU 中断唤醒（经 GIC） | 次选 |
| `RKPM_GPIO_WKUP_EN` | BIT(8) | GPIO0 唤醒（直达 PMU，不经 GIC） | **首选** |
| `RKPM_SDMMC_WKUP_EN` | BIT(9) | SDMMC 唤醒 | 按需 |
| `RKPM_SDIO_WKUP_EN` | BIT(10) | SDIO 唤醒 | 按需 |
| `RKPM_USB_WKUP_EN` | BIT(11) | USB DEV 唤醒 | 按需 |
| `RKPM_UART0_WKUP_EN` | BIT(12) | UART0 唤醒 | 按需 |
| `RKPM_VAD_WKUP_EN` | BIT(13) | VAD 语音唤醒 | 按需 |
| `RKPM_TIMER_WKUP_EN` | BIT(14) | RK TIMER 唤醒 | 按需 |
| `RKPM_TIME_OUT_WKUP_EN` | BIT(16) | PMU 内部 timer（默认 1s，仅 debug） | 仅调试 |

**唤醒源选择要点：**
- **GPIO 唤醒（首选）**：仅 GPIO0 支持作为唤醒源，信号直达 PMU 状态机，不经过 GIC，可靠性最高
- **CPU 中断唤醒（次选）**：支持所有 `enable_irq_wake()` 注册的中断唤醒，但可能被非预期中断唤醒
- **USB 唤醒限制**：USB 唤醒时不能关闭 USB 电源/时钟，不能配置 `RKPM_SLP_ARMOFF_LOGOFF` 和 `RKPM_SLP_PMU_DIS_OSC`

### 2.3 Debug 配置

| 宏定义 | Bit | 功能 |
|--------|-----|------|
| `RKPM_SLP_TIME_OUT_WKUP` | BIT(25) | 待机 1s 自动唤醒（仅 debug 用） |
| `RKPM_SLP_PMU_DBG` | BIT(26) | PMU 状态机通过 **GPIO0_A5** 输出波形信号 |

```dts
/* Debug 模式完整配置示例 */
rockchip_suspend: rockchip-suspend {
    compatible = "rockchip,pm-rk3588";
    status = "okay";
    rockchip,sleep-mode-config = <
        (0
        | RKPM_SLP_ARMOFF_LOGOFF
        | RKPM_SLP_PMU_PMUALIVE_32K
        | RKPM_SLP_PMU_DIS_OSC
        )>;
    rockchip,wakeup-config = <
        (0
        | RKPM_GPIO_WKUP_EN
        )>;
    rockchip,sleep-debug-en = <1>;   /* 打开休眠 log */
};
```

### 2.4 休眠打印信息解读

```
# 进入休眠打印
INFO: ... trust version ...      # Trust 固件版本
sleep:mode(N) ...                # 配置及次数
... SLP_ARMOFF_LOGOFF ...        # 休眠模式
GPIO0_INTEN: 0x00000041          # GPIO0 中断使能状态
PMU_WKUP_INT_CON: 0x00000100    # PMU 唤醒中断配置

# 唤醒打印
012376543edcba2                  # PMU 状态机步骤序列
wake up by: gpio0                # 唤醒源标识
```

---

## 3. RK3399 待机配置

### 3.1 Sleep Mode Config

| 宏定义 | Bit | 功能 |
|--------|-----|------|
| `RKPM_SLP_WFI` | BIT(0) | CPU 处于 WFI 状态（仅调试） |
| `RKPM_SLP_ARMPD` | BIT(1) | cpu_pd power down |
| `RKPM_SLP_PERILPPD` | BIT(2) | perilp_pd power down |
| `RKPM_SLP_DDR_RET` | BIT(3) | DDR 进入自刷新 + retention |
| `RKPM_SLP_PLLPD` | BIT(4) | PLL power down |
| `RKPM_SLP_OSC_DIS` | BIT(5) | 关闭 24M OSC，系统切 32K |
| `RKPM_SLP_CENTER_PD` | BIT(6) | center_pd power down |
| `RKPM_SLP_AP_PWROFF` | BIT(7) | AP_OFF 拉高，控制 PMIC 休眠 |

### 3.2 电源配置 (pwm-regulator-config)

```dts
/* 如果硬件使用 PWM 调压器，需要对应配置 */
rockchip,pwm-regulator-config = <
    (0
    | PWM2_REGULATOR_EN     /* VDD_LOG 使用 PWM2 */
    )>;
```

### 3.3 APIO 配置

```dts
/* 硬件电路支持时，APIO 可在休眠时独立断电 */
rockchip,apios-suspend = <
    (0
    | RKPM_APIO1_SUSPEND   /* APIO1 休眠时断电 */
    | RKPM_APIO2_SUSPEND
    )>;
```

### 3.4 GPIO 控制外部电源

```dts
/* 休眠时通过 GPIO 关闭外部电源，唤醒时恢复 */
rockchip,power-ctrl =
    <&gpio1 RK_PC1 GPIO_ACTIVE_HIGH>,  /* WiFi 电源 */
    <&gpio3 RK_PD5 GPIO_ACTIVE_HIGH>;  /* 某外设电源 */
```

### 3.5 唤醒打印解读

```
# 典型唤醒日志
wake up status: 0x4        # bit2 = GPIO 唤醒
GPIO interrupt wakeup
GPIO1: 0x200000            # GPIO1 的中断状态
→ gpio1_c5                 # 具体唤醒引脚
```

---

## 4. RK3308 待机配置

### 4.1 两种产品形态

| 产品类型 | 特点 | 功耗级别 |
|---------|------|---------|
| **VAD 产品** | 保持 VAD/ACODEC/PDM 时钟和 24M 晶振，支持语音唤醒 | 较高（几 mA） |
| **Non-VAD 产品** | 几乎所有模块关闭，系统时钟切 32K/24M | 极低（百 uA 级） |

### 4.2 Sleep Mode Config

| 宏定义 | Bit | 功能 |
|--------|-----|------|
| `RKPM_ARMOFF` | BIT(0) | 断电 vdd_arm |
| `RKPM_VADOFF` | BIT(1) | 关闭 VAD 模块 |
| `RKPM_PMU_HW_PLLS_PD` | BIT(3) | 默认必选 |
| `RKPM_PMU_DIS_OSC` | BIT(4) | 关闭 24M 晶振 |
| `RKPM_PMU_PMUALIVE_32K` | BIT(5) | 使用 PMU 内部 32K（推荐） |
| `RKPM_PMU_EXT_32K` | BIT(6) | 使用外部 32K（不推荐） |
| `RKPM_PDM_CLK_OFF` | BIT(9) | ARMOFF 时关闭 PDM 时钟 |
| `RKPM_PWM_VOLTAGE_DEFAULT` | BIT(10) | PWM 设置为 maskrom 同电压（宽温芯片） |

### 4.3 Debug 配置

| 宏定义 | Bit | 功能 |
|--------|-----|------|
| `RKPM_DBG_CLK_UNGATE` | BIT(25) | 休眠时保持所有 clk 使能（排查 clk 关闭导致唤醒异常） |
| `RKPM_DBG_FSM_SOUT` | BIT(27) | PMU 状态机通过 **GPIO4_D5** 输出波形 |
| `RKPM_DBG_REG` | BIT(29) | dump 寄存器（GPIO/GRF/SGRF 等） |

### 4.4 休眠打印解读

```
GPIO0_INTEN: 00000041           # 唤醒 pin
config=0x8040009:armoff-hwplldown-ddrsw-gating-24M-sout-  # 配置标志
0123a4                          # 休眠步骤编号
Enabling: vad(1) acodec(1)...   # VAD 模块状态
DDR: vpll0 | VOICE: vpll0 ...  # PLL 占用状态
5bRc678wfi                      # 完成休眠进入 WFI
876ab543210                     # 唤醒步骤编号
IRQ=89, PMU wakeup int: vad     # 唤醒源信息
Wfi total: 2.419s               # 实际休眠时间
```

### 4.5 Reboot/Reset 保护

```dts
/* 重启时跳过指定模块复位（用于 "power hold" 引脚保护） */
rockchip,rst-config = <
    (0
    | GLB1RST_IGNORE_PWM0    /* 保护 PWM 调压器 */
    )>;
```

---

## 5. 跨平台通用调试方法

### 5.1 信任链调试

```bash
# 1. 确认 Trust 固件版本
dmesg | grep -i trust
# 不同版本的 Trust 对 suspend 支持不同

# 2. 确认 DTS 配置生效
cat /sys/firmware/devicetree/base/rockchip-suspend/rockchip,sleep-mode-config
# 验证实际读到的值与 DTS 配置一致

# 3. 测试最简配置（仅 ARMOFF）
# 先用最轻量的配置确认基本 suspend/resume 工作
rockchip,sleep-mode-config = <(0 | RKPM_SLP_ARMOFF)>;
rockchip,wakeup-config = <(0 | RKPM_GPIO_WKUP_EN)>;
# 成功后再逐步加深休眠深度
```

### 5.2 PMU 状态机波形调试

```
各平台 PMU 状态机 debug 引脚:
  RK3588: GPIO0_A5
  RK3308: GPIO4_D5
  RK3399: 参考具体 TRM

使用方法:
  1. DTS 打开 FSM_SOUT debug bit
  2. 示波器探针接到对应 GPIO
  3. 触发休眠，观察波形
  4. 波形表示 PMU 状态机的步进过程
  → 如果波形卡在某个状态，说明该步骤出了问题
```

### 5.3 常见 RK 平台功耗优化

```
1. 基准: 先确认 EVB 板的功耗数据（作为参考标准）
2. 分路测量: 分别测 VDD_CPU, VDD_GPU, VDD_LOGIC, VCC_DDR, VCC_IO
3. DCDC 折算: V × I / 效率(0.8~0.9) / 电池电压 → 电池端功耗
4. IO 漏电排查: 逐个断开外设电源，观察功耗变化
5. PHY 漏电: Ethernet PHY / USB PHY 休眠时的漏电是常见问题
```

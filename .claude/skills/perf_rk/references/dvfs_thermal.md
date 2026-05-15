# DVFS 与温控详细参考

本文件包含 CPUFreq、Devfreq、Thermal 的完整 DTS 配置和调参指南。

## 目录

1. [CPUFreq 完整配置](#1-cpufreq-完整配置)
2. [Devfreq (GPU/DDR/BUS) 完整配置](#2-devfreq-完整配置)
3. [Thermal 温控完整配置](#3-thermal-温控完整配置)
4. [功耗分析方法](#4-功耗分析方法)

---

## 1. CPUFreq 完整配置

### 1.1 代码路径

```
drivers/cpufreq/cpufreq.c                    # 核心框架
drivers/cpufreq/cpufreq-dt.c                 # platform driver
drivers/cpufreq/rockchip-cpufreq.c           # platform device（RK 定制）
drivers/soc/rockchip/rockchip_opp_select.c   # 根据 leakage/PVTM 修改电压表
drivers/cpufreq/cpufreq_interactive.c        # interactive governor
kernel/sched/cpufreq_schedutil.c             # schedutil governor
```

### 1.2 全部 Governor 列表

| Governor | 说明 | 适用场景 |
|----------|------|----------|
| `performance` | 始终最高频 | 基准测试/性能场景 |
| `powersave` | 始终最低频 | 省电 |
| `ondemand` | 按负载大幅调频 | 通用 |
| `conservative` | 按比例平滑调频 | 通用 |
| `interactive` | 响应快，参数多 | Android 默认 |
| `userspace` | 用户手动设频 | 定频测试 |
| `schedutil` | EAS 调度器驱动 | Linux 5.x+ 推荐 |

### 1.3 完整 sysfs 接口

路径：`/sys/devices/system/cpu/cpufreq/policy{0,4,6}/`

| 接口 | 说明 |
|------|------|
| `related_cpus` | 同 cluster 下所有 CPU |
| `affected_cpus` | 同 cluster 下未关闭的 CPU |
| `cpuinfo_transition_latency` | 频率切换延迟 (ns) |
| `cpuinfo_max_freq` | 硬件支持的最高频率 |
| `cpuinfo_min_freq` | 硬件支持的最低频率 |
| `cpuinfo_cur_freq` | 硬件寄存器中当前频率 |
| `scaling_available_frequencies` | 支持的频率列表 |
| `scaling_available_governors` | 支持的 governor 列表 |
| `scaling_governor` | 当前 governor |
| `scaling_cur_freq` | 软件最后设置的频率 |
| `scaling_max_freq` | 软件限制最高频率 |
| `scaling_min_freq` | 软件限制最低频率 |
| `scaling_setspeed` | userspace 模式下设置频率 |
| `stats/time_in_state` | 各频率运行时间 (10ms 单位) |
| `stats/total_trans` | 总变频次数 |
| `stats/trans_table` | 频率切换矩阵 |

### 1.4 Leakage 调压 DTS

根据芯片漏电流值选择不同电压档位：

```dts
cpu0_opp_table {
    nvmem-cells = <&cpu_leakage>;
    nvmem-cell-names = "cpu_leakage";
    rockchip,leakage-voltage-sel = <
        1   10  0    /* leakage 1-10mA → L0 电压 */
        11  254 1    /* leakage 11-254mA → L1 电压 */
    >;
    opp-1296000000 {
        opp-microvolt = <1350000 1350000 1350000>;       /* 默认 */
        opp-microvolt-L0 = <1350000 1350000 1350000>;    /* L0 档 */
        opp-microvolt-L1 = <1300000 1300000 1350000>;    /* L1 档（更省电） */
    };
};
```

### 1.5 PVTM 调压 DTS

根据工艺参数监测值选择电压档：

```dts
cpu0_opp_table {
    rockchip,pvtm-voltage-sel = <
        0     14300 0
        14301 15000 1
        15001 16000 2
        16001 99999 3
    >;
    rockchip,pvtm-freq = <408000>;            /* 测量时的频率 */
    rockchip,pvtm-volt = <1000000>;           /* 测量时的电压 */
    rockchip,pvtm-ch = <0 0>;                 /* 通道 <ring sel> */
    rockchip,pvtm-sample-time = <1000>;       /* 采样时间 us */
    rockchip,pvtm-number = <10>;              /* 采样次数 */
    rockchip,pvtm-error = <1000>;             /* 允许误差 */
    rockchip,pvtm-ref-temp = <35>;            /* 参考温度 */
    rockchip,pvtm-temp-prop = <(-18) (-18)>;  /* 温度补偿系数 */
    rockchip,thermal-zone = "soc-thermal";
};
```

### 1.6 IR-Drop 补偿 DTS

板级走线和电容带来的压降补偿：

```dts
/* SoC 级别：EVB 板上的 IR-Drop 参考值 */
cpu0_opp_table {
    rockchip,max-volt = <1350000>;
    rockchip,evb-irdrop = <25000>;    /* EVB 板压降 25mV */
};

/* 板级 DTS：实际板子的 IR-Drop */
&cpu0_opp_table {
    rockchip,board-irdrop = <
        0    815  37500    /* 0-815mV 电压范围下的压降 37.5mV */
        816  1119 50000    /* 实际补偿 = board-irdrop - evb-irdrop */
        1200 1512 75000
    >;
};
```

### 1.7 宽温配置 DTS

```dts
cpu0_opp_table {
    rockchip,temp-hysteresis = <5000>;            /* 迟滞 5°C */
    rockchip,low-temp = <0>;                       /* 低温阈值 0°C */
    rockchip,low-temp-min-volt = <900000>;         /* 低温最低电压 */
    rockchip,low-temp-adjust-volt = <
        0 1800 25000    /* 低温下所有频点加 25mV */
    >;
    rockchip,high-temp = <85000>;                  /* 高温阈值 85°C */
    rockchip,high-temp-max-volt = <1200000>;       /* 高温最高电压限制 */
    rockchip,high-temp-max-freq = <1008000>;       /* 或 限制最高频率 */
};
```

---

## 2. Devfreq 完整配置

### 2.1 代码路径

```
drivers/devfreq/devfreq.c                           # 核心框架
drivers/devfreq/rockchip_dmc.c                      # DMC driver + dmc_ondemand governor
drivers/devfreq/event/rockchip-dfi.c                # DDR 读写 cycle 监控
drivers/devfreq/event/rockchip-nocp.c               # 各模块 DDR 访问字节数
drivers/gpu/arm/midgard/.../mali_kbase_devfreq.c    # GPU Mali driver
drivers/devfreq/rockchip_bus.c                      # BUS driver
```

### 2.2 Devfreq sysfs 接口

路径：`/sys/class/devfreq/<device>/`

| 接口 | 说明 |
|------|------|
| `available_frequencies` | 支持的频率列表 |
| `available_governors` | 支持的 governor |
| `cur_freq` | 当前频率 |
| `governor` | 当前 governor |
| `load` | 当前负载百分比 |
| `max_freq` | 软件限制最高频率 |
| `min_freq` | 软件限制最低频率 |
| `polling_interval` | 负载检测间隔 ms |
| `target_freq` | 软件最后设置的目标频率 |
| `trans_stat` | 变频统计 |

### 2.3 GPU OPP Table DTS

```dts
gpu_opp_table: opp-table2 {
    compatible = "operating-points-v2";
    opp-200000000 {
        opp-hz = /bits/ 64 <200000000>;
        opp-microvolt = <800000>;
    };
    opp-400000000 {
        opp-hz = /bits/ 64 <400000000>;
        opp-microvolt = <900000>;
    };
    opp-800000000 {
        opp-hz = /bits/ 64 <800000000>;
        opp-microvolt = <1100000>;
    };
};
&gpu {
    operating-points-v2 = <&gpu_opp_table>;
    mali-supply = <&vdd_gpu>;
};
```

### 2.4 DMC 完整 DTS（DDR 变频）

```dts
&dmc {
    operating-points-v2 = <&dmc_opp_table>;
    center-supply = <&vdd_center>;          /* 或 vdd_logic */
    devfreq-events = <&dfi>;                /* 通过 DFI 监控 DDR 利用率 */

    /* 场景变频 */
    system-status-freq = <
        SYS_STATUS_NORMAL       800000      /* 空闲 */
        SYS_STATUS_REBOOT       528000      /* 重启 */
        SYS_STATUS_SUSPEND      200000      /* 休眠 */
        SYS_STATUS_VIDEO_1080P  200000      /* 1080P 播放 */
        SYS_STATUS_VIDEO_4K     600000      /* 4K 播放 */
        SYS_STATUS_VIDEO_4K_10B 800000      /* 4K 10bit */
        SYS_STATUS_PERFORMANCE  800000      /* performance 模式 */
        SYS_STATUS_BOOST        400000      /* 触摸 boost */
        SYS_STATUS_DUALVIEW     600000      /* 双屏 */
        SYS_STATUS_ISP          600000      /* 拍照 */
    >;
    /* 头文件：include/dt-bindings/clock/rk_system_status.h */

    /* 负载变频 */
    auto-freq-en = <1>;             /* 负载变频开关 */
    upthreshold = <40>;             /* 利用率 >40% → 最高频 */
    downdifferential = <20>;        /* 利用率 <20% → 降频 */
    auto-min-freq = <400000>;       /* 负载变频最低频率 */

    /* VOP 带宽驱动的频率下限 */
    vop-bw-dmc-freq = <
        0    577  200000     /* VOP 带宽 0-577 MB/s → DDR ≥ 200MHz */
        578  1701 300000
        1702 99999 400000
    >;
};
```

### 2.5 BUS DVFS DTS

```dts
bus_apll: bus-apll {
    compatible = "rockchip,px30-bus";
    rockchip,busfreq-policy = "clkfreq";
    clocks = <&cru PLL_APLL>;
    clock-names = "bus";
    operating-points-v2 = <&bus_apll_opp_table>;
    status = "okay";
};
&bus_apll { bus-supply = <&vdd_logic>; };
```

---

## 3. Thermal 温控完整配置

### 3.1 代码路径

```
drivers/thermal/thermal_core.c
drivers/thermal/power_allocator.c        # PID 温控
drivers/thermal/step_wise.c
drivers/thermal/cpu_cooling.c            # CPU cooling device
drivers/thermal/devfreq_cooling.c        # GPU/DDR cooling device
drivers/thermal/rockchip_thermal.c       # RK Tsadc 驱动
```

### 3.2 Tsadc 配置

```dts
&tsadc {
    rockchip,hw-tshut-mode = <1>;        /* 0: CRU 复位  1: GPIO 复位 */
    rockchip,hw-tshut-polarity = <1>;    /* 0: LOW  1: HIGH */
    rockchip,hw-tshut-temp = <120000>;   /* 硬件过温重启阈值 120°C */
    status = "okay";
};
```

### 3.3 CPU Cooling Device

```dts
cpu_l0: cpu@0 {
    #cooling-cells = <2>;
    dynamic-power-coefficient = <100>;   /* 动态功耗常数 C */
};
cpu_b0: cpu@100 {
    #cooling-cells = <2>;
    dynamic-power-coefficient = <436>;   /* A72 功耗常数远大于 A53 */
};
```

### 3.4 GPU Power Model

```dts
gpu {
    #cooling-cells = <2>;
    power_model {
        compatible = "arm,mali-simple-power-model";
        static-coefficient = <411000>;
        dynamic-coefficient = <733>;
        ts = <32000 4700 (-80) 2>;       /* 温度系数 a, b, c, d */
        thermal-zone = "gpu-thermal";
    };
};
```

### 3.5 功耗计算公式

- **动态功耗**：P_dynamic = C × V² × F
- **静态功耗**：P_static = C × t_scale × v_scale
  - t_scale = a×T³ + b×T² + c×T + d
  - v_scale = V³
- **sustainable-power 推导**：
  sustainable + 2×sustainable/(target-threshold) × (target-T_start) = P_max

### 3.6 Trace 温控数据的 event 列表

```bash
# 基础温度事件
/sys/kernel/debug/tracing/events/thermal/

# power_allocator 事件（PID 控制数据）
/sys/kernel/debug/tracing/events/thermal_power_allocator/
```

---

## 4. 功耗分析方法

### 4.1 RK3399 电压域划分

| VD | 供电模块 |
|----|---------|
| VD_CORE_B | 2×A72 |
| VD_CORE_L | 4×A53 |
| VD_LOGIC | USB, eMMC, GMAC, SPI, I2C, EDP, VOP, AXI/AHB/APB |
| VD_CENTER | VDPU, VEPU, IEP, RGA, DDR 控制器 |
| VD_GPU | GPU |
| VD_PMU | PMU, SRAM, GPIO, PVTM |

### 4.2 排查命令汇总

```bash
# 全部 regulator 状态
cat /sys/kernel/debug/regulator/regulator_summary

# Clock 树
cat /sys/kernel/debug/clk/clk_summary

# Power Domain
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary

# 中断计数
cat /proc/interrupts

# CPU 频率分布
cat /sys/devices/system/cpu/cpufreq/policy0/stats/time_in_state
```

### 4.3 CPUSET/CPUCTL 功耗优化

```bash
# CPUSET：限制进程只跑小核
mkdir -p /dev/cpuset/little
echo 0-3 > /dev/cpuset/little/cpus
echo 0 > /dev/cpuset/little/mems
echo $PID > /dev/cpuset/little/tasks

# CPUCTL：限制 CPU 时间（需 CONFIG_CFS_BANDWIDTH）
mkdir -p /dev/cpuctl/mygroup
echo 100000 > /dev/cpuctl/mygroup/cpu.cfs_period_us   # 周期 100ms
echo 50000 > /dev/cpuctl/mygroup/cpu.cfs_quota_us     # 最多用 50ms
echo $PID > /dev/cpuctl/mygroup/tasks
```

### 4.4 Power Domain 管理

- DTS 无 PD 引用 → 开机后框架自动关闭
- DTS 有 PD 引用但驱动无 runtime PM → PD 常开（unsupported）
- DTS 有 PD 引用 + 驱动有 runtime PM → 按需开关

关闭不使用的外设（DTS 中 `status = "disabled"`）可降低功耗。

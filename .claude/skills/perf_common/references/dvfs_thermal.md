# DVFS 与温控详细参考（通用 Linux）

本文件包含 CPUFreq、Devfreq、Thermal 的完整配置和调参指南，适用于所有 Linux 嵌入式平台。

## 目录

1. [CPUFreq 完整配置](#1-cpufreq-完整配置)
2. [Devfreq 完整配置](#2-devfreq-完整配置)
3. [Thermal 温控完整配置](#3-thermal-温控完整配置)
4. [功耗分析方法](#4-功耗分析方法)
5. [EAS 能效感知调度](#5-eas-能效感知调度)

---

## 1. CPUFreq 完整配置

### 1.1 核心代码路径

```
drivers/cpufreq/cpufreq.c                    # CPUFreq 核心框架
drivers/cpufreq/cpufreq-dt.c                 # 通用 DT-based cpufreq driver
drivers/cpufreq/cpufreq_ondemand.c            # ondemand governor
drivers/cpufreq/cpufreq_conservative.c        # conservative governor
kernel/sched/cpufreq_schedutil.c              # schedutil governor (EAS)
drivers/opp/of.c                              # OPP 框架 (device-tree 绑定)
```

平台特化驱动（各厂商）：
```
# Rockchip
drivers/cpufreq/rockchip-cpufreq.c

# NXP i.MX
drivers/cpufreq/imx6q-cpufreq.c
drivers/cpufreq/imx-cpufreq-dt.c

# TI
drivers/cpufreq/ti-cpufreq.c

# 全志 Allwinner
drivers/cpufreq/sun50i-cpufreq-nvmem.c
drivers/cpufreq/cpufreq-dt.c               # 大部分全志用通用驱动

# MediaTek
drivers/cpufreq/mediatek-cpufreq.c
drivers/cpufreq/mediatek-cpufreq-hw.c

# Qualcomm
drivers/cpufreq/qcom-cpufreq-hw.c
drivers/cpufreq/qcom-cpufreq-nvmem.c

# Samsung Exynos
drivers/cpufreq/exynos-cpufreq.c

# STM32MP
drivers/cpufreq/cpufreq-dt.c               # 使用通用驱动
```

### 1.2 完整 sysfs 接口

路径：`/sys/devices/system/cpu/cpufreq/policy{N}/`

| 接口 | 说明 | 读写 |
|------|------|------|
| `related_cpus` | 同 cluster 下所有 CPU | R |
| `affected_cpus` | 同 cluster 下在线 CPU | R |
| `cpuinfo_transition_latency` | 频率切换延迟 (ns) | R |
| `cpuinfo_max_freq` | 硬件最高频率 | R |
| `cpuinfo_min_freq` | 硬件最低频率 | R |
| `cpuinfo_cur_freq` | 硬件寄存器当前频率 | R |
| `scaling_available_frequencies` | OPP 表频率列表 | R |
| `scaling_available_governors` | 可用 governor 列表 | R |
| `scaling_governor` | 当前 governor | RW |
| `scaling_cur_freq` | 软件最后设置频率 | R |
| `scaling_max_freq` | 软件限制最高频率 | RW |
| `scaling_min_freq` | 软件限制最低频率 | RW |
| `scaling_setspeed` | userspace 模式设频 | RW |
| `stats/time_in_state` | 各频率运行时间 | R |
| `stats/total_trans` | 总变频次数 | R |
| `stats/trans_table` | 频率切换矩阵 | R |

### 1.3 Governor 参数速查

#### ondemand

| 参数 | 默认 | 说明 |
|------|------|------|
| `up_threshold` | 80 | 负载超过此值→跳最高频 |
| `sampling_rate` | — | 负载采样间隔 (μs) |
| `sampling_down_factor` | 1 | 高频时采样率降低倍数 |
| `io_is_busy` | 0 | IO 等待是否计入负载 |
| `ignore_nice_load` | 0 | 是否忽略 nice 进程负载 |
| `powersave_bias` | 0 | 偏向省电 (0-1000) |

#### conservative

| 参数 | 默认 | 说明 |
|------|------|------|
| `up_threshold` | 80 | 升频阈值 |
| `down_threshold` | 20 | 降频阈值 |
| `freq_step` | 5 | 每次变频幅度 (%) |
| `sampling_rate` | — | 采样间隔 (μs) |

#### interactive（Android/嵌入式常见）

| 参数 | 说明 |
|------|------|
| `target_loads` | 各频率的目标负载（逗号分隔的 freq:load 对）|
| `hispeed_freq` | 从低到高的过渡频率 |
| `go_hispeed_load` | 跳到 hispeed 的负载阈值 |
| `above_hispeed_delay` | 超过 hispeed 后继续提频延迟 |
| `min_sample_time` | 提频后最短保持时间 |
| `timer_rate` | 采样间隔 (μs) |
| `timer_slack` | idle 时延长采样间隔 |
| `boost` | 1=强制最高频 |
| `boostpulse_duration` | boost 脉冲持续时间 (μs) |

### 1.4 OPP Table DTS 通用格式

```dts
/* Operating Points v2 标准格式 */
cpu_opp_table: opp-table {
    compatible = "operating-points-v2";
    opp-shared;    /* 同 cluster 的 CPU 共享此表 */

    opp-408000000 {
        opp-hz = /bits/ 64 <408000000>;
        opp-microvolt = <950000 950000 1350000>;     /* <target min max> */
        clock-latency-ns = <40000>;                   /* 切换此频率的延迟 */
        opp-suspend;                                   /* 标记为 suspend 频点 */
    };
    opp-1200000000 {
        opp-hz = /bits/ 64 <1200000000>;
        opp-microvolt = <1150000>;                     /* 简写（只给 target）*/
    };
    opp-1800000000 {
        opp-hz = /bits/ 64 <1800000000>;
        opp-microvolt = <1250000 1250000 1350000>;
        turbo-mode;                                     /* 标记为睿频（可选）*/
    };
};

/* 关联 CPU 节点 */
&cpu0 {
    operating-points-v2 = <&cpu_opp_table>;
    cpu-supply = <&vdd_cpu>;                            /* CPU 电源 regulator */
    /* i.MX 还支持 arm-supply, soc-supply, pu-supply 等 */
};

/* 板级 DTS 禁用频点 */
&cpu_opp_table {
    opp-1800000000 { status = "disabled"; };
};
```

### 1.5 平台特化示例

#### NXP i.MX8M 速度分级

```dts
/* i.MX8M 使用 speed grade fuses 选择 OPP 子集 */
cpu0_opp_table: opp-table {
    compatible = "operating-points-v2";
    opp-shared;
    opp-1200000000 {
        opp-hz = /bits/ 64 <1200000000>;
        opp-microvolt = <850000>;
        opp-supported-hw = <0xd>;    /* bit mask: 速度等级 0,2,3 支持 */
    };
    opp-1800000000 {
        opp-hz = /bits/ 64 <1800000000>;
        opp-microvolt = <1000000>;
        opp-supported-hw = <0x4>;    /* 仅速度等级 2 支持 */
    };
};
```

#### 全志 Allwinner NVMEM 速度分级

```dts
cpu_opp_table: opp-table {
    compatible = "allwinner,sun50i-h6-operating-points";
    nvmem-cells = <&speedbin_efuse>;
    opp-shared;
    opp@480000000 {
        clock-latency-ns = <244144>;
        opp-hz = /bits/ 64 <480000000>;
        opp-microvolt-speed0 = <880000>;
        opp-microvolt-speed1 = <820000>;
        opp-microvolt-speed2 = <800000>;
    };
};
```

---

## 2. Devfreq 完整配置

### 2.1 核心代码

```
drivers/devfreq/devfreq.c                     # Devfreq 核心框架
drivers/devfreq/governor_simpleondemand.c      # simple_ondemand governor
drivers/devfreq/governor_performance.c         # performance governor
drivers/devfreq/governor_userspace.c           # userspace governor
drivers/devfreq/governor_passive.c             # passive governor
```

### 2.2 sysfs 接口

路径：`/sys/class/devfreq/<device>/`

| 接口 | 说明 |
|------|------|
| `cur_freq` | 当前频率 |
| `target_freq` | 目标频率 |
| `min_freq` / `max_freq` | 软件限制频率范围 |
| `available_frequencies` | 可用频率列表 |
| `governor` | 当前 governor |
| `available_governors` | 可用 governor 列表 |
| `polling_interval` | 负载采样间隔 (ms) |
| `load` | 当前负载百分比 |
| `trans_stat` | 变频统计 |
| `userspace/set_freq` | userspace 模式下设频 |

### 2.3 Governor 列表

| Governor | 行为 |
|----------|------|
| `simple_ondemand` | 按负载自动调频，通过 upthreshold/downdifferential 控制 |
| `performance` | 始终最高频 |
| `powersave` | 始终最低频 |
| `userspace` | 手动设频 |
| `passive` | 跟随另一个 devfreq 设备 |

### 2.4 DTS 配置

```dts
gpu: gpu@xxxxx {
    operating-points-v2 = <&gpu_opp_table>;
    devfreq = <&gpu_opp_table>;
    /* 调频阈值 */
    upthreshold = <75>;
    downdifferential = <10>;
};

gpu_opp_table: gpu-opp-table {
    compatible = "operating-points-v2";
    opp-200000000 {
        opp-hz = /bits/ 64 <200000000>;
        opp-microvolt = <900000>;
    };
    opp-800000000 {
        opp-hz = /bits/ 64 <800000000>;
        opp-microvolt = <1100000>;
    };
};
```

---

## 3. Thermal 温控完整配置

### 3.1 核心代码

```
drivers/thermal/thermal_core.c               # Thermal 核心框架
drivers/thermal/gov_power_allocator.c        # power_allocator governor
drivers/thermal/gov_step_wise.c              # step_wise governor
drivers/thermal/gov_fair_share.c             # fair_share governor
drivers/thermal/gov_bang_bang.c              # bang_bang governor
drivers/thermal/cpufreq_cooling.c            # CPU cooling device
drivers/thermal/devfreq_cooling.c            # Devfreq cooling device
```

### 3.2 sysfs 接口

路径：`/sys/class/thermal/thermal_zone{N}/`

| 接口 | 说明 |
|------|------|
| `type` | 设备类型 |
| `temp` | 当前温度 (milli-Celsius) |
| `policy` | 当前温控策略 |
| `available_policies` | 可用策略列表 |
| `mode` | enabled/disabled |
| `trip_point_{N}_temp` | 第 N 个阈值温度 |
| `trip_point_{N}_type` | 阈值类型 (passive/active/critical) |
| `trip_point_{N}_hyst` | 迟滞 |

路径：`/sys/class/thermal/cooling_device{N}/`

| 接口 | 说明 |
|------|------|
| `type` | 类型（如 thermal-cpufreq-0）|
| `max_state` | 最大限制级别 |
| `cur_state` | 当前限制级别（0=不限，越大限制越大）|

### 3.3 DTS 完整示例

```dts
/* 温度传感器 */
tsadc: tsadc@xxxxx {
    compatible = "vendor,soc-tsadc";
    #thermal-sensor-cells = <1>;          /* 多 zone: 1, 单 zone: 0 */
};

/* Thermal Zone 定义 */
thermal_zones {
    cpu_thermal: cpu-thermal {
        polling-delay-passive = <100>;     /* 超阈值采样间隔 ms */
        polling-delay = <1000>;            /* 正常采样间隔 ms */
        sustainable-power = <1500>;        /* power_allocator 功耗预算 mW */
        thermal-sensors = <&tsadc 0>;

        trips {
            cpu_alert0: trip0 {
                temperature = <70000>;      /* 70°C */
                hysteresis = <2000>;
                type = "passive";
            };
            cpu_alert1: trip1 {
                temperature = <85000>;      /* 85°C */
                hysteresis = <2000>;
                type = "passive";
            };
            cpu_crit: trip2 {
                temperature = <115000>;     /* 115°C */
                hysteresis = <2000>;
                type = "critical";          /* 触发重启 */
            };
        };

        cooling-maps {
            map0 {
                trip = <&cpu_alert1>;
                cooling-device = <&cpu0 THERMAL_NO_LIMIT THERMAL_NO_LIMIT>;
                contribution = <1024>;
            };
            map1 {
                trip = <&cpu_alert1>;
                cooling-device = <&gpu THERMAL_NO_LIMIT THERMAL_NO_LIMIT>;
                contribution = <512>;
            };
        };
    };
};
```

### 3.4 power_allocator 调参指南

`power_allocator` 使用 PID 控制器，目标是将温度维持在 `sustainable-power` 对应的热平衡点。

关键参数：

| 参数 | 说明 | 默认 |
|------|------|------|
| `sustainable-power` | 总功耗预算 (mW) | 必须设置 |
| `k_po` | PID 比例增益（正偏差） | 算法内部 |
| `k_pu` | PID 比例增益（负偏差） | 算法内部 |
| `k_i` | PID 积分增益 | 算法内部 |
| `k_d` | PID 微分增益 | 0 |
| `integral_cutoff` | 积分项起效温度偏差 | 0 |

调参方法：
1. 先设 `sustainable-power` 为所有 cooling-device 最大功耗之和的 50-70%
2. 运行典型负载，观察温度是否稳定在目标附近
3. 温度偏高→减小 `sustainable-power`
4. 性能不足→增大 `sustainable-power`
5. 温度振荡→调整 `k_i` / `k_d`

---

## 4. 功耗分析方法

### 4.1 硬件测量

1. **精密功率计**：在电源输入处串联功率计
2. **电流探针**：在 Power Tree 各路串接小电阻 (10-20mΩ)
3. **板载 INA226**：部分开发板自带功耗监测 IC

### 4.2 软件估算

```bash
# 1. 检查时钟使能（未用设备应关闭）
cat /sys/kernel/debug/clk/clk_summary | grep -v " 0 "

# 2. 检查 Power Domain（未用模块应 off）
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary

# 3. 检查 Regulator 状态
cat /sys/kernel/debug/regulator/regulator_summary

# 4. 检查 Runtime PM
grep -r "." /sys/bus/platform/devices/*/power/runtime_status 2>/dev/null | grep -v suspended | head

# 5. CPU idle 统计
cat /sys/devices/system/cpu/cpu0/cpuidle/state*/name
cat /sys/devices/system/cpu/cpu0/cpuidle/state*/time
cat /sys/devices/system/cpu/cpu0/cpuidle/state*/usage
```

### 4.3 功耗优化 checklist

- [ ] 删除不用的外设 DTS 节点或设 `status = "disabled"`
- [ ] 确认 Runtime PM 正常工作（未使用的设备应 suspended）
- [ ] 检查 clock enable_cnt（不用的时钟应关闭）
- [ ] 使用合适的 CPU idle 状态
- [ ] DDR/GPU 使用动态调频
- [ ] 关闭不需要的 regulator (regulator-always-on 是否必要)
- [ ] 使用合适的 IO 电压 (1.8V vs 3.3V)

---

## 5. EAS 能效感知调度

Energy Aware Scheduling (EAS) 是 Linux 5.x+ 的默认能效策略，结合 schedutil governor 使用。

### 5.1 检查 EAS 是否生效

```bash
# 查看能量模型
cat /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_available_preferences 2>/dev/null
ls /sys/kernel/debug/energy_model/ 2>/dev/null

# 确认 schedutil 正在使用
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_governor
# 应该显示 schedutil
```

### 5.2 DTS 能量模型

```dts
/* 在 CPU 节点中定义能量模型 */
&cpu0 {
    capacity-dmips-mhz = <485>;    /* 相对算力（大核=1024 基准下小核的值）*/
    dynamic-power-coefficient = <100>;  /* 动态功耗系数 */
};

&cpu4 {
    capacity-dmips-mhz = <1024>;   /* 大核 */
    dynamic-power-coefficient = <436>;
};
```

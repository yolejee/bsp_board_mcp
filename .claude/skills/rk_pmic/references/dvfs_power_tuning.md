# DVFS 与功耗调优参考

本文档提供 CPUFreq、Devfreq、OPP Table 的详细配置方法和功耗分析方法论。

---

## 1. CPUFreq 完整配置

### 1.1 代码路径

```
drivers/cpufreq/cpufreq_conservative.c    # conservative 策略
drivers/cpufreq/cpufreq_ondemand.c        # ondemand 策略
drivers/cpufreq/cpufreq_interactive.c     # interactive 策略
drivers/cpufreq/cpufreq_userspace.c       # userspace 策略
drivers/cpufreq/cpufreq_performance.c     # performance 策略
kernel/sched/cpufreq_schedutil.c          # schedutil 策略 (EAS)
drivers/cpufreq/cpufreq.c                # core
drivers/cpufreq/cpufreq-dt.c             # platform driver
drivers/cpufreq/rockchip-cpufreq.c       # platform device
drivers/soc/rockchip/rockchip_opp_select.c # 电压表修改接口
```

### 1.2 Menuconfig

```
CPU Power Management  --->
    CPU Frequency scaling  --->
        [*] CPU Frequency scaling
        <*>   CPU frequency translation statistics
        [*]   CPU frequency time-in-state statistics
            Default CPUFreq governor (interactive)  --->
        <*>   'performance' governor
        <*>   'powersave' governor
        <*>   'userspace' governor
        <*>   'ondemand' cpufreq policy governor
        -*-   'interactive' cpufreq policy governor
        <*>   'conservative' cpufreq governor
        [ ]   'schedutil' cpufreq policy governor
        <*>   Generic DT based cpufreq driver
        <*>   Rockchip CPUfreq driver
```

### 1.3 DTS 完整配置

#### Clock 配置

```dts
/* 非大小核 (RK3328/RK3326/PX30) */
cpu0: cpu@0 {
    clocks = <&cru ARMCLK>;
};

/* 大小核 (RK3399) */
cpu_l0: cpu@0   { clocks = <&cru ARMCLKL>; };
cpu_l1: cpu@1   { clocks = <&cru ARMCLKL>; };
cpu_l2: cpu@2   { clocks = <&cru ARMCLKL>; };
cpu_l3: cpu@3   { clocks = <&cru ARMCLKL>; };
cpu_b0: cpu@100 { clocks = <&cru ARMCLKB>; };
cpu_b1: cpu@101 { clocks = <&cru ARMCLKB>; };
```

失败提示：`cpu cpu0: failed to get clock: -2` / `cpufreq-dt: probe failed with error -2`

#### Regulator 配置

```dts
/* 非大小核 */
&cpu0 { cpu-supply = <&vdd_arm>; };

/* 大小核 */
&cpu_l0 { cpu-supply = <&vdd_cpu_l>; };
&cpu_l1 { cpu-supply = <&vdd_cpu_l>; };
&cpu_l2 { cpu-supply = <&vdd_cpu_l>; };
&cpu_l3 { cpu-supply = <&vdd_cpu_l>; };
&cpu_b0 { cpu-supply = <&vdd_cpu_b>; };
&cpu_b1 { cpu-supply = <&vdd_cpu_b>; };
```

注意：未配置 regulator 时，cpufreq 仍可加载但只调频不调压，高频时可能死机。

### 1.4 Interactive Governor 参数详解

```bash
# Interactive 参数目录
/sys/devices/system/cpu/cpu0/cpufreq/interactive/

go_hispeed_load     # 负载 > 该值且频率 < hispeed_freq 时直接跳到 hispeed_freq
hispeed_freq        # 过渡频率，从低频首先跳到此频率
above_hispeed_delay # 频率 > hispeed_freq 时，每次提频前需维持的时间
min_sample_time     # 提频后，降频前需维持的最短时间
target_loads        # 目标负载
timer_rate          # 负载采样间隔 (us)
timer_slack         # CPU idle 后的采样间隔
boost               # 持续 boost 到 hispeed_freq
boostpulse          # 瞬时 boost 到 hispeed_freq
boostpulse_duration # boost 维持时间 (us)
io_is_busy          # IO 等待是否计入 CPU 负载
```

**调优重点：**
- `hispeed_freq`: 选择中间频率，太大太小都会导致频繁跳高频
- `target_loads`: 加大→更容易跑低频→功耗↓性能↓
- `timer_rate`: 加大→更容易跑低频→功耗↓性能↓

### 1.5 用户态接口完整参考

```bash
/sys/devices/system/cpu/cpufreq/policy0/
├── related_cpus                  # 同 cluster 下所有 CPU
├── affected_cpus                 # 同 cluster 下未关闭的 CPU
├── cpuinfo_transition_latency    # 变频切换时间 (ns)
├── cpuinfo_max_freq              # 硬件支持最高频率
├── cpuinfo_min_freq              # 硬件支持最低频率
├── cpuinfo_cur_freq              # 硬件寄存器当前频率
├── scaling_available_frequencies # 系统可用频率列表
├── scaling_available_governors   # 系统可用 governor 列表
├── scaling_governor              # 当前 governor
├── scaling_cur_freq              # 软件最后设置的频率
├── scaling_max_freq              # 软件限制最高频率
├── scaling_min_freq              # 软件限制最低频率
├── scaling_setspeed              # userspace 定频节点
└── stats/
    ├── time_in_state             # 各频率运行时间 (单位 10ms)
    ├── total_trans               # 变频总次数
    └── trans_table               # 各频率间变频次数矩阵
```

---

## 2. Devfreq 完整配置

### 2.1 代码路径

```
drivers/devfreq/governor_simpleondemand.c    # simple ondemand
drivers/devfreq/governor_performance.c       # performance
drivers/devfreq/governor_powersave.c         # powersave
drivers/devfreq/governor_userspace.c         # userspace
drivers/devfreq/devfreq-event.c              # event 框架
drivers/devfreq/event/rockchip-dfi.c         # DDR 读写 cycle 监控
drivers/devfreq/event/rockchip-nocp.c        # 模块访问 DDR 字节数监控
drivers/devfreq/rockchip_dmc.c               # dmc ondemand + DMC driver
drivers/devfreq/rockchip_bus.c               # bus driver
drivers/gpu/arm/.../mali_kbase_devfreq.c     # GPU driver
```

### 2.2 Menuconfig

```
Device Drivers  --->
    [*] Generic Dynamic Voltage and Frequency Scaling (DVFS) support  --->
        -*-   Simple Ondemand
        <*>   Performance
        <*>   Powersave
        <*>   ARM ROCKCHIP BUS DEVFREQ Driver
        <*>   ARM ROCKCHIP DMC DEVFREQ Driver
        [*]   DEVFREQ-Event device Support  --->
            -*-   ROCKCHIP DFI DEVFREQ event Driver
            <*>   ROCKCHIP NoC Probe DEVFREQ event Driver
```

### 2.3 GPU DVFS DTS 配置

```dts
/* DTSI 中 */
gpu: gpu@ff9a0000 {
    compatible = "arm,malit860", "arm,mali-midgard";
    clocks = <&cru ACLK_GPU>;
    clock-names = "clk_mali";
    operating-points-v2 = <&gpu_opp_table>;
    upthreshold = <75>;        /* 升频负载阈值 (默认 90) */
    downdifferential = <10>;   /* 降频差值 (默认 5) */
};

/* 板级 DTS 中 */
&gpu {
    status = "okay";
    mali-supply = <&vdd_gpu>;
};
```

### 2.4 DMC DVFS 场景变频配置

```dts
&dmc {
    status = "okay";
    center-supply = <&vdd_center>;
    system-status-freq = <
        SYS_STATUS_NORMAL       800000    /* 默认场景 */
        SYS_STATUS_REBOOT       528000    /* 重启前 */
        SYS_STATUS_SUSPEND      200000    /* 一级待机 */
        SYS_STATUS_VIDEO_1080P  200000    /* 1080P 视频 */
        SYS_STATUS_VIDEO_4K     600000    /* 4K 视频 */
        SYS_STATUS_VIDEO_4K_10B 800000    /* 4K 10bit */
        SYS_STATUS_PERFORMANCE  800000    /* 跑分 */
        SYS_STATUS_BOOST        400000    /* 触屏 */
        SYS_STATUS_DUALVIEW     600000    /* 双屏 (固定不变频) */
        SYS_STATUS_ISP          600000    /* 拍照 (固定不变频) */
    >;
};
```

场景定义: `include/dt-bindings/clock/rk_system_status.h`

```bash
# 查看当前场景
cat /sys/class/devfreq/dmc/system_status
```

### 2.5 DMC 负载变频配置

```dts
&dmc {
    devfreq-events = <&dfi>;        /* DDR 利用率监控 */
    upthreshold = <40>;             /* 负载>40% 调最高频 */
    downdifferential = <20>;        /* 负载差 20% 降频 */
    auto-min-freq = <400000>;       /* 最低频率 (防闪屏) */
    auto-freq-en = <1>;             /* 使能负载变频 */
};
```

### 2.6 VOP 带宽变频

```dts
&dmc {
    vop-bw-dmc-freq = <
    /* min_bw(MB/s) max_bw(MB/s) freq(KHz) */
        0       577      200000
        578     1701     300000
        1702    99999    400000
    >;
    auto-min-freq = <200000>;   /* 配合 VOP 带宽可降低该值 */
};
```

### 2.7 BUS PLL DVFS

```dts
bus_apll: bus-apll {
    compatible = "rockchip,px30-bus";
    rockchip,busfreq-policy = "clkfreq";   /* 监控 PLL 频率变化 */
    clocks = <&cru PLL_APLL>;
    clock-names = "bus";
    operating-points-v2 = <&bus_apll_opp_table>;
    status = "disabled";
};

bus_apll_opp_table: bus-apll-opp-table {
    compatible = "operating-points-v2";
    opp-shared;
    opp-1008000000 { opp-hz = /bits/ 64 <1008000000>; opp-microvolt = <950000>; };
    opp-1512000000 { opp-hz = /bits/ 64 <1512000000>; opp-microvolt = <1000000>; };
};

/* 板级 */
&bus_apll {
    bus-supply = <&vdd_logic>;
    status = "okay";
};
```

### 2.8 Devfreq 用户态接口

```bash
/sys/class/devfreq/<device>/
├── available_frequencies    # 可用频率
├── available_governors      # 可用 governor
├── cur_freq                 # 当前频率
├── governor                 # 当前 governor
├── load                     # 当前负载 (格式: load@freqHz)
├── max_freq                 # 最高频率限制
├── min_freq                 # 最低频率限制
├── polling_interval         # 负载检测间隔
├── target_freq              # 目标频率
└── trans_stat               # 变频统计
```

---

## 3. OPP Table 高级配置

### 3.1 Leakage 分档调压

```dts
cpu0_opp_table: cpu0-opp-table {
    compatible = "operating-points-v2";
    opp-shared;

    nvmem-cells = <&cpu_leakage>;
    nvmem-cell-names = "cpu_leakage";

    /* leakage 1-10mA → L0 档, 11-254mA → L1 档 */
    rockchip,leakage-voltage-sel = <
        1   10    0
        11  254   1
    >;

    opp-1296000000 {
        opp-hz = /bits/ 64 <1296000000>;
        opp-microvolt = <1350000 1350000 1350000>;      /* 默认 */
        opp-microvolt-L0 = <1350000 1350000 1350000>;   /* 小 leakage */
        opp-microvolt-L1 = <1300000 1300000 1350000>;   /* 大 leakage, 降压 */
        clock-latency-ns = <40000>;
    };
};
```

查看当前 leakage: `dmesg | grep leakage`

### 3.2 PVTM 分档调压

```dts
cpu0_opp_table: opp_table0 {
    compatible = "operating-points-v2";
    opp-shared;

    /* 多工艺支持 */
    nvmem-cells = <&process_version>;
    nvmem-cell-names = "process";

    rockchip,pvtm-voltage-sel = <
        0        14300   0      /* PVTM 0-14300 → L0 */
        14301    15000   1      /* PVTM 14301-15000 → L1 */
        15001    16000   2
        16001    99999   3
    >;

    rockchip,pvtm-freq = <408000>;          /* 采样频率 (KHz) */
    rockchip,pvtm-volt = <1000000>;         /* 采样电压 (uV) */
    rockchip,pvtm-ch = <0 0>;              /* PVTM 通道 */
    rockchip,pvtm-sample-time = <1000>;     /* 采样时间 (us) */
    rockchip,pvtm-number = <10>;            /* 采样个数 */
    rockchip,pvtm-error = <1000>;           /* 允许误差 */
    rockchip,pvtm-ref-temp = <35>;          /* 参考温度 (°C) */
    rockchip,pvtm-temp-prop = <(-18) (-18)>;/* 温度系数 */
    rockchip,thermal-zone = "soc-thermal";

    opp-1608000000 {
        opp-hz = /bits/ 64 <1608000000>;
        opp-microvolt = <1350000 1350000 1350000>;
        opp-microvolt-L0 = <1350000 1350000 1350000>;
        opp-microvolt-L1 = <1350000 1350000 1350000>;
        opp-microvolt-L2 = <1300000 1300000 1350000>;
        opp-microvolt-L3 = <1250000 1250000 1350000>;
    };
};
```

查看当前 PVTM 档位: `dmesg | grep pvtm`

### 3.3 IR-Drop 板级电源纹波补偿

```dts
/* DTSI 中 */
cpu0_opp_table: cpu0-opp-table {
    rockchip,max-volt = <1350000>;     /* 允许最高电压 */
    rockchip,evb-irdrop = <25000>;     /* EVB 板纹波 (uV) */
};

/* 板级 DTS 中 */
&cpu0_opp_table {
    rockchip,board-irdrop = <
    /* MHz   MHz     uV */
        0       815     37500       /* 增加 37500-25000=12500uV */
        816     1119    50000       /* 增加 50000-25000=25000uV */
        1200    1512    75000       /* 增加 75000-25000=50000uV */
    >;
};
```

### 3.4 宽温配置

```dts
&cpu0_opp_table {
    rockchip,temp-hysteresis = <5000>;          /* 迟滞 5°C */
    rockchip,low-temp = <0>;                    /* 低温阈值 0°C */
    rockchip,low-temp-min-volt = <900000>;      /* 低温最低电压 */
    rockchip,low-temp-adjust-volt = <
        0      1800   25000                     /* 低温 0-1800MHz 加压 25mV */
    >;
    rockchip,max-volt = <1250000>;
    rockchip,high-temp = <85000>;               /* 高温阈值 85°C */
    rockchip,high-temp-max-volt = <1200000>;    /* 高温最高电压限制 */
    /* 或使用限频: rockchip,high-temp-max-freq = <1008000>; */
};
```

---

## 4. 功耗分析方法论

### 4.1 DCDC vs LDO 功耗折算

| 类型 | 折算公式 |
|------|---------|
| DCDC | I_battery = V_out × I_out / 效率 / V_battery (效率≈80%-90%) |
| LDO | I_battery = I_out (输入电流=输出电流) |

### 4.2 测量步骤

1. 在每路电源输出端串联 0.01Ω 电阻
2. 测量电阻两端电压差 → I = U/R
3. 使用 PowerMeterage 同时采集多路 (最多 20 路)
4. 将所有路折算到电池端，加总对比实测总功耗

### 4.3 各路电源分析重点

| 电源 | 分析要点 |
|------|---------|
| VDD_CPU/ARM | 确认 OPP table 电压正确；检查 CPU 负载/中断；确认定频测试电压 |
| VDD_GPU | 确认 OPP table；检查 GPU 负载 (`cat load`)；devfreq governor |
| VDD_LOGIC | 检查 clk_summary 各模块频率；检查 pm_genpd_summary PD 开关状态 |
| VCC_DDR | DDR 频率、负载、低功耗配置 (pd_idle/sr_idle/odt)；颗粒差异 |
| VCC_IO | 外设工作状态；IO 管脚电平是否与外设匹配 |

### 4.4 常见场景分析

| 场景 | 预期状态 | 分析重点 |
|------|---------|---------|
| 静态桌面 | CPU/GPU/DDR 最低频，VDD 最低压 | 基准功耗，优先优化 |
| 视频播放 | VPU/RKVDEC 工作，GPU 关闭 | DDR 频率 + VDD_LOGIC |
| 游戏 | CPU + GPU 高负载 | CPU/GPU 负载、频率、电压 |
| 二级待机 | VDD_CPU/GPU 关闭，VDD_LOG 最低 | IO/DDR/外设功耗 |

### 4.5 CPU 功耗优化命令集

```bash
# 关闭部分核
echo 0 > /sys/devices/system/cpu/cpu2/online
echo 0 > /sys/devices/system/cpu/cpu3/online

# 限制最高频率
echo 1200000 > /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq

# CPUSET 绑核 (大小核架构)
mkdir /dev/cpuset/little
echo 0-3 > /dev/cpuset/little/cpus
echo 1111 > /dev/cpuset/little/tasks

# CPUCTL 带宽限制 (需 CONFIG_CFS_BANDWIDTH)
mkdir /dev/cpuctl/mygroup
echo 10000 > /dev/cpuctl/mygroup/cpu.cfs_quota_us
echo 5000 > /dev/cpuctl/mygroup/cpu.cfs_period_us
echo 1111 > /dev/cpuctl/mygroup/tasks

# 查看 CPU 负载
top -m 5 -t

# 查看中断
cat /proc/interrupts

# 查看各频率运行时间
cat /sys/devices/system/cpu/cpu0/cpufreq/stats/time_in_state
```

### 4.6 各平台 CPU 最高频率参考

| 平台 | ARM 核 | 最高主频 |
|------|--------|---------|
| RK312x | 4×A7 | 1200MHz |
| RK322x | 4×A7 | 1464MHz |
| RK3288 | 4×A17 | 1608MHz |
| RK3328 | 4×A53 | 1296MHz |
| RK3368 | 4×A53 + 4×A53 | 1512MHz(big) + 1200MHz(little) |
| RK3399 | 2×A72 + 4×A53 | 1800MHz(big) + 1416MHz(little) |

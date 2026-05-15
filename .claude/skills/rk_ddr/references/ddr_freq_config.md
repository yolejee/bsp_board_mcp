# DDR 频率配置完整参考

## 1. Kernel 4.4+ DMC 完整 DTS 配置

### 1.1 RK3399 完整 DMC 配置示例

```dts
/* rk3399.dtsi 中的 DMC 节点定义 */
dmc: dmc {
    compatible = "rockchip,rk3399-dmc";
    devfreq-events = <&dfi>;
    interrupts = <GIC_SPI 1 IRQ_TYPE_LEVEL_HIGH 0>;
    clocks = <&cru SCLK_DDRCLK>;
    clock-names = "dmc_clk";
    ddr_timing = <&ddr_timing>;

    /* DDR 利用率超过 40% 开始升频 (auto-freq-en=1 时有效) */
    upthreshold = <40>;
    /* DDR 利用率低于 20% 开始降频 (auto-freq-en=1 时有效) */
    downdifferential = <20>;

    system-status-freq = <
        /*system status         freq(KHz)*/
        /* auto-freq-en=0 时: 非下列场景均使用此频率 */
        /* auto-freq-en=1 时: NORMAL 完全被负载变频替代, 最低频率由 auto-min-freq 决定 */
        SYS_STATUS_NORMAL       800000

        /* reboot 前的 DDR 频率 */
        SYS_STATUS_REBOOT       528000

        /* 一级待机的 DDR 频率 */
        SYS_STATUS_SUSPEND      200000

        /* 1080P 视频时的 DDR 频率 */
        SYS_STATUS_VIDEO_1080P  300000

        /* 4K 视频时的 DDR 频率 */
        SYS_STATUS_VIDEO_4K     600000

        /* 4K 10bit 视频时的 DDR 频率 */
        SYS_STATUS_VIDEO_4K_10B 800000

        /* 性能模式时的 DDR 频率 */
        SYS_STATUS_PERFORMANCE  800000

        /* 触屏时的 DDR 频率 (改善触屏响应) */
        SYS_STATUS_BOOST        400000

        /* 双屏显示时的 DDR 频率 */
        SYS_STATUS_DUALVIEW     600000

        /* ISP 时的 DDR 频率 */
        SYS_STATUS_ISP          600000
    >;

    /* VOP 带宽需求驱动 DDR 提频 (auto-freq-en=1 时有效) */
    vop-bw-dmc-freq = <
        /* min_bw(MB/s) max_bw(MB/s) freq(KHz) */
        0       577      200000
        578     1701     300000
        1702    99999    400000
    >;

    /* 负载变频最低频率 (KHz) */
    auto-min-freq = <400000>;

    /* 1=开启负载变频, 0=关闭负载变频
     * 开启后: NORMAL 场景完全被负载变频替代, 其他场景频率作为最低频率
     * 关闭后: 只有场景变频生效 */
    auto-freq-en = <1>;

    status = "disabled";
};

/* rk3399-evb.dtsi 中的板级覆盖 */
&dfi {
    status = "okay";
};

&dmc {
    status = "okay";
    center-supply = <&vdd_center>;  /* 实际 DDR 供电 regulator */
};
```

### 1.2 RK3399 dmc_opp_table 示例

```dts
dmc_opp_table: opp-table3 {
    compatible = "operating-points-v2";

    opp-200000000 {
        opp-hz = /bits/ 64 <200000000>;
        opp-microvolt = <825000>;  /* vdd_center 电压 */
    };
    opp-300000000 {
        opp-hz = /bits/ 64 <300000000>;
        opp-microvolt = <850000>;
    };
    opp-400000000 {
        opp-hz = /bits/ 64 <400000000>;
        opp-microvolt = <850000>;
    };
    opp-528000000 {
        opp-hz = /bits/ 64 <528000000>;
        opp-microvolt = <900000>;
    };
    opp-600000000 {
        opp-hz = /bits/ 64 <600000000>;
        opp-microvolt = <900000>;
    };
    opp-800000000 {
        opp-hz = /bits/ 64 <800000000>;
        opp-microvolt = <900000>;
    };
    opp-928000000 {
        opp-hz = /bits/ 64 <928000000>;
        opp-microvolt = <900000>;
        status = "disabled";  /* 默认关闭, 需要时删除此行或改为 okay */
    };
};
```

### 1.3 RK3368 dmc_opp_table 示例 (vdd_logic)

```dts
dmc_opp_table: opp_table2 {
    compatible = "operating-points-v2";

    opp-192000000 {
        opp-hz = /bits/ 64 <192000000>;
        opp-microvolt = <1100000>;  /* vdd_logic 电压 */
    };
    opp-300000000 {
        opp-hz = /bits/ 64 <300000000>;
        opp-microvolt = <1100000>;
    };
    opp-396000000 {
        opp-hz = /bits/ 64 <396000000>;
        opp-microvolt = <1100000>;
    };
    opp-528000000 {
        opp-hz = /bits/ 64 <528000000>;
        opp-microvolt = <1100000>;
    };
    opp-600000000 {
        opp-hz = /bits/ 64 <600000000>;
        opp-microvolt = <1100000>;
    };
};
```

## 2. Kernel 3.10 DDR 变频配置

### 2.1 clk_ddr_dvfs_table 完整示例 (RK3288)

```dts
&clk_ddr_dvfs_table {
    /* 频率-电压表: DDR 频率 ≤ 指定频率时使用对应电压 */
    operating-points = <
        /* KHz    uV */
        200000 1050000
        300000 1050000
        400000 1100000
        533000 1150000
    >;

    /* 场景频率表 */
    freq-table = <
        /*status                freq(KHz)*/
        SYS_STATUS_NORMAL       400000
        SYS_STATUS_SUSPEND      200000
        SYS_STATUS_VIDEO_1080P  240000
        SYS_STATUS_VIDEO_4K     400000
        SYS_STATUS_VIDEO_4K_60FPS 400000
        SYS_STATUS_PERFORMANCE  528000
        SYS_STATUS_DUALVIEW     400000
        SYS_STATUS_BOOST        324000
        SYS_STATUS_ISP          400000
    >;

    /* VOP 带宽驱动频率 (auto-freq=1 时有效) */
    bd-freq-table = <
        /* bandwidth   freq */
        5000           800000
        3500           456000
        2600           396000
        2000           324000
    >;

    /* 负载变频频率表格 */
    auto-freq-table = <
        240000
        324000
        396000
        528000
    >;

    /* 1=开启负载变频, 0=关闭 */
    auto-freq = <1>;

    /* VOP dclk 模式: 0=standard, 1=never divided, 2=always divided */
    vop-dclk-mode = <0>;

    status = "okay";
};
```

### 2.2 Kernel 3.10 与 4.4 关键差异

| 特性 | Kernel 3.10 | Kernel 4.4+ |
|------|-------------|-------------|
| 配置节点 | clk_ddr_dvfs_table | dmc + dmc_opp_table |
| 场景变频+负载变频 | 场景变频期间不做负载变频 | 场景频率作为最低值,叠加负载变频 |
| 频率匹配 | 频率可任意设置 | 频率必须匹配 opp-table |
| supply 属性 | 不需要 | 需要 center-supply |
| dfi 依赖 | 无 | dfi 必须 okay |

## 3. Kernel 3.0 DDR 变频配置

```c
/* board-rk30-sdk.c */
static struct cpufreq_frequency_table dvfs_ddr_table[] = {
    /* .frequency = 频率(KHz) + 场景标记 */
    /* .index = 对应电压(uV) */
    {.frequency = 200 * 1000 + DDR_FREQ_SUSPEND, .index = 1050 * 1000},
    {.frequency = 300 * 1000 + DDR_FREQ_VIDEO,   .index = 1050 * 1000},
    {.frequency = 400 * 1000 + DDR_FREQ_NORMAL,  .index = 1125 * 1000},
    {.frequency = CPUFREQ_TABLE_END},
};
/* 只有 3 个场景: SUSPEND, VIDEO, NORMAL */
/* 定频: 注释掉其他, 只留 DDR_FREQ_NORMAL */
```

## 4. 平台特化频率配置

### 4.1 RV1126/RV1109/RK356x 4 频点机制

Loader 阶段确定 4 个频率点 (通过串口 log 查看):
```
change to: 324MHz
change to: 528MHz
change to: 780MHz
change to: 1560MHz(final freq)
```

最高频率由 DDR bin 名称体现: `rk3568_ddr_1560MHz_v1.04.bin`

**修改最高频率步骤**:
1. 修改 `rkbin/RKBOOT/RK3568MINIALL.ini` 中 DDR bin 指向
2. DTS 中 dmc_opp_table 频率对应修改

**修改 loader 频率可用工具**: `rkbin/tools/ddrbin_tool` (参考 `tools/ddrbin_tool_user_guide.txt`)

### 4.2 RK3326S/PX30S 4 频点机制

由 DDR params 节点 + px30s_dmc_opp_table 共同决定:

```dts
/ {
    lpddr4_params: lpddr4-params {
        /* freq_0 is final frequency, unit: MHz */
        freq_0 = <924>;   /* 最终运行频率 */
        freq_1 = <328>;
        freq_2 = <666>;
        freq_3 = <786>;
    };
};

px30s_dmc_opp_table: px30s-dmc-opp-table {
    compatible = "operating-points-v2";

    opp-328000000 {
        opp-hz = /bits/ 64 <328000000>;
        opp-microvolt = <1000000>;
    };
    opp-666000000 {
        opp-hz = /bits/ 64 <666000000>;
        opp-microvolt = <1000000>;
    };
    opp-786000000 {
        opp-hz = /bits/ 64 <786000000>;
        opp-microvolt = <1000000>;
    };
    opp-924000000 {
        opp-hz = /bits/ 64 <924000000>;
        opp-microvolt = <1000000>;
    };
    /* 1056M only for LP4 */
    opp-1056000000 {
        opp-hz = /bits/ 64 <1056000000>;
        opp-microvolt = <1000000>;
        status = "disabled";
    };
};
```

切换到 1056MHz: 修改 freq_0=1056, disabled 旧频点, 使能 1056M 频点。

### 4.3 RK3399 LPDDR4 928MHz 开启方法

1. 修改 `RKBOOT/RK3399MINIALL.ini` 选择 933MHz DDR bin
2. dmc_opp_table 中删除 `opp-928000000` 的 `status = "disabled"`
3. system-status-freq 中将 856000 改为 928000

### 4.4 center-supply 对照表

| 平台 | center-supply 默认值 |
|------|---------------------|
| RK3399 | `<&vdd_center>` |
| RK3588 | `<&vdd_ddr_s0>` |
| RK3568/RV1126/PX30 | `<&vdd_logic>` |

## 5. DDR bin 路径参考

| 芯片 | DDR bin 路径 |
|------|-------------|
| RK1808 | `rkbin/bin/rk1x/rk1808_ddr_XXXMHz_vX.XX.bin` |
| RK3288 | `rkbin/bin/rk32/rk3288_ddr_400MHz_vX.XX.bin` |
| RK322x | `rkbin/bin/rk32/rk322x_ddr_300MHz_vX.XX.bin` |
| RK3308 | `rkbin/bin/rk33/rk3308_ddr_XXXMHz_uartX_mX_vX.XX.bin` |
| PX30 | `rkbin/bin/rk33/px30_ddr_333MHz_vX.XX.bin` |
| RK3399 | `rkbin/bin/rk33/rk3399_ddr_XXXMHz_vX.XX.bin` |
| RK3568 | 由 `RKBOOT/RK3568MINIALL.ini` 指定 |
| RK3588 | 由 `RKBOOT/RK3588MINIALL.ini` 指定 |

## 6. DDR 容量修改方法

### 6.1 U-Boot 代码修改 (评估用)

位置: `arch/arm/mach-rockchip/param.c` 的 `param_parse_ddr_mem()` 函数

```c
struct memblock *param_parse_ddr_mem(int *out_count)
{
    ......
    //修改DDR容量信息
    count = 1;                            // DRAM 区域数量
    t->u.ddr_mem.count = count;
    t->u.ddr_mem.bank[0] = 0x0;           // Region 0 base
    t->u.ddr_mem.bank[0 + count] = 0x40000000 - 0x0;  // Region 0 size (1GB)
    t->u.ddr_mem.hash = 0;                // 必须设为 0
    //修改结束

    count = t->u.ddr_mem.count;
    ......
}
```

**注意**: 改大容量会因无真实存储器导致系统异常,一般只用于改小评估。

### 6.2 多 Region 示例

```c
count = 2;
t->u.ddr_mem.count = count;
t->u.ddr_mem.bank[0] = 0x0;
t->u.ddr_mem.bank[0 + count] = 0x40000000;   // Region 0: 0~1GB
t->u.ddr_mem.bank[1] = 0x70000000;
t->u.ddr_mem.bank[1 + count] = 0x10000000;   // Region 1: 1.75~2GB
t->u.ddr_mem.hash = 0;
```

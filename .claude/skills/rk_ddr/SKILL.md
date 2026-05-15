---
name: rk_ddr
description: "Rockchip 瑞芯微平台 DDR 内存子系统技能。覆盖 RK3588/RK3568/RK3566/RK3399/RK3288/RK3328/PX30/RV1126/RK3308 等全系列芯片的 DDR 初始化、频率配置、DMC 变频、容量管理、带宽监控、ECC、稳定性验证与问题排查。触发关键词：DDR、DDR3、DDR4、LPDDR3、LPDDR4、LPDDR4X、LPDDR5、DRAM、DDR 频率、DDR 变频、DDR 定频、DMC、dmc_opp_table、DDR 带宽、rk_msch_probe、DDR 初始化、DDR bin、stressapptest、memtester、DDR 拷机、DDR 花屏、DDR 死机、DDR ECC、de-skew、DQ、DQS、DDR 走线、VCC_DDR、self-refresh、sr_idle、DDR 兼容、场景变频、ddr_freq_scan。当用户在 Rockchip 平台遇到 DDR 相关的任何问题时触发本技能。"
---

# Rockchip DDR 内存子系统技能

## 1. DDR 类型与平台支持

### 1.1 支持的 DDR 类型

| DDR 类型 | 典型平台 | 典型电压 (VCC_DDR) |
|---------|---------|-------------------|
| DDR3 | RK3288, RK3368, RK3308, RK322x | 1.5V |
| DDR4 | RK3568 | 1.2V |
| LPDDR2 | RK3308, RV1108 | 1.2V |
| LPDDR3 | RK3399, RK3288, PX30, RV1126 | 1.2V |
| LPDDR4/4X | RK3399, RK3566/RK3568, RK3588 | 1.1V |
| LPDDR5/5X | RK3588 | 1.05V |

### 1.2 DDR 通道架构

- **单通道**: RK3288(32bit), RK3326/PX30(32bit/16bit), RK3308(16bit), RV1108(16bit)
- **双通道**: RK3399(通道a+b, 各32bit), RK3568(32bit)
- **四通道**: RK3588(CH0-CH3)

容量 = 各通道 Size 之和。

## 2. DDR 打印信息解读

### 2.1 Loader 打印（串口可见，adb 不可见）

```
DDR Version 1.05 20170712   # DDR 初始化代码版本
In
SRX                          # 有 SRX=热重启; 无 SRX=冷开机
Channel a: DDR3 400MHz       # DDR 类型和初始化频率
Bus Width=32 Col=10 Bank=8 Row=15 CS=1 Die Bus-Width=16 Size=1024MB
Channel b: DDR3 400MHz
Bus Width=32 Col=10 Bank=8 Row=15 CS=1 Die Bus-Width=16 Size=1024MB
Memory OK                    # Channel a 自测通过
Memory OK                    # Channel b 自测通过
OUT                          # 退出 DDR 初始化
```

**关键字段**: Bus Width(总线位宽), Col(列), Bank, Row(行), CS(片选), Die Bus-Width(颗粒位宽), Size(容量)

**注意**: Die Bus-Width 比实际大不影响; 比实际小会引起死机。

### 2.2 Kernel 4.4 DMC 打印

kernel 4.4 中 DDR 容量信息不在 kernel 打印，需看 loader 打印。DMC 驱动加载成功后可通过 devfreq 接口查询。

### 2.3 查看 DDR 容量

```bash
cat /proc/meminfo | grep MemTotal
# MemTotal 会比实际容量小一些，往上取到标准容量即可
# 512MB ≈ 533504kB, 1GB ≈ 1048576kB, 2GB ≈ 2097152kB, 4GB ≈ 4194304kB
```

### 2.4 查看 DDR 厂商 ID

仅 LPDDR 类型支持（DDR2/3/4 无厂商 ID）。

```bash
# 开启 dmcdbg 节点 (RK356x 示例):
# 在 rk3568.dtsi 中: dmcdbg: dmcdbg { compatible = "rockchip,rk3568-dmcdbg"; status = "okay"; };

cat /proc/dmcdbg/dmcinfo
# DramType: LPDDR4
# Dram ID: MR5=0x1,MR6=0x0,MR7=0x1   # MR5 = 厂商 ID
```

**常见 MR5 厂商 ID**: 0x1=Samsung, 0x6=SK hynix, 0xff=Micron, 0x13=CXMT(长鑫), 0x1a=紫光展锐, 0x9=ESMT, 0xfd=AP Memory

## 3. DDR 变频机制

→ 完整 DMC DTS 配置示例与参数详解见 `references/ddr_freq_config.md`

### 3.1 Kernel 4.4+ DMC 变频架构

DDR 变频由 DMC (Dynamic Memory Controller) 驱动控制，包含两种策略：

**场景变频 (Scene-based)**:
- 进入指定场景（视频/ISP/双屏等）时切换到对应频率
- 频率由 `system-status-freq` 中 `SYS_STATUS_XXX` 定义
- `auto-freq-en=1` 时，场景频率作为最低频率

**负载变频 (Load-based)**:
- 根据 DDR 带宽利用率动态调频
- 由 `upthreshold` (升频阈值) 和 `downdifferential` (降频差值) 控制
- `auto-freq-en=1` 时开启

### 3.2 DMC DTS 核心配置 (Kernel 4.4+)

```dts
&dfi {
    status = "okay";  /* 必须与 dmc 保持一致 */
};

&dmc {
    status = "okay";
    center-supply = <&vdd_center>;  /* DDR 供电 regulator，平台相关 */
    /* RK3399: vdd_center, RK3588: vdd_ddr_s0, RK3568/RV1126/PX30: vdd_logic */

    upthreshold = <40>;        /* DDR 利用率超过 40% 升频 */
    downdifferential = <20>;   /* DDR 利用率低于 20% 降频 */

    system-status-freq = <
        SYS_STATUS_NORMAL       800000    /* 默认频率 (KHz) */
        SYS_STATUS_REBOOT       528000
        SYS_STATUS_SUSPEND      200000
        SYS_STATUS_VIDEO_1080P  300000
        SYS_STATUS_VIDEO_4K     600000
        SYS_STATUS_VIDEO_4K_10B 800000
        SYS_STATUS_PERFORMANCE  800000
        SYS_STATUS_BOOST        400000
        SYS_STATUS_DUALVIEW     600000
        SYS_STATUS_ISP          600000
    >;

    auto-min-freq = <400000>;  /* 负载变频最低频率 (KHz) */
    auto-freq-en = <1>;        /* 1=开启负载变频, 0=关闭 */
};
```

### 3.3 dmc_opp_table 频率电压表

```dts
dmc_opp_table: opp-table3 {
    compatible = "operating-points-v2";
    opp-200000000 {
        opp-hz = /bits/ 64 <200000000>;
        opp-microvolt = <825000>;  /* 对应电压 */
    };
    opp-800000000 {
        opp-hz = /bits/ 64 <800000000>;
        opp-microvolt = <900000>;
    };
};
```

**重要规则**:
- 频率小于最小 opp-hz 时，按最小 opp-hz 运行
- 频率不在表中时向上取整到最近的 opp-hz
- 频率超过最大 opp-hz 时，只按最大 opp-hz 运行

### 3.4 Loader 频率匹配

**RV1126/RV1109/RK356x**: Loader 阶段确定 4 个频率点，kernel DMC 的频率必须与之匹配。

```
# Loader 串口 log 示例:
change to: 324MHz
change to: 528MHz
change to: 780MHz
change to: 1560MHz(final freq)
```

dmc_opp_table 只能定义这 4 个频率。不匹配会报错:
```
rockchip-dmc dmc: Get wrong frequency, Request 1056000000, Current 924000000
```

**RK3568/RK3588**: 新平台 kernel DMC 驱动自动获取 loader 支持的频率，无需手工匹配。

修改 loader 频率: 修改 `rkbin/RKBOOT/RKxxxxMINIALL.ini` 中 DDR bin 路径指向目标频率。

### 3.5 center-supply 缺失问题

DMC 节点缺少 `center-supply` 会导致驱动加载失败：
```
rockchip-dmc dmc: Cannot get the regulator "center"
```
需根据实际硬件电路配置正确的 regulator。

## 4. DDR 定频方法

### 4.1 命令行定频 (Kernel 4.4+)

```bash
# 查看支持的频率
cat /sys/class/devfreq/dmc/available_frequencies

# 定频到指定频率
echo userspace > /sys/class/devfreq/dmc/governor
echo 300000000 > /sys/class/devfreq/dmc/min_freq
echo 300000000 > /sys/class/devfreq/dmc/userspace/set_freq
```

### 4.2 命令行定频 (Kernel 3.10)

```bash
# 需打开 pm_tests: menuconfig -> System Type -> /sys/pm_tests/ support
echo set clk_ddr 300000000 > /sys/pm_tests/clk_rate
```

### 4.3 DTS 定频 (开机固定频率)

```dts
&dmc {
    status = "okay";
    system-status-freq = <
        SYS_STATUS_NORMAL  666000  /* 只留 NORMAL，设为目标频率 */
    >;
    auto-min-freq = <666000>;
    auto-freq-en = <0>;  /* 必须关闭负载变频 */
};
```

**三步定频**: (1) auto-freq-en=0, (2) 只留 SYS_STATUS_NORMAL, (3) 确保目标频率在 dmc_opp_table 中有对应电压。

## 5. DDR 带宽监控

### 5.1 简单查看 (Kernel 4.4+)

```bash
cat /sys/class/devfreq/dmc/load
# 输出: 11@396000000Hz  → 当前带宽利用率 11%，频率 396MHz
```

### 5.2 详细带宽工具 rk_msch_probe

**使用前提**:
1. **切换 governor**: `echo userspace > /sys/class/devfreq/dmc/governor`
2. **DDR 定频**: `echo 780000000 > /sys/class/devfreq/dmc/userspace/set_freq`
3. **kernel 需开启 CONFIG_DEVMEM=y**

**使用命令**:
```bash
rk-msch-probe -c rk356x -d 1000
# -c 芯片平台名, -d 采样间隔(ms), -f DDR频率(MHz,可选), -t 测试轮次
```

**输出字段说明**:

| 字段 | 含义 |
|------|------|
| LOAD | 总带宽及利用率 |
| RD | 读带宽及占比 |
| WR | 写带宽及占比 |
| ACT (access:active) | 每个 active 命令后的读写次数，值越大=地址越连续，越好 |
| srex | self-refresh 状态时间占比 |
| pdex | power-down 状态时间占比 |
| LP/LOW POWER | 低功耗状态总时间占比 |

RK3588 输出扩展为 ALL + CH0-CH3 四通道。

## 6. DDR 省电模式检测

### 6.1 Self-Refresh (自刷新)

测量 CKE 信号：**CKE 低电平 > 7.8μs** → 进入自刷新。

### 6.2 Auto Power-Down

测量 CKE 信号: **CKE 低电平 < 7.8μs** (DDR3/DDR4) 或 **< 3.9μs** (LPDDR2/3/4) → auto power-down。

表现为 CKE 周期性低电平(接近界限值)然后短暂拉高再低。

## 7. DDR 稳定性验证

→ 完整验证流程、工具参数和脚本见 `references/ddr_debug_verification.md`

### 7.1 验证流程概要

```
确认容量 → 定频拷机(最高频) → 变频拷机 → Reboot 拷机 → Sleep 拷机(LPDDR4必做)
```

每项测试至少 **12 小时**。

### 7.2 测试工具

**stressapptest** (粗筛选，快速报错):
```bash
# 申请总容量 1/8 进行测试，12h = 43200s
/data/stressapptest -s 43200 -i 4 -C 4 -W --stop_on_errors -M 128
# PASS: "Status: PASS - please verify no corrected errors"
# FAIL: "Status: FAIL - test discovered HW problems"
```

**memtester** (细筛选，信号覆盖全面):
```bash
/data/memtester 128m
# 正常: 所有项显示 ok，持续循环
# 异常: 打印 FAILURE 并退出 (资源包中修改版)
```

### 7.3 定频拷机 (Kernel 4.4+)

```bash
# 使用 ddr_freq_scan.sh 定频
/data/ddr_freq_scan.sh 800000000
# 然后分别运行 stressapptest 和 memtester，各 12h+
```

### 7.4 变频拷机

```bash
# 后台运行 memtester
/data/memtester 128m > /data/memtester_log.txt &
# 执行变频扫描
/data/ddr_freq_scan.sh
# 确认 memtester 进程存在且变频 log 正常打印
ps | grep memtester
```

### 7.5 确定最高可运行频率

1. 添加各种高频的频率电压表
2. 从高频到低频运行 stressapptest，报错则降频
3. 通过后再运行 memtester 确认

## 8. DDR 问题排查

→ 更多排查手段和案例见 `references/ddr_debug_verification.md`

### 8.1 判断是否为 DDR 问题

| 现象 | 判断 |
|------|------|
| Loader DDR 初始化报错 | **一定是 DDR 问题** |
| DDR 容量/行列/bank 信息错误 | 大概率是 DDR 问题 |
| Panic 地址每次不同 | 可能是 DDR 或电源问题 |
| Panic 地址固定 | 基本不是 DDR 问题 |
| 死机时显示花屏 | DDR 变频或电源问题 |
| 死机时显示重影 | DDR 信号质量 (参考层) 问题 |
| 死机时显示正常 | DDR 可能正常，但不排除 |

### 8.2 排查实验

```
1. CPU/GPU 降频抬压 → 改善 → 电源问题
2. 关闭 DDR 变频 → 改善 → DDR 变频问题
3. DDR 降频到 200MHz → 改善 → DDR 信号质量问题
```

### 8.3 三大根因

**电源问题**:
- 电容不足/远离芯片/分布不合理
- 电源 feedback 回路未从末端引回
- 敷铜路径太窄
- LQFP 封装芯片下方 GND 堆锡不足

**信号质量问题**:
- DDR 走线不等长 (影响 setup/hold time)
- 线间距过窄 (串扰)
- T 型拓扑分支不等长
- 信号参考层不完整

**颗粒问题**:
- 白牌颗粒良率无保证
- 特殊渠道颗粒驱动强度偏弱
- 特定颗粒兼容性 (如 Hynix 4Gb C die DDR3)

### 8.4 Loader 初始化报错对照

| 报错信息 | 原因 |
|---------|------|
| `rd addr 0x... = 0x...` | 焊接问题，用 DDR 测试工具定位 |
| `16bit error!!!` / `W FF != R` | 基本读写错误，大概率焊接问题 |
| `unknow device` | 无法探测 DRAM 类型，检查焊接 |
| 特殊容量 (768MB/1.5GB/3GB) 异常 | 更新最新 loader |

### 8.5 常用修复手段

| 手段 | 适用场景 |
|------|---------|
| 降低 DDR 频率 | 信号质量问题初步验证 |
| 加强/减弱驱动强度/ODT | 信号质量微调 |
| 提高 VCC_DDR 电压 | 重影/DDR3 信号异常 (可临时升至 1.6V) |
| 改变 RZQ 阻值 | 个别 220ball LPDDR3 |
| 关闭 pd_idle / sr_idle | 白牌颗粒省电模式不兼容 |
| Bypass DRAM DLL | 重影+白牌颗粒 |
| DDR 测试工具 March 专项 | 存储单元问题检测 |

## 9. DDR ECC

### 9.1 RK3568 ECC 支持

- **类型**: SEC/DED ECC (纠正 1bit 错误，检测 2bit 错误)
- **方式**: SideBand ECC — 需额外贴一颗 ECC 颗粒存放 ECC 数据
- **ECC 颗粒要求**: 类型、Row/Col/Bank 需与数据颗粒一致
- **使能**: DDR_ECC_DQ0-7 有贴颗粒时自动使能
- **数据宽度**: 32bit DQ → 7bit ECC, 16bit DQ → 6bit ECC, 8bit DQ → 5bit ECC

### 9.2 HAL API (裸系统)

```c
#define HAL_DDR_ECC_MODULE_ENABLED  // hal_conf.h 使能

HAL_DDR_ECC_Init(&eccInfo);            // 初始化
HAL_DDR_ECC_GetInfo(&eccInfo);         // 获取累计 CE/UE 数量
// eccInfo.ce_count = 可纠正单 bit 错误数
// eccInfo.ue_count = 不可纠正双 bit 错误数
```

支持**轮询**和**中断** (DDR_ECC_CE_IRQn / DDR_ECC_UE_IRQn) 两种获取方式。

## 10. De-skew 调整

用于补偿 DDR PCB 走线不等长。DDR PHY 内部延迟单元可独立控制各信号线延迟。

### 10.1 Kernel 中调整 (RK322xh/RK3328)

修改 DTS:
- `arch/arm64/boot/dts/rk322xh-dram-default-timing.dtsi`
- `arch/arm64/boot/dts/rk322xh-dram-2layer-timing.dtsi`

使用 "deskew 自动扫描工具" 获取 mid 值后填入。

### 10.2 Loader 中调整 (RK3308)

使用 `3308_deskew.exe` 工具将扫描结果写入 DDR bin。

## 11. DDR 电压修改

### 11.1 命令行临时修改

```bash
# Kernel 4.4 (需打开 pm_tests):
echo set vdd_center 900000 > /sys/pm_tests/clk_volt   # RK3399
echo set vdd_logic 1200000 > /sys/pm_tests/clk_volt   # 其他平台

# Kernel 3.10 (需打开 pm_tests):
echo set vdd_center 900000 > /sys/pm_tests/clk_volt   # RK3399
echo set vdd_logic 1200000 > /sys/pm_tests/clk_volt   # 其他
```

### 11.2 DTS 永久修改

修改 dmc_opp_table 中对应频率的 `opp-microvolt` 值。
新增频率超出表格最大 opp-hz 时必须添加对应电压项。

## 12. 常用命令速查

```bash
# 查看 DDR 容量
cat /proc/meminfo | grep MemTotal

# 查看当前 DDR 频率和状态
cat /sys/class/devfreq/dmc/cur_freq
cat /sys/class/devfreq/dmc/available_frequencies
cat /sys/class/devfreq/dmc/governor

# DDR 定频
echo userspace > /sys/class/devfreq/dmc/governor
echo 780000000 > /sys/class/devfreq/dmc/userspace/set_freq

# 查看 DDR 带宽利用率
cat /sys/class/devfreq/dmc/load

# DDR 厂商信息 (需 dmcdbg 节点)
cat /proc/dmcdbg/dmcinfo

# 关闭/启用 DDR 变频 (DTS 中修改)
# &dmc { status = "disabled"; };  → 关闭
# &dmc { status = "okay"; };     → 开启
```

## 13. 故障排查速查表

| 问题 | 排查方向 | 参考章节 |
|------|---------|---------|
| Loader 阶段 DDR 初始化报错 | 焊接、颗粒兼容 | §8.4 |
| DMC 驱动加载失败 | center-supply 缺失或 dfi disabled | §3.5 |
| dmc_opp_table 频率不匹配 | Loader 频率与 DTS 不一致 | §3.4 |
| DDR 变频时死机 | 定频排查；检查频率电压表 | §4, §8.2 |
| 系统随机死机(panic地址不固定) | DDR 或电源问题 | §8.1 |
| 死机花屏 | DDR 变频问题或电源异常 | §8.3 |
| 死机重影 | 参考层不完整/信号质量 | §8.3 |
| DDR 容量识别错误 | 检查 loader 打印的详细信息 | §2.1 |
| DDR 跑不到高频 | 信号质量/电源/颗粒验证 | §7.5 |
| 白牌颗粒不稳定 | 关 pd_idle/sr_idle, bypass DLL | §8.5 |
| ECC 错误 | 检查 ECC 颗粒焊接、HAL 获取CE/UE | §9 |
| DDR 带宽工具报错 /dev/mem | kernel 开启 CONFIG_DEVMEM | §5.2 |

---

## 参考资料索引

| 文件 | 内容 | 加载时机 |
|------|------|---------|
| `references/ddr_freq_config.md` | DMC 完整 DTS 配置示例 (RK3399/RK3568/RK3588)、场景变频参数详解、Loader 频率匹配规则 | 用户需要配置 DDR 频率或排查变频问题 |
| `references/ddr_debug_verification.md` | DDR 颗粒验证完整流程、stressapptest/memtester 详细参数、定频/变频/Reboot/Sleep 拷机脚本、问题排查扩展案例 | 用户验证 DDR 稳定性或排查 DDR 故障 |

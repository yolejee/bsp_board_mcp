# DDR 调试与验证完整参考

## 1. DDR 颗粒验证完整流程

### 1.1 验证流程总览

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  确认容量    │ → │ 定频拷机    │ → │ 变频拷机    │ → │ Reboot拷机  │ → │ Sleep拷机   │
│  cat meminfo│    │ 最高频 12h+ │    │ 范围全覆盖  │    │ 12h+        │    │ LPDDR4必做  │
└─────────────┘    │stressapptest│    │ memtester后台│    └─────────────┘    └─────────────┘
                   │+ memtester  │    │+ 强制变频   │
                   └─────────────┘    └─────────────┘
```

### 1.2 测试工具详细参数

#### stressapptest

```bash
# 基本语法
/data/stressapptest -s <秒数> -i 4 -C 4 -W --stop_on_errors -M <MB数>

# 参数说明
# -M: 申请测试的内存大小(MB), 一般为总容量的 1/8
#     512MB → 64, 1GB → 128, 2GB → 256, 4GB → 512
# -s: 测试时间(秒), 12h=43200, 24h=86400
# -i: I/O 线程数
# -C: CPU 线程数
# -W: 使用更多写操作
# --stop_on_errors: 遇到错误立即停止

# 结果判断
# PASS: "Status: PASS - please verify no corrected errors"
# FAIL: "Status: FAIL - test discovered HW problems"
# 每 10 秒打印一条 log 显示剩余时间
```

#### memtester

```bash
# 基本语法
/data/memtester <容量>m [循环次数]

# 容量: 总容量的 1/8 (与 stressapptest 相同)
# 测试项: Stuck Address, Random Value, Compare XOR/SUB/MUL/DIV/OR/AND,
#         Sequential Increment, Solid Bits, Block Sequential, Checkerboard,
#         Bit Spread, Bit Flip, Walking Ones, Walking Zeroes

# 正常输出: 每项显示 "ok"
# 异常输出: 打印 "FAILURE: 0x... != 0x... at offset 0x..."
# 资源包中修改版: 出错自动退出 (EXIT_FAIL_OTHERTEST)
# RK3308 版本: 出错不停止,需查看所有打印
```

### 1.3 Linux 4.xx 定频拷机

```bash
# 1. 确认容量
cat /proc/meminfo | grep MemTotal

# 2. 定频到最高频率
su
/data/ddr_freq_scan.sh 800000000   # 根据平台选择: 533000000/800000000/933000000
# 确认输出: "already change to 800000000 done."

# 3. stressapptest (12h+, 1GB 系统)
/data/stressapptest -s 43200 -i 4 -C 4 -W --stop_on_errors -M 128

# 4. memtester (12h+, 1GB 系统)
/data/memtester 128m
```

### 1.4 Linux 4.xx 变频拷机

```bash
# 1. 后台运行 memtester
/data/memtester 128m > /data/memtester_log.txt &

# 2. 执行变频扫描 (全频率范围)
/data/ddr_freq_scan.sh

# 3. 12h 后确认
ps | grep memtester          # 进程存在=正常
cat /data/memtester_log.txt  # 无 FAILURE=正常
# 变频 log 正常打印频率切换信息
```

### 1.5 Linux 3.10 变频拷机

```bash
# Kernel 3.10 使用 proc 接口变频
/data/memtester 128m > /data/memtester_log.txt &
echo 'a:200M-533M-1000000T' > proc/driver/ddr_ts
# 格式: 'a:最低频-最高频-循环次数T'
```

### 1.6 Reboot 拷机

```bash
# Android: 计算器输入 "83991906=" → 点击 "RebootTest"
# 非 Android:
/rockchip_test/rockchip_test.sh
# 选择 auto reboot test
# 关闭: echo off > /data/cfg/rockchip_test/reboot_cnt
```

### 1.7 Sleep 拷机 (RK3399 LPDDR4 必做)

```bash
# Android: 拔掉 USB, 计算器输入 "83991906=" → 点击 "SleepTest"
# 非 Android:
/rockchip_test/rockchip_test.sh
# 选择 suspend_resume test → auto suspend (resume by rtc)
# 手动方式:
while true; do echo mem > /sys/power/state; sleep 5; done
```

### 1.8 RK3308 特殊流程

RK3308 不支持变频, 频率由 loader 设定:
- DDR3: 使用 800MHz loader
- DDR2/LPDDR2: 使用 533MHz loader

```bash
# 内置工具:
memtester 16m > /data/memtester_log.txt &
stressapptest -s 86400 -i 4 -C 4 -W --stop_on_errors -M 32

# 休眠唤醒测试需开启 RKPM_TIMEOUT_WAKEUP_EN:
# rk3308.dtsi 中: rockchip,wakeup-config = <(0 | RKPM_GPIO0_WAKEUP_EN | RKPM_TIMEOUT_WAKEUP_EN)>;
```

## 2. DDR 问题排查详细流程

### 2.1 排查决策树

```
系统异常
├── 看串口 log
│   ├── Loader DDR 初始化阶段报错 → DDR 问题确认
│   │   ├── "rd addr 0x...=0x..." → 焊接问题 → DDR 测试工具
│   │   ├── "16bit error!!!" / "W FF != R" → 焊接问题
│   │   ├── "unknow device" → 焊接/无颗粒
│   │   └── 特殊容量异常 → 更新最新 loader
│   │
│   └── Kernel panic
│       ├── panic 地址每次一致 → 不是 DDR 问题
│       └── panic 地址每次不同 → 可能 DDR 或电源
│
├── 看显示
│   ├── 花屏 → DDR 变频问题 或 电源问题
│   │   └── 定频试试, 排除变频因素
│   ├── 重影 → 参考层不完整 / 信号质量
│   │   └── 提高 VCC_DDR 到 1.6V 或 bypass DRAM DLL
│   └── 正常 → DDR 可能正常,不排除
│
└── 排查实验
    ├── CPU/GPU 降频+抬压 → 改善 → 电源问题
    ├── 关闭 DDR 变频 → 改善 → DDR 变频相关
    └── DDR 降频到 200MHz → 改善 → 信号质量问题
```

### 2.2 电源问题排查

```
检查项:
1. PCB layout 电容: 数量是否足够? 是否靠近芯片? 分布是否合理?
2. 电源 feedback 回路: 是否从末端引回到 PMU/DC-DC?
3. 敷铜: 是否按 RK layout 规则? 电源路径是否太窄?
4. GND: LQFP 封装芯片下方是否堆锡?
5. 纹波测量: 是否存在电源纹波问题?

验证方法:
- 固定 CPU/GPU 到低频, 适当抬高 arm/logic 电压
- 有改善 = 电源问题概率大
```

### 2.3 信号质量问题排查

```
检查项:
1. DDR 走线等长性 (RK 大部分平台不带 eye training)
2. 线间距 (过窄导致串扰)
3. T 型拓扑分支等长性
4. 信号参考层完整性 (过孔隔断参考层)

解决手段:
- 降低 DDR 频率验证
- 调整驱动强度/ODT 强度
- 改变 RZQ 阻值 (个别 220ball LPDDR3 需改小或去掉)
- De-skew 调整 (补偿走线不等长)
```

### 2.4 白牌颗粒问题排查

```
尝试顺序:
1. 关闭 pd_idle, sr_idle → 排除省电模式不兼容
2. Bypass DRAM DLL → 适用于重影现象
3. DDR 测试工具 March 专项 → 存储单元问题检测概率较大

注意: DDR 测试工具仅作辅助, PASS 不代表一定稳定
```

## 3. DDR 带宽工具 (rk_msch_probe) 详细使用

### 3.1 完整使用流程

```bash
# 1. 准备: 切换 governor, DDR 定频
echo userspace > /sys/class/devfreq/dmc/governor
echo 780000000 > /sys/class/devfreq/dmc/userspace/set_freq

# 2. 确认 CONFIG_DEVMEM=y
# 若报错 "open /dev/mem error: No such file or directory"
# → kernel menuconfig: Device Drivers → Character devices → [*] /dev/mem virtual device support

# 3. 运行工具
rk-msch-probe -c rk356x -d 1000     # 一般平台
rk-msch-probe -c rk3588 -d 1000     # RK3588 (4通道输出)

# 参数:
# -c 芯片名: rk312x, rk322x, rk3328, rk3399, rk356x, rk3588 等
# -d 采样间隔 (ms), 默认 1000
# -f DDR频率 (MHz), 工具获取失败时手动传入
# -t 测试轮次, 默认无限
```

### 3.2 输出格式解读

**一般平台** (单通道/双通道):
```
ddr freq: 928Mhz
CH0:
ddr monitor statistics:
ddr load = 3251.23MB/s(43.76%) [RD:1859.93MB/s(25.03%), WR:1391.30MB/s(18.72%),
 ACT(access : active): 3.34, srex:0.54%, pdex:1.27%, clkstp:0.00%, lp:1.81%]
```

**RK3588** (四通道):
```
ddr freq: 2133Mhz
===========ALL=============CH0===============CH1==============CH2===============CH3========
LOAD:  4.51MB/s(0.03%),  1.23MB/s(0.04%),  1.13MB/s(0.03%),  1.16MB/s(0.04%),  1.00MB/s(0.03%)
RD:    2.57MB/s(0.02%),  0.74MB/s(0.02%),  0.65MB/s(0.02%),  0.67MB/s(0.02%),  0.51MB/s(0.02%)
WR:    1.94MB/s(0.01%),  0.49MB/s(0.02%),  0.48MB/s(0.01%),  0.49MB/s(0.02%),  0.48MB/s(0.01%)
```

### 3.3 常见问题

| 问题 | 解决方案 |
|------|---------|
| `/dev/mem` 不存在 | kernel 开启 CONFIG_DEVMEM=y |
| "DDR monitor time gets error" | devfreq governor 不能是 dmc_ondemand, 切换到 userspace |
| 测量结果不准确 | 确保 DDR 已定频, 否则频率变化导致结果偏差 |

## 4. DDR ECC HAL 详细参考

### 4.1 术语

| 缩写 | 含义 |
|------|------|
| SEC ECC | Single Error Correction — 单 bit 可纠正 |
| DED ECC | Double Error Detection — 双 bit 可检测不可纠正 |
| CE | Correctable Error — 单 bit 可纠正错误 |
| UE | Uncorrectable Error — 双 bit 不可纠正错误 |

### 4.2 轮询方式

```c
#include "hal_ddr_ecc.h"

struct DDR_ECC_CNT eccInfo;

void ddr_ecc_poll(void)
{
    HAL_DDR_ECC_Init(&eccInfo);
    while (1) {
        HAL_DDR_ECC_GetInfo(&eccInfo);
        // eccInfo 包含 CE 和 UE 累计数量
        // 以及出错地址: cs, Row, Bank, BankGroup(DDR4), Col, Bit position
        HAL_DelayMs(50);
    }
}
```

### 4.3 中断方式

```c
void HAL_DDR_ECC_IRQHandler(uint32_t irq)
{
    HAL_DDR_ECC_GetInfo(&eccInfo);
    // 处理 ECC 错误信息
}

void ddr_ecc_interrupt_init(void)
{
    HAL_DDR_ECC_Init(&eccInfo);
    HAL_GIC_SetHandler(DDR_ECC_CE_IRQn, HAL_DDR_ECC_IRQHandler);
    HAL_GIC_SetHandler(DDR_ECC_UE_IRQn, HAL_DDR_ECC_IRQHandler);
}
```

### 4.4 DDR ECC 错误注入 (验证用)

```c
// 开启错误注入后, 对特定物理地址的写操作将触发 ECC CE/UE
// API 在 hal_ddr_ecc.c / hal_ddr_ecc.h 中
```

## 5. DDR 厂商 ID 对照表

### 5.1 LPDDR2/LPDDR3

| MR5 | 厂商 |
|-----|------|
| 0x01 | Samsung |
| 0x03 | Elpida |
| 0x05 | Nanya |
| 0x06 | SK hynix |
| 0x08 | Winbond |
| 0x09 | ESMT |
| 0x0e | Intel |
| 0x1a | Xi'an UniIC (紫光展锐) |
| 0x1b | ISSI |
| 0xc2 | Macronix |
| 0xf8 | Fidelix |
| 0xfd | AP Memory |
| 0xff | Micron |

### 5.2 LPDDR4/LPDDR4X

| MR5 | 厂商 |
|-----|------|
| 0x01 | Samsung |
| 0x05 | Nanya |
| 0x06 | SK hynix |
| 0x08 | Winbond |
| 0x09 | ESMT |
| 0x13 | CXMT (长鑫) |
| 0x1a | Xi'an UniIC (紫光展锐) |
| 0x1c | JSC |
| 0xf8 | Fidelix |
| 0xf9 | Ultra Memory |
| 0xfd | AP Memory |
| 0xff | Micron |

### 5.3 LPDDR5/LPDDR5X

| MR5 | 厂商 |
|-----|------|
| 0x01 | Samsung |
| 0x05 | Nanya |
| 0x06 | SK hynix |
| 0x08 | Winbond |
| 0x09 | ESMT |
| 0x13 | CXMT (长鑫) |
| 0xe5 | Dosilicon |
| 0xff | Micron |

### 5.4 读取方式

```bash
# 需开启 dmcdbg 节点
# RK356x: 在 rk3568.dtsi 中添加:
dmcdbg: dmcdbg {
    compatible = "rockchip,rk3568-dmcdbg";
    status = "okay";
};

# 读取:
cat /proc/dmcdbg/dmcinfo
# DramType:       LPDDR4
# Dram ID:        MR5=0x1,MR6=0x0,MR7=0x1
# MR5 = 厂商 ID, MR6/MR7 = 厂商自定义 version ID
```

**注意**: DDR2/DDR3/DDR4 无厂商 ID; LPDDR 的厂商 ID 是晶圆厂商,不一定等于封装品牌。

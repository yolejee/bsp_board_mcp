# Clock / Pinctrl / Regulator / Power Domain / DMA / IOMMU 子系统深度调试

## 目录

1. [Clock 子系统深入](#1-clock-子系统深入)
2. [Pinctrl 子系统深入](#2-pinctrl-子系统深入)
3. [Regulator 子系统深入](#3-regulator-子系统深入)
4. [Power Domain 调试](#4-power-domain-调试)
5. [DMA 子系统调试](#5-dma-子系统调试)
6. [IOMMU 调试](#6-iommu-调试)

---

## 1. Clock 子系统深入

### 1.1 时钟树 debugfs 详解

```bash
cat /sys/kernel/debug/clk/clk_summary

# 输出格式:
#                               enable  prepare  protect               duty
# clock                   count   count    count   rate    accuracy  cycle
# -----------------------------------------------------------------------
#  xin24m                     2       2        0  24000000       0   50000
#    pll_gpll                 6       6        0  1188000000     0   50000
#      clk_uart2              1       1        0  24000000       0   50000
#        sclk_uart2           1       1        0  24000000       0   50000

# 关键列:
# enable count: 硬件使能引用计数
# prepare count: 软件准备引用计数
# rate: 当前频率 (Hz)
```

### 1.2 时钟 API 常见错误

```c
// 常见错误模式:
// 1. clk_enable 没有先 clk_prepare
//    正确: clk_prepare_enable(clk)
//    或: clk_prepare(clk) → clk_enable(clk)

// 2. 引用计数不匹配
//    每次 clk_prepare_enable 必须有对应的 clk_disable_unprepare
//    否则: clock 永远不关 (功耗) 或提前关 (crash)

// 3. 在中断上下文调用 clk_prepare (可能睡眠)
//    clk_prepare = 可能睡眠, 只能在进程上下文
//    clk_enable = 不睡眠, 可在中断上下文
```

### 1.3 DTS 中的时钟配置

```dts
my_device: my_device@ff000000 {
    clocks = <&cru SCLK_UART2>, <&cru PCLK_UART2>;
    clock-names = "baudclk", "apb_pclk";

    // 初始化时设置频率
    assigned-clocks = <&cru SCLK_UART2>;
    assigned-clock-rates = <24000000>;

    // 设置 parent
    assigned-clock-parents = <&cru PLL_GPLL>;
};

// 驱动中获取:
clk = devm_clk_get(dev, "baudclk");    // 按 clock-names 获取
clk = devm_clk_get(dev, NULL);          // 获取第一个 clock
```

### 1.4 时钟问题排查

```bash
# 时钟未使能
cat /sys/kernel/debug/clk/clk_summary | grep <clock_name>
# enable count = 0 → 需要检查驱动是否调用了 clk_prepare_enable

# 频率不对
cat /sys/kernel/debug/clk/<clock_name>/clk_rate
# 检查 assigned-clock-rates 和 parent 时钟

# 时钟树关系
cat /sys/kernel/debug/clk/clk_dump    # JSON 格式的完整时钟树
```

---

## 2. Pinctrl 子系统深入

### 2.1 debugfs 详解

```bash
# 查看所有 pinctrl 控制器
ls /sys/kernel/debug/pinctrl/

# 查看引脚复用状态
cat /sys/kernel/debug/pinctrl/<ctrl>/pinmux-pins
# 格式: pin XX (GPIOXX): <device> <function> <group>
# 例: pin 45 (GPIO1_B5): ffd50000.serial uart2m0-xfer

# 查看所有定义的 function
cat /sys/kernel/debug/pinctrl/<ctrl>/pinmux-functions

# 查看所有 pin group
cat /sys/kernel/debug/pinctrl/<ctrl>/pingroups

# 查看 pin 配置 (drive strength, pull, etc.)
cat /sys/kernel/debug/pinctrl/<ctrl>/pinconf-pins
```

### 2.2 Pinctrl DTS 配置模板

```dts
// 定义 pinctrl group (在 pinctrl 节点下)
&pinctrl {
    my_device {
        my_dev_default: my-dev-default {
            rockchip,pins =
                <4 RK_PA6 1 &pcfg_pull_up>,       // func=1, 上拉
                <4 RK_PA7 1 &pcfg_pull_up>;
        };
        my_dev_sleep: my-dev-sleep {
            rockchip,pins =
                <4 RK_PA6 0 &pcfg_input_high>,    // func=0=GPIO, 高阻
                <4 RK_PA7 0 &pcfg_input_high>;
        };
    };
};

// 引用 pinctrl
&my_device {
    pinctrl-names = "default", "sleep";
    pinctrl-0 = <&my_dev_default>;      // active 状态
    pinctrl-1 = <&my_dev_sleep>;        // sleep 状态
};
```

### 2.3 引脚冲突排查

```bash
# 查看是否有冲突 (同一 pin 被多个设备引用)
cat /sys/kernel/debug/pinctrl/<ctrl>/pinmux-pins | sort -t'(' -k2 -n

# 如果同一 pin 出现多次 → 冲突
# 内核处理: 后 probe 的设备会覆盖先 probe 的配置
# 解决: 确保只有一个设备使用该 pin, 其他设备 status = "disabled"
```

---

## 3. Regulator 子系统深入

### 3.1 debugfs 详解

```bash
cat /sys/kernel/debug/regulator/regulator_summary

# 格式:
# regulator                   use open bypass voltage current   min   max
# -----------------------------------------------------------------------
#  vdd_cpu                      3    4      0  1100000       0  712500 1390000
#    └── fc000000.gpu                                  0                0
#  vcc_3v3                      1    2      0  3300000       0 3300000 3300000

# use: use_count (驱动引用计数)
# open: open_count
# voltage: 当前电压 (uV)
# min/max: 允许电压范围
```

### 3.2 Regulator DTS 配置

```dts
// PMIC 中定义 regulator
regulators {
    vcc_3v3: DCDC_REG4 {
        regulator-name = "vcc_3v3";
        regulator-min-microvolt = <3300000>;
        regulator-max-microvolt = <3300000>;
        regulator-always-on;                     // 始终开启
        regulator-boot-on;                       // 启动时开启
    };
};

// 消费者引用
my_device {
    vdd-supply = <&vcc_3v3>;                    // 引用 regulator
    // 驱动中: devm_regulator_get(dev, "vdd")
};
```

### 3.3 Regulator 问题排查

```bash
# 找到某个设备的 regulator
cat /sys/class/regulator/regulator.*/name       # 找到名称
cat /sys/class/regulator/regulator.*/num_users   # 使用者数量

# 电压设置失败
# → 检查 regulator-min/max-microvolt 范围是否包含目标电压
# → 检查 PMIC 硬件是否支持该电压档位

# regulator_enable 返回错误
# → 检查 PMIC 是否 probe 成功
# → 检查 I2C 通信 (大多数 PMIC 通过 I2C)
# → 检查上级 supply (供电链)
```

---

## 4. Power Domain 调试

### 4.1 概念

```
电源域 (Power Domain) = SoC 内部可独立上下电的区域
  例: GPU PD, VPU PD, RGA PD, etc.
  
当该域内所有设备都不用时, 内核可以关闭整个 PD 以节省功耗
设备使用时, 需要先开启对应 PD
```

### 4.2 debugfs

```bash
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary

# 格式:
# domain                  status  children  performance
#     /device              runtime status
# -------------------------------------------------------
# pd_gpu                  on
#     /devices/.../gpu     active
# pd_vpu                  off
#     /devices/.../vpu     suspended

# status on/off = PD 当前状态
# 设备 runtime 状态与 PD 关联
```

### 4.3 PD 问题排查

```bash
# 设备访问时 bus error / external abort
# → PD 可能关闭了
# → 检查: cat pm_genpd_summary 中对应 PD 是否 on
# → 修复: 确保设备驱动调用了 pm_runtime_get_sync()

# DTS 中关联 PD
my_device {
    power-domains = <&power RK3568_PD_GPU>;
};
```

---

## 5. DMA 子系统调试

### 5.1 DMA 映射类型

```c
// 1. Coherent (一致性) DMA
//    CPU 和设备看到一致的内存, 无需手动 sync
ptr = dma_alloc_coherent(dev, size, &dma_addr, GFP_KERNEL);
dma_free_coherent(dev, size, ptr, dma_addr);

// 2. Streaming DMA
//    需要在 CPU 和设备访问间做 sync
dma_addr = dma_map_single(dev, ptr, size, DMA_TO_DEVICE);
// ... 设备 DMA 操作 ...
dma_unmap_single(dev, dma_addr, size, DMA_TO_DEVICE);

// 方向:
// DMA_TO_DEVICE    → 内存→设备 (TX)
// DMA_FROM_DEVICE  → 设备→内存 (RX)
// DMA_BIDIRECTIONAL → 双向
```

### 5.2 DMA Debug 启用

```bash
# 内核配置
CONFIG_DMA_API_DEBUG=y

# 启动参数
dma_debug=1

# debugfs
cat /sys/kernel/debug/dma-api/num_errors
cat /sys/kernel/debug/dma-api/driver_filter     # 过滤特定驱动
echo <driver_name> > /sys/kernel/debug/dma-api/driver_filter
```

### 5.3 常见 DMA 错误

```bash
# "DMA-API: device driver tries to map memory from stack"
#   → 不能对栈变量做 DMA, 使用 kmalloc 分配

# "DMA-API: device driver frees DMA memory with wrong function"
#   → dma_alloc_coherent 必须用 dma_free_coherent 释放

# "DMA-API: device driver maps memory area partially"
#   → map 的 size 和实际不完全一致

# 数据不对 (cache 一致性)
#   → Streaming DMA 必须在合适时机调用:
#     dma_sync_single_for_cpu()    → 设备DMA写完后, CPU要读
#     dma_sync_single_for_device() → CPU写完后, 设备要DMA读
```

---

## 6. IOMMU 调试

### 6.1 IOMMU 概念

```
没有 IOMMU:
  设备 DMA 地址 = 物理地址 (设备直接访问物理内存)
  
有 IOMMU:
  设备 DMA 地址 = IOVA (虚拟地址)
  IOMMU 做 IOVA → PA 翻译 (类似 CPU 的 MMU)
  好处: 支持分散内存的连续 DMA, 设备隔离, 权限控制
```

### 6.2 IOMMU DTS

```dts
// 设备关联 IOMMU
vop: vop@fe040000 {
    iommus = <&vop_mmu>;
};

// IOMMU 控制器
vop_mmu: iommu@fe043e00 {
    compatible = "rockchip,iommu";
    reg = <0x0 0xfe043e00 0x0 0x100>;
    interrupts = <GIC_SPI 148 IRQ_TYPE_LEVEL_HIGH>;
    #iommu-cells = <0>;
};
```

### 6.3 IOMMU fault 分析

```bash
dmesg | grep -i "iommu\|page fault"

# 典型 fault 日志:
# rk_iommu fe043e00.iommu: Page fault at 0x00000000 of type read
#   → 设备尝试DMA访问地址 0x0 (NULL)
#   → 通常是buffer指针为空

# rk_iommu fe043e00.iommu: Page fault at 0x12345000 of type write
#   → 设备写入一个未映射的 IOVA
#   → 通常是 buffer 已释放但设备还在用 (use-after-unmap)

# 排查:
# 1. 检查 fault 地址是否是有效的 IOVA
# 2. 检查对应的 buffer 是否已正确 map
# 3. 检查处理流程中是否有 unmap 后还在用的情况
```

---
name: linux_driver_debug
description: "通用 Linux 驱动调试技能，不限于任何特定 SoC 平台。用于指导 Linux 设备驱动的开发调试、probe 失败排查、总线驱动调试（I2C/SPI/UART/GPIO）、中断调试、clock/pinctrl/regulator/power domain 子系统调试、DMA/IOMMU 调试、USB/PCIe/GMAC/MMC 外设驱动排查、驱动电源管理（runtime PM/suspend/resume）、设备模型与 deferred probe、sysfs/debugfs 调试接口。触发关键词：驱动调试、driver debug、probe 失败、driver not bound、deferred probe、compatible 匹配、platform driver、i2c_driver、insmod 失败、设备节点不存在、中断不触发、pinctrl 配置、clock enable 失败、regulator enable 失败、IOMMU fault、runtime PM、suspend 失败、devres、devm_、sysfs、debugfs、regmap。当用户描述外设不工作、设备 probe 流程、驱动框架使用等问题时触发。本技能侧重驱动框架和调试方法论，不涉及特定 SoC 的寄存器细节。"
---

# Linux 驱动调试技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| 设备 probe 失败 / 驱动没绑定 | §2 |
| 不知道驱动有没有加载 | §1 设备模型 |
| I2C/SPI/UART/GPIO 外设不工作 | §3 |
| 中断不触发 / 中断风暴 | §4 |
| clock/pinctrl/regulator 配置问题 | §5 |
| DMA / IOMMU 异常 | §6 |
| USB/PCIe/网卡/存储 驱动问题 | §7 |
| 驱动电源管理 (PM) 问题 | §8 |
| devres / sysfs / debugfs 使用 | §9 |
| 驱动开发常用 CONFIG | §10 |

---

## 1. Linux 设备模型基础

### 1.1 设备-驱动匹配流程

```
DTS 节点 (.dts)
  ↓ dtc 编译
FDT (flat device tree, .dtb)
  ↓ 内核解析
platform_device 注册到 bus
  ↓ 与已注册的 driver 匹配
匹配规则 (按优先级):
  1. of_match_table (compatible 字符串)  ← 最常用
  2. acpi_match_table
  3. id_table (name 匹配)
  4. driver.name == device.name         ← 已不推荐
  ↓ 匹配成功
调用 driver.probe()
```

### 1.2 确认设备和驱动状态

```bash
ls /sys/bus/platform/devices/                       # 所有 platform 设备
ls /sys/bus/platform/drivers/<driver_name>/          # 已绑定的设备
ls -l /sys/bus/platform/devices/<dev>/driver         # 有链接=已绑定
cat /sys/bus/platform/devices/<dev>/of_node/compatible  # DTS compatible
ls /sys/bus/{i2c,spi,usb,pci,sdio}/devices/          # 各总线设备
lsmod | grep <driver>                                # 已加载模块
ls /sys/firmware/devicetree/base/                    # 运行时设备树
```

---

## 2. Probe 失败诊断

### 2.1 诊断决策树

```
设备不工作
├── /sys/bus/*/devices/ 中找不到设备
│   ├── DTS 中 status 不是 "okay" → 修改 DTS
│   ├── DTS compatible 拼写错误 → 检查 of_match_table
│   └── DTS 被其他文件 overlay 覆盖 → 梳理 include 链
├── 设备存在但没有 driver 链接
│   ├── 驱动没编译/没加载 → 检查 CONFIG / insmod
│   ├── compatible 不匹配 → 对比 DTS 和驱动 of_match_table
│   └── probe 返回了错误 → 看 dmesg
├── probe 报错
│   ├── -EPROBE_DEFER (-517) → §2.2 Deferred Probe
│   ├── -ENODEV (-19) → 设备不存在或接口错误
│   ├── -ENOMEM (-12) → 内存分配失败
│   ├── -EINVAL (-22) → DTS 属性缺失/格式错误
│   ├── -EIO (-5) → 硬件通信失败 (I2C NAK, SPI 无响应等)
│   ├── -EBUSY (-16) → 资源被占用 (GPIO/IRQ/IO region)
│   └── -ENXIO (-6) → 无此设备或地址
└── probe 成功但功能异常
    ├── clock/pinctrl/regulator 配置不对 → §5
    ├── 中断配置错误 → §4
    └── DMA/IOMMU 映射问题 → §6
```

### 2.2 Deferred Probe (-EPROBE_DEFER)

```bash
# 查看当前挂起等待的设备
cat /sys/kernel/debug/devices_deferred

# 查看 deferred probe 日志
dmesg | grep -i "deferred\|defer"

# 常见原因:
# - regulator 还没 ready (PMIC 驱动未先 probe)
# - clock provider 还没注册
# - GPIO controller 还没 probe
# - reset controller 还没 ready
# - PHY provider 还没 ready

# 排查: 找到依赖链
# 方法1: 启用 initcall_debug 看 probe 顺序
# 在 cmdline 加: initcall_debug

# 方法2: 内核 dynamic debug
echo 'file drivers/base/dd.c +p' > /sys/kernel/debug/dynamic_debug/control
echo 'file drivers/base/core.c +p' > /sys/kernel/debug/dynamic_debug/control
```

### 2.3 手动绑定/解绑

```bash
# 手动解绑设备
echo <device_id> > /sys/bus/platform/drivers/<driver>/unbind

# 手动绑定
echo <device_id> > /sys/bus/platform/drivers/<driver>/bind

# 手动触发所有 deferred probe
echo 1 > /sys/bus/platform/drivers_autoprobe
```

---

## 3. 总线驱动调试

### 3.1 I2C 调试

```bash
# 检查 I2C bus 列表
ls /sys/bus/i2c/devices/       # 格式: <bus>-<addr>
i2cdetect -l                    # 列出所有 I2C adapter

# 扫描总线上的设备 (7-bit 地址)
i2cdetect -y <bus>
# 03 表示设备存在, UU 表示已被驱动占用

# 读写寄存器
i2cget -y <bus> <addr> <reg>
i2cset -y <bus> <addr> <reg> <value>
i2cdump -y <bus> <addr>         # dump 所有寄存器

# I2C trace event
echo 1 > /sys/kernel/debug/tracing/events/i2c/enable
cat /sys/kernel/debug/tracing/trace

# i2ctransfer: 多字节/16位寄存器地址传输
i2ctransfer -y <bus> w2@<addr> <regH> <regL> r4  # 写2字节地址+读4字节

# 注意: i2c-tools 需要 CONFIG_I2C_CHARDEV=y，否则 /dev/i2c-* 不存在

# 常见返回值速查:
# -6  (ENXIO)  → NACK: 地址错/设备未上电/上电时序不对/总线干扰
# -11 (EAGAIN) → 总线忙: 其他设备占用/在中断上下文调用了 i2c_transfer
# -110(ETIMEDOUT) → SCL/SDA 被拉低 (ipd=0x80: slave拉住SCL)
# 隐藏地址冲突: 某些设备响应多个地址 → 逐一拔除外设排查

# I2C 总线恢复:
echo 1 > /sys/bus/i2c/devices/i2c-<bus>/delete_device  # 或重新probe
```

### 3.2 SPI 调试

```bash
# 查看 SPI 设备
ls /sys/bus/spi/devices/

# 用户态 SPI 测试 (需要 spidev)
# 确保 DTS 中有 compatible = "spidev" 或 "rohm,dh2228fv" 等
ls /dev/spidev*

# SPI 内核测试工具
# 内核源码: tools/spi/spidev_test.c
spidev_test -D /dev/spidev0.0 -s 1000000 -p "\\x01\\x02\\x03"

# SPI loopback 测试 (MOSI 接 MISO)
spidev_test -D /dev/spidev0.0 -s 1000000 -l

# SPI trace event
echo 1 > /sys/kernel/debug/tracing/events/spi/enable

# 常见问题:
# 无信号输出 → 检查 pinctrl 复用、clock enable
# CS 不拉低 → 检查 cs-gpios 配置
# 数据错位 → mode (CPOL/CPHA) 不匹配
# 速率不对 → 检查 spi-max-frequency 和实际时钟源
# 高速>20M数据出错 → 调节 rx-sample-delay-ns (tick delay)
# DMA 传输数据异常 → cache 与 memory 不一致:
#   发送前: flush cache→memory; 接收后: invalidate cache 再读
```

### 3.3 UART 调试

```bash
ls /dev/ttyS* /dev/ttyUSB*; dmesg | grep tty       # 查看串口
stty -F /dev/ttyS1 -a                               # 查看参数
microcom -s 115200 /dev/ttyS1                       # 交互测试
echo 1 > /sys/kernel/debug/tracing/events/serial/enable  # trace
# 常见问题: 无输出→pinctrl/clock  乱码→波特率  RX不收→RX脚复用
```

### 3.4 GPIO 调试

```bash
# 查看所有 GPIO 状态
cat /sys/kernel/debug/gpio

# 新 chardev 接口 (推荐)
gpiodetect                      # 列出所有 GPIO chip
gpioinfo <gpiochip>             # 查看所有引脚状态
gpioget <gpiochip> <line>       # 读取
gpioset <gpiochip> <line>=1     # 设置

# GPIO sysfs 接口 (legacy, 仍可用)
echo <N> > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio<N>/direction
echo 1 > /sys/class/gpio/gpio<N>/value
cat /sys/class/gpio/gpio<N>/value

# GPIO 编号换算 (Rockchip):
# GPIO4_C5 = 4*32 + 2*8 + 5 = 149
# 通用公式: bank*32 + group*8 + pin
# group: A=0, B=1, C=2, D=3

# 常见问题:
# gpio_request 失败 → 被其他驱动/pinctrl 占用
# 电平不对 → io-domain 电压配置错误
# 中断不触发 → §4
```

---

## 4. 中断调试

```bash
# 查看中断统计
cat /proc/interrupts

# 查看中断亲和性
cat /proc/irq/<N>/smp_affinity

# IRQ trace event
echo 1 > /sys/kernel/debug/tracing/events/irq/enable

# 常见问题诊断:
# 中断计数始终为 0:
#   1. 检查 DTS interrupts/interrupt-parent 配置
#   2. 确认中断触发类型 (edge vs level, 上升/下降沿)
#   3. 确认硬件是否真正产生了中断信号
#   4. 检查 interrupt-controller 是否 probe 成功

# 中断风暴 (计数疯涨):
#   1. 共享中断未正确处理 → handler 返回 IRQ_NONE
#   2. 电平中断未清除源 → 中断处理中必须清 pending
#   3. GPIO 中断 bounce → 加去抖 (debounce)

# 查看共享中断
cat /proc/interrupts | awk '$2+0 > 0'

# 中断线程化检查
ps aux | grep irq/   # threaded IRQ 会有 [irq/<N>-<name>] 进程
```

---

## 5. 子系统框架调试

### 5.1 Clock 调试

```bash
# 查看时钟树
cat /sys/kernel/debug/clk/clk_summary

# 关键列说明:
# enable_cnt: 引用计数 (0=关闭)
# prepare_cnt: prepare 引用计数
# rate: 当前频率 (Hz)

# 查看单个时钟
cat /sys/kernel/debug/clk/<clk_name>/clk_rate
cat /sys/kernel/debug/clk/<clk_name>/clk_enable_count

# clock trace event
echo 1 > /sys/kernel/debug/tracing/events/clk/enable

# 常见问题:
# clk_enable 返回错误 → parent clock 没有 prepare/enable
# 频率不对 → 检查 assigned-clock-rates (DTS)
# enable_cnt=0 但设备在用 → clock 被其他驱动意外关闭
```

### 5.2 Pinctrl 调试

```bash
# 查看 pinctrl 状态
cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins

# 查看所有 pin group
cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pingroups

# 查看设备的 pinctrl 状态
cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-functions

# 常见问题:
# 引脚复用冲突 → 两个设备配了同一个 pin → 检查 pinctrl-0
# pinctrl 不生效 → status = "disabled" 或 probe 失败
# 驱动强度/上下拉不对 → 检查 DTS drive-strength / bias-pull-up
```

### 5.3 Regulator 调试

```bash
cat /sys/kernel/debug/regulator/regulator_summary   # 全部 regulator 状态
# 关键列: state(enabled/disabled), voltage(uV), use_count(引用)
cat /sys/class/regulator/regulator.*/name            # 单个详情
echo 1 > /sys/kernel/debug/tracing/events/regulator/enable
# 常见: enable失败→PMIC I2C断  电压超范围→min/max限制  use_count=0→always-on
```

### 5.4 Power Domain 调试

```bash
# 查看 power domain 状态
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary

# 状态: on / off / suspended
# 如果 device 的 power domain off 了, 设备不可访问

# 常见问题:
# 访问设备寄存器时 bus error → PD 处于 off
# 需要 runtime PM enable 才能自动管理 PD
```

---

## 6. DMA / IOMMU 调试

### 6.1 DMA 调试

```bash
# 启用 DMA Debug
CONFIG_DMA_API_DEBUG=y

# 启动参数
dma_debug=1

# 查看 DMA 映射统计
cat /sys/kernel/debug/dma-api/dump
cat /sys/kernel/debug/dma-api/num_errors

# 常见错误:
# DMA-API: device driver frees DMA memory with wrong function
#   → dma_alloc_coherent 对应 dma_free_coherent
# DMA-API: device driver maps memory from stack
#   → 不能对栈内存做 DMA 映射
# DMA 地址超范围
#   → 检查 dma-ranges (DTS), 设置 dma_set_mask_and_coherent()
```

### 6.2 IOMMU 调试

```bash
# 查看 IOMMU group
ls /sys/kernel/iommu_groups/*/

# 查看 IOMMU 域信息
cat /sys/kernel/debug/iommu/*/

# IOMMU fault 日志
dmesg | grep -i iommu

# 常见 IOMMU fault 原因:
# 1. 设备 DMA 地址未在 IOMMU 中映射
# 2. 映射的 size 不够, 设备越界访问
# 3. IOMMU 权限不匹配 (read-only 但设备要写)
# 4. DTS 中 iommus 属性缺失或配错
```

---

## 7. 外设驱动调试速查

### 7.1 USB

```bash
# 查看 USB 设备树
lsusb -t
lsusb -v

# 查看 USB 控制器
cat /sys/kernel/debug/usb/devices

# USB 枚举过程
dmesg | grep -i "usb\|ehci\|xhci\|dwc"

# 常见问题:
# 枚举失败 → VBUS 供电 / USB PHY 时钟/复位 / 信号质量
# OTG 不切换 → id-gpio / dr_mode 配置
# Gadget 不工作 → UDC driver / configfs 配置
```

### 7.2 PCIe

```bash
# 查看 PCIe 设备
lspci -vvv
lspci -t    # 树形

# 查看链路状态
lspci -vvv | grep -i "lnksta\|lnkcap\|speed\|width"

# 常见问题:
# Link 不起 → 复位时序 / PERST# GPIO / refclk / PHY 配置
# 链路降速 → 信号完整性 / ASPM 配置
# BAR 分配失败 → 地址空间不够 / DTS ranges 配置
```

### 7.3 GMAC / 网卡

```bash
# 查看网口状态
ip link show
ethtool <eth>
ethtool -S <eth>       # 统计计数

# PHY 状态
cat /sys/class/net/<eth>/carrier
ethtool <eth> | grep "Link detected"

# MDIO/PHY 寄存器
# 部分平台:
cat /sys/bus/mdio_bus/devices/*/phy_id

# 常见问题:
# Link 不起 → RGMII delayline / PHY 供电/复位 / MDIO 通信
# 有 Link 无数据 → MAC/PHY 接口模式不匹配 / delayline
# 丢包严重 → 中断合并配置 / ring buffer 大小 / 网络拥塞
```

### 7.4 MMC / eMMC / SD

```bash
# 查看 MMC 设备
ls /sys/bus/mmc/devices/
cat /sys/class/mmc_host/mmc*/ios   # 当前 IO 设置

# 查看识别信息
cat /sys/block/mmcblk*/device/{type,name,cid,csd}

# 常见问题:
# 识别不到 → 供电/时钟/CMD线/数据线 检查
# 速度慢 → tuning 失败, 降速到低速模式
# IO 错误 → 信号完整性, 检查 dmesg 中的 error code
```

---

## 8. 驱动电源管理

### 8.1 Runtime PM

```bash
# 查看 runtime PM 状态
cat /sys/devices/.../power/runtime_status    # active/suspended/...
cat /sys/devices/.../power/runtime_usage     # 引用计数
cat /sys/devices/.../power/control           # auto/on

# 禁用某设备的 runtime PM (调试用)
echo on > /sys/devices/.../power/control

# Runtime PM trace
echo 1 > /sys/kernel/debug/tracing/events/rpm/enable

# 常见问题:
# 设备访问时 bus error → runtime PM 把设备 suspend 了
# 修复: pm_runtime_get_sync() 后再访问, 访问完 pm_runtime_put()
```

### 8.2 System Suspend/Resume

```bash
cat /sys/power/state                           # 支持的睡眠状态
echo mem > /sys/power/state                    # 测试 suspend
echo 1 > /sys/power/pm_debug_messages          # 启用 PM debug
echo 1 > /sys/power/pm_print_times             # 显示每设备耗时
dmesg | grep -i "suspend\|resume\|PM:"         # 定位失败设备
# 查找: "dpm_run_callback(): xxx returns error"

# 中断唤醒系统:
# DTS: 设备节点加 wakeup-source (旧写法: gpio-key,wakeup)
# 驱动 suspend() 中调用 enable_irq_wake(irq) → 使中断在休眠时有效
# 驱动 resume() 中调用 disable_irq_wake(irq) → 成对使用
# 唤醒后保持一段时间不再睡: __pm_stay_awake() / pm_wakeup_event()
# 查看唤醒源: cat /sys/kernel/debug/wakeup_sources
```

---

## 9. 调试接口与工具

### 9.1 devres / regmap / 运行时设备树

```bash
# devres: 查看设备分配了哪些资源 (devm_* 自动管理)
cat /sys/devices/.../devres

# regmap: 读写硬件寄存器
ls /sys/kernel/debug/regmap/                         # 已注册设备
cat /sys/kernel/debug/regmap/<dev>/registers          # 读寄存器
echo 1 > /sys/kernel/debug/tracing/events/regmap/enable  # trace

# 运行时设备树验证
dtc -I fs -O dts /sys/firmware/devicetree/base/ 2>/dev/null  # 完整 DTS
cat /sys/firmware/devicetree/base/<node>/<property>   # 读属性
```

---

## 10. 驱动调试常用 CONFIG

| CONFIG | 作用 | 性能影响 |
|--------|------|---------|
| `CONFIG_DYNAMIC_DEBUG` | 运行时 dev_dbg 开关 | 极小 |
| `CONFIG_DEBUG_DRIVER` | 驱动核心调试信息 | 小 |
| `CONFIG_DEBUG_DEVRES` | devres 分配/释放追踪 | 小 |
| `CONFIG_PM_DEBUG` | 电源管理调试 | 小 |
| `CONFIG_PM_TRACE` | suspend/resume 追踪 | 小 |
| `CONFIG_GPIO_SYSFS` | GPIO sysfs 接口 | 无 |
| `CONFIG_I2C_CHARDEV` | I2C 用户态接口 (/dev/i2c-*) | 无 |
| `CONFIG_SPI_SPIDEV` | SPI 用户态接口 (/dev/spidev*) | 无 |
| `CONFIG_DMA_API_DEBUG` | DMA API 使用检查 | 中 |
| `CONFIG_IOMMU_DEBUGFS` | IOMMU 调试文件系统 | 小 |
| `CONFIG_USB_MON` | USB 数据包监控 | 小 |
| `CONFIG_REGMAP_DEBUGFS` | regmap 寄存器读写 | 小 |
| `CONFIG_DEBUG_PINCTRL` | pinctrl 调试打印 | 小 |

### 推荐组合

```bash
# 基础调试 (开发阶段常开)
CONFIG_DYNAMIC_DEBUG=y
CONFIG_DEBUG_DRIVER=y
CONFIG_DEBUG_DEVRES=y
CONFIG_I2C_CHARDEV=y
CONFIG_SPI_SPIDEV=y
CONFIG_GPIO_SYSFS=y
CONFIG_REGMAP_DEBUGFS=y

# 电源管理调试
CONFIG_PM_DEBUG=y
CONFIG_PM_TRACE=y

# DMA/IOMMU 调试 (遇到问题时开)
CONFIG_DMA_API_DEBUG=y
CONFIG_IOMMU_DEBUGFS=y
```

---

## 11. 通用排查流程

```
外设不工作
  1. dmesg | grep -i <driver_name>   → 有无 probe 日志?
  2. ls /sys/bus/*/devices/           → 设备存在?
  3. ls /sys/bus/*/drivers/<drv>/     → 驱动绑定了?
  4. 用户态工具测试:
     I2C: i2cdetect/i2cget
     SPI: spidev_test
     UART: microcom
     GPIO: gpioget/gpioset
  5. 子系统状态:
     clk_summary / regulator_summary / gpio / pinmux-pins
  6. trace event 追踪:
     echo 1 > events/<subsys>/enable → cat trace
  7. 看原理图:
     供电/复位/时钟/信号 是否正确连接
```

---

## References

> 以下参考文件在需要深入信息时由 AI 自动加载：

| 文件 | 内容 |
|------|------|
| `references/probe_failure_debug.md` | probe 失败全流程深入分析、deferred probe 机制、设备匹配机制详解、initcall 顺序、模块加载调试 |
| `references/bus_driver_debug.md` | I2C/SPI/UART/GPIO 深入调试：协议分析、波形诊断、错误码速查、驱动框架 API、用户态工具高级用法 |
| `references/subsystem_framework_debug.md` | clock/pinctrl/regulator/power domain/DMA/IOMMU 框架深度调试：API 调用链、debugfs 详解、常见错误模式 |
| `references/peripheral_driver_debug.md` | USB/PCIe/GMAC/MMC 驱动调试：枚举流程、链路训练、PHY 调试、信号完整性、错误码分析 |

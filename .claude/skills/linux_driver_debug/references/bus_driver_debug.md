# I2C / SPI / UART / GPIO 总线驱动深入调试

## 目录

1. [I2C 深入调试](#1-i2c-深入调试)
2. [SPI 深入调试](#2-spi-深入调试)
3. [UART 深入调试](#3-uart-深入调试)
4. [GPIO 深入调试](#4-gpio-深入调试)
5. [中断子系统调试](#5-中断子系统调试)

---

## 1. I2C 深入调试

### 1.1 I2C 协议基础回顾

```
START → Address(7bit) + R/W → ACK → Data → ACK → ... → STOP
  ↓                           ↓
SDA从高到低(SCL高)     从设备拉低SDA
```

**7-bit vs 10-bit 地址：**
- 绝大多数设备使用 7-bit 地址 (0x03~0x77 有效)
- i2cdetect 扫描显示的是 7-bit 地址
- DTS `reg` 属性填 7-bit 地址

### 1.2 i2c-tools 高级用法

```bash
# 列出所有 I2C adapter
i2cdetect -l

# 扫描特定功能
i2cdetect -y -r <bus>          # SMBus 快速读方式
i2cdetect -y -q <bus>          # Quick Command 方式

# 读特定寄存器
i2cget -y <bus> <addr> <reg> b            # byte 读
i2cget -y <bus> <addr> <reg> w            # word 读 (16-bit)
i2cget -y <bus> <addr> <reg>0x<reg2> i 2  # I2C block read

# 批量写
i2cset -y <bus> <addr> <reg> <val1> <val2> ... i  # I2C block write

# 转储所有寄存器
i2cdump -y <bus> <addr>
i2cdump -y -r 0x00-0x1f <bus> <addr>   # 范围转储

# 传输原始数据 (i2ctransfer, 4.10+)
i2ctransfer -y <bus> w2@<addr> 0x00 0x10 r2  # 写2字节后读2字节
```

### 1.3 I2C 常见错误分析

| 错误日志 | 含义 | 排查方向 |
|---------|------|---------|
| `i2c_write: NAK on address` | 地址 NAK | 地址错误 / 设备未上电 / SDA 线断 |
| `i2c_read: NAK on data` | 数据 NAK | 寄存器不存在 / 设备忙 |
| `timeout, ipd: 0x00` | 超时无中断 | SCL 被拉低(总线死锁) / clock 未使能 |
| `timeout, ipd: 0x10` | 超时有 START | SDA 被拉低 / 设备卡死 |
| `the I2C SCL is low` | SCL 被拉低 | 从设备异常 / 需总线恢复 |

### 1.4 I2C 总线恢复

```bash
# 内核 4.19+ 支持总线恢复 (发9个clock脉冲)
# DTS 中需要配置:
# &i2c1 {
#     pinctrl-1 = <&i2c1_gpio>;      // GPIO 恢复模式 pinctrl
#     scl-gpios = <&gpio0 RK_PB5 GPIO_ACTIVE_HIGH>;
#     sda-gpios = <&gpio0 RK_PB6 GPIO_ACTIVE_HIGH>;
# };

# 手动 GPIO 恢复 (需要具体 GPIO 号):
# 将 SCL 配置为 GPIO 输出, 手动翻转 9 次
# 每次翻转后检查 SDA 是否释放
```

### 1.5 I2C trace event 详解

```bash
echo 1 > /sys/kernel/debug/tracing/events/i2c/enable
cat /sys/kernel/debug/tracing/trace

# 输出格式:
# i2c_write: i2c-1 #0 a=050 f=0000 l=2 [00 10]
# i2c_read:  i2c-1 #1 a=050 f=0001 l=4 [xx xx xx xx]
# i2c_result: i2c-1 n=2 ret=0
#  a=050 → 7-bit 地址 0x50
#  f=0001 → flags (0x0001=I2C_M_RD)
#  l=2 → 数据长度
#  ret=0 → 成功
```

---

## 2. SPI 深入调试

### 2.1 SPI 模式

| Mode | CPOL | CPHA | 说明 |
|------|------|------|------|
| 0 | 0 | 0 | 空闲低, 上升沿采样 (最常用) |
| 1 | 0 | 1 | 空闲低, 下降沿采样 |
| 2 | 1 | 0 | 空闲高, 下降沿采样 |
| 3 | 1 | 1 | 空闲高, 上升沿采样 |

### 2.2 SPI DTS 配置详解

```dts
&spi0 {
    status = "okay";
    max-freq = <50000000>;                  // SPI 控制器最大频率
    // assigned-clocks / assigned-clock-rates 设置源时钟

    my_device@0 {
        compatible = "vendor,model";
        reg = <0>;                          // chip select 编号
        spi-max-frequency = <10000000>;     // 设备最大频率
        spi-cpha;                           // CPHA=1 (省略=0)
        spi-cpol;                           // CPOL=1 (省略=0)
        // spi-cs-high;                     // CS 高有效
        // spi-3wire;                       // 3线模式
        // spi-lsb-first;                   // LSB 优先
    };
};
```

### 2.3 spidev_test 工具详解

```bash
# 编译 (内核源码 tools/spi/)
make -C tools/spi/

# 基本读写
spidev_test -D /dev/spidev0.0 -s 1000000 -p "\x01\x02\x03"

# 参数:
# -D  设备节点
# -s  速率 (Hz)
# -p  发送数据 (hex)
# -l  回环模式 (loopback, MOSI接MISO)
# -b  每字位数 (默认8)
# -H/O  CPHA/CPOL 设置
# -v  verbose, 显示收发数据

# 回环测试: 物理短接 MOSI-MISO
spidev_test -D /dev/spidev0.0 -s 1000000 -l -v
# TX: FF FF FF FF FF FF → RX 应该一致
```

### 2.4 SPI 常见问题

```bash
# 1. /dev/spidev* 不存在
# → DTS 中添加 compatible = "rohm,dh2228fv" (通用 spidev)
# → 确认 CONFIG_SPI_SPIDEV=y

# 2. 数据全 0 或全 FF
# → MISO 悬空 (未接设备) / 设备未上电

# 3. 数据错位
# → SPI mode 不匹配 (CPOL/CPHA)
# → 检查示波器: 采样沿是否对齐数据有效期

# 4. CS 不拉低
# → 检查 cs-gpios 配置 (DTS)
# → 对于非 cs-gpios, 检查原生 CS 引脚 pinctrl
```

---

## 3. UART 深入调试

### 3.1 UART 参数

```bash
# 完整参数设置
stty -F /dev/ttyS1 115200   # 波特率
stty -F /dev/ttyS1 cs8      # 8 数据位 (cs5/cs6/cs7/cs8)
stty -F /dev/ttyS1 -parenb  # 无校验 (parenb=有, parodd=奇)
stty -F /dev/ttyS1 -cstopb  # 1 停止位 (cstopb=2)
stty -F /dev/ttyS1 raw      # 原始模式
stty -F /dev/ttyS1 -echo    # 关闭回显
stty -F /dev/ttyS1 crtscts  # 开启硬件流控 (-crtscts 关闭)
```

### 3.2 UART DTS 配置

```dts
&uart1 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&uart1m0_xfer>;           // TX/RX 引脚
    // pinctrl-0 = <&uart1m0_xfer &uart1m0_ctsn &uart1m0_rtsn>;  // 含流控
};

// 作为控制台:
chosen {
    stdout-path = "serial2:1500000n8";      // 串口号:波特率+格式
};
```

### 3.3 UART trace event

```bash
echo 1 > /sys/kernel/debug/tracing/events/serial/enable
# 可追踪: serial_8250_interrupt, serial_8250_tx, serial_8250_rx
```

### 3.4 波特率异常调试

```bash
# 查看实际波特率 (部分平台)
cat /sys/kernel/debug/clk/clk_summary | grep uart

# 计算: 实际波特率 = UART 源时钟 / (16 * divisor)
# 如果源时钟不能精确分频, 会有误差
# 误差 > 2% 可能导致乱码

# 特殊波特率: 1500000 (Rockchip 控制台常用)
# 需要 24MHz 时钟源, 才能精确分频
```

---

## 4. GPIO 深入调试

### 4.1 GPIO 新接口 (libgpiod)

```bash
# 安装
apt install gpiod    # 或 opkg install libgpiod-utils

# 命令:
gpiodetect           # 列出所有 GPIO chip
gpioinfo gpiochip0   # 查看所有引脚 (line) 状态
gpioget gpiochip0 5  # 读取值
gpioset gpiochip0 5=1 # 设置值

# 事件监控 (中断/边沿)
gpiomon gpiochip0 5  # 监控某引脚的边沿事件
gpiomon --rising gpiochip0 5    # 只监控上升沿
gpiomon --format='%e %o %s.%n' gpiochip0 5  # 自定义格式
```

### 4.2 GPIO 编号体系

```bash
# 通用方法: 查看 gpiochip 的 base 号
cat /sys/class/gpio/gpiochip*/base
cat /sys/class/gpio/gpiochip*/label
cat /sys/class/gpio/gpiochip*/ngpio

# Rockchip 换算:
# GPIO<bank>_<group><pin>
# 编号 = bank*32 + group_offset + pin
# group: A=0, B=8, C=16, D=24
# 例: GPIO4_C5 = 4*32 + 16 + 5 = 149

# 全志 Allwinner 换算:
# P<port><pin>
# 编号 = (port - 'A') * 32 + pin
# 例: PH5 = 7*32 + 5 = 229

# 已占用的 GPIO 查看
cat /sys/kernel/debug/gpio
# 会显示每个 GPIO 的使用者和方向/电平
```

### 4.3 GPIO 常见问题

```bash
# "gpio_request failed" → 资源冲突
cat /sys/kernel/debug/gpio | grep <gpio_num>
# 查看谁已经占用了该 GPIO

# GPIO 电平不对
# 1. 检查 io-domain 电压 (1.8V vs 3.3V)
# 2. 检查 pull-up/pull-down 配置
# 3. 检查输出是否被外部电路拉住

# GPIO 在 suspend 后状态变化
# 需要在 DTS 中配置 pinctrl-1 = <&sleep_state>;
# pinctrl-names = "default", "sleep";
```

---

## 5. 中断子系统调试

### 5.1 中断 DTS 配置

```dts
// GPIO 中断
my_device {
    interrupt-parent = <&gpio0>;
    interrupts = <RK_PB5 IRQ_TYPE_EDGE_FALLING>;
    // 或:
    // interrupts = <RK_PB5 IRQ_TYPE_LEVEL_LOW>;
};

// GIC 中断 (SoC 内部外设)
my_periph {
    interrupt-parent = <&gic>;
    interrupts = <GIC_SPI 123 IRQ_TYPE_LEVEL_HIGH>;
    // GIC_SPI = 共享外设中断
    // GIC_PPI = 私有外设中断
};
```

### 5.2 中断触发类型

| 类型 | 值 | 说明 |
|------|---|------|
| `IRQ_TYPE_EDGE_RISING` | 1 | 上升沿 |
| `IRQ_TYPE_EDGE_FALLING` | 2 | 下降沿 |
| `IRQ_TYPE_EDGE_BOTH` | 3 | 双沿 |
| `IRQ_TYPE_LEVEL_HIGH` | 4 | 高电平 |
| `IRQ_TYPE_LEVEL_LOW` | 8 | 低电平 |

### 5.3 中断调试命令

```bash
# 查看中断计数和分布
cat /proc/interrupts

# 软中断统计
cat /proc/softirqs

# 查看某个 IRQ 的注册信息
cat /proc/irq/<N>/spurious       # 虚假中断
cat /proc/irq/<N>/actions        # handler 名称

# 设置中断亲和性 (测试用)
echo <cpu_mask> > /proc/irq/<N>/smp_affinity

# IRQ trace event 详解
echo 1 > /sys/kernel/debug/tracing/events/irq/irq_handler_entry/enable
echo 1 > /sys/kernel/debug/tracing/events/irq/irq_handler_exit/enable
# irq_handler_exit 中 ret=handled → 处理成功
# irq_handler_exit 中 ret=unhandled → 共享中断, 不是本设备的

# 中断延迟测量
echo 1 > /sys/kernel/debug/tracing/events/irq/enable
# 分析 irq_handler_entry 和 irq_handler_exit 的时间差
```

### 5.4 中断风暴诊断

```bash
# 快速确认: 短时间内中断计数暴涨
watch -n 1 "cat /proc/interrupts | grep <keyword>"

# 原因分析:
# 1. 电平中断: handler 没清中断源 → 退出后立即又触发
#    修复: 在 handler 中写清 pending 寄存器
# 2. 共享中断: handler 返回 IRQ_NONE → 导致反复触发
#    修复: 正确检查中断原因寄存器
# 3. GPIO 抖动: 按键等机械开关产生多次边沿
#    修复: DTS 加 debounce-interval 或软件去抖

# 内核自动禁用:
# "irq NN: nobody cared" → 某中断连续多次返回 IRQ_NONE
# 内核会自动禁用该中断, dmesg 中有日志
```

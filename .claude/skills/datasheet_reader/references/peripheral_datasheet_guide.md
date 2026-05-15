# 外设数据手册 (Peripheral Datasheet) 深入分析指南

> 本文件是 `datasheet_reader` 技能的参考资料，按外设类型给出详细的 Datasheet 分析方法。

## 目录

1. [传感器类 (Sensor)](#1-传感器类)
2. [电源管理类 (Power Management)](#2-电源管理类)
3. [通信接口类 (Communication Interface)](#3-通信接口类)
4. [存储器类 (Memory)](#4-存储器类)
5. [音频编解码器 (Audio Codec)](#5-音频编解码器)
6. [显示驱动类 (Display Driver)](#6-显示驱动类)
7. [时钟与定时器 (Clock & Timer)](#7-时钟与定时器)
8. [通用分析检查清单](#8-通用分析检查清单)

---

## 1. 传感器类

适用：加速度计、陀螺仪、温度传感器、压力传感器、光传感器、磁力计、IMU 等

### 1.1 关键参数提取清单

| 参数 | 为什么重要 | 在 Datasheet 哪里找 |
|------|-----------|-------------------|
| 量程 (Range/Full Scale) | 决定能测量的范围 | Features / Electrical Characteristics |
| 灵敏度 (Sensitivity) | 分辨率=量程/灵敏度 | Electrical Characteristics |
| 分辨率 (Resolution) | 最小可分辨的变化量 | Features 或计算得出 |
| 精度 (Accuracy) | 与真实值的偏差 | Electrical Characteristics 脚注 |
| 零偏 (Zero Offset / Bias) | 零位输出误差 | Electrical Characteristics |
| 噪声密度 (Noise Density) | 影响低信号测量 | Electrical Characteristics (μg/√Hz, °/s/√Hz) |
| 输出数据率 (ODR) | 数据更新频率 | Features / Register 配置 |
| 带宽 (Bandwidth / -3dB) | 信号频率响应范围 | Electrical Characteristics |
| 温漂 (Temperature Drift) | 温度变化引起的误差 | Electrical Characteristics / Graphs |
| 启动时间 (Power-Up Time) | 从上电到数据可用 | Timing / Electrical Characteristics |
| 自检功能 (Self-Test) | 是否支持内建自测 | Features / Register |

### 1.2 传感器 I2C/SPI 配置速查

**I2C 型传感器必查项：**
```
- 设备地址 (Slave Address): 查 Pin Description 中 SDO/SA0 引脚
  · SDO=GND → 地址 = 0x{A}  (7-bit)
  · SDO=VDD → 地址 = 0x{B}  (7-bit)
- 时钟速率: Standard (100kHz) / Fast (400kHz) / Fast Plus (1MHz)
- WHO_AM_I 寄存器: 地址 0x{XX}, 预期值 0x{YY} → 首先读此寄存器验证通信
```

**SPI 型传感器必查项：**
```
- SPI 模式: CPOL=? CPHA=? (通常 Mode 0 或 Mode 3)
- 最大 SPI 时钟: {X} MHz
- 读/写位: 通常 bit7: 0=Write, 1=Read
- 多字节传输: 地址是否自增? 查 IF_INC 或 AUTO_INCREMENT 位
```

### 1.3 典型初始化流程

```c
/* 通用传感器初始化模板 */
// 1. 读 WHO_AM_I → 验证芯片通信和 ID
id = read_reg(WHO_AM_I);
if (id != EXPECTED_ID) return ERROR;

// 2. 软复位 (如果支持)
write_reg(CTRL_RESET, RESET_BIT);
mdelay(BOOT_TIME); // 查 Datasheet Power-Up Time

// 3. 配置量程
write_reg(CTRL_FS, FULL_SCALE_SETTING);

// 4. 配置输出数据率
write_reg(CTRL_ODR, ODR_SETTING);

// 5. 配置滤波器 (如支持)
write_reg(CTRL_FILTER, FILTER_SETTING);

// 6. 使能传感器
write_reg(CTRL_POWER, NORMAL_MODE);
mdelay(STARTUP_TIME);
```

---

## 2. 电源管理类

适用：LDO、DC-DC、PMIC、电池充电器、电源开关、电压基准

### 2.1 LDO/DC-DC 关键参数

| 参数 | 含义 | 注意事项 |
|------|------|---------|
| Input Voltage Range (VIN) | 输入电压范围 | 注意最小压差 (Dropout) |
| Output Voltage (VOUT) | 输出电压 | 固定/可调？精度多少？ |
| Output Current (IOUT) | 最大输出电流 | 注意降额条件（温度、VIN） |
| Dropout Voltage (VDO) | 最小输入输出压差 | LDO 的核心指标，低压差=好 |
| Quiescent Current (IQ) | 静态功耗 | 电池供电应用的关键 |
| PSRR | 电源抑制比 | 抑制输入纹波的能力 (dB@freq) |
| Load Regulation | 负载调整率 | 负载变化时输出电压的稳定性 |
| Line Regulation | 电源调整率 | 输入变化时输出电压的稳定性 |
| Output Capacitor | 输出电容要求 | ESR 范围！选错会振荡 |
| Thermal Shutdown (TSD) | 过温保护温度 | 自保护阈值 |
| Enable (EN) | 使能脚逻辑电平 | 是否有内部上/下拉 |
| Soft Start | 软启动时间 | 避免浪涌电流 |

### 2.2 PMIC 特有关注点

```
PMIC 分析要点：
1. 电源拓扑图 (Power Tree)
   - 哪些 BUCK/LDO 供电给哪些域
   - 上电顺序 (Power Sequence)
   - 关机顺序

2. I2C 寄存器组
   - 电压配置寄存器 (voltage selector)
   - 使能控制寄存器
   - 中断状态/控制寄存器
   - GPIO 复用配置

3. 特殊功能
   - DVFS (动态电压频率调节) 支持
   - 休眠模式电压配置
   - Power Key 检测
   - RTC 功能
```

### 2.3 电源设计检查清单

- [ ] 输入电压在 VIN 范围内（考虑瞬态）
- [ ] 输出电流留有 20%+ 余量
- [ ] 散热满足最大功耗要求（计算 θJA）
- [ ] 输出电容类型和 ESR 在要求范围内
- [ ] 反馈电阻精度满足要求（可调型）
- [ ] 使能引脚电平与主控兼容
- [ ] 上电顺序符合系统要求
- [ ] PCB 布局满足推荐

---

## 3. 通信接口类

适用：CAN 收发器、RS485/RS232 收发器、以太网 PHY、USB PHY、电平转换器

### 3.1 收发器关键参数

| 参数 | 含义 | 关键考量 |
|------|------|---------|
| Data Rate | 最大通信速率 | 需留余量 (实际 < 标称) |
| Propagation Delay | 传输延迟 | 影响总线时序 |
| Common Mode Range | 共模电压范围 | 长线传输抗干扰 |
| ESD Protection | 静电防护等级 | 接外部接口需关注 |
| Fail-Safe | 总线断开时的输出 | 已知/确定状态？ |
| Number of Nodes | 最大节点数 | 总线负载能力 |
| Supply Current | 工作电流 | 含发送/接收/待机模式 |
| Isolation Voltage | 隔离耐压 | 隔离型收发器的核心 |

### 3.2 以太网 PHY 关键参数

```
必查项：
- 支持速率: 10/100/1000 Mbps
- 接口类型: MII / RMII / RGMII / SGMII
- MDIO 地址配置: 查地址引脚 (PHYAD[0:4])
- LED 指示配置: LED0/LED1 功能
- 时钟输入/输出: REF_CLK 方向和频率
  · RMII: 50MHz (谁提供?)
  · RGMII: 125MHz (TX_CLK/RX_CLK)
- 自协商 (Auto-Negotiation): 默认通告的能力
- 中断输出: Link Status Change
- 内置终端电阻: 是否需要外部 49.9Ω
- 电源域: Analog VDD / Digital VDD / I/O VDD
```

---

## 4. 存储器类

适用：DRAM (DDR3/DDR4/LPDDR4)、NAND Flash、NOR Flash、eMMC、EEPROM

### 4.1 DRAM 关键参数

| 参数 | 含义 | 注意 |
|------|------|------|
| Density | 容量 (Gb/Gbit) | 注意 bit vs Byte |
| Organization | 位宽×深度 | 如 x16, x32 |
| Speed Grade | 速度等级 | 如 DDR4-2400, DDR4-3200 |
| CAS Latency (CL) | 列地址选通延迟 | 影响随机读取性能 |
| tRCD | 行地址到列地址延迟 | |
| tRP | 行预充电时间 | |
| tRAS | 行有效时间 | |
| VDDQ | I/O 电源电压 | DDR4=1.2V, LPDDR4=1.1V |
| ODT | 片上终端电阻 | 阻抗匹配 |
| Operating Temperature | 工作温度范围 | 工业级 vs 商业级 |

### 4.2 eMMC/Flash 关键参数

```
必查项：
- 容量: 如 8/16/32/64 GB
- 接口版本: eMMC 5.0 / 5.1
- 总线宽度: x1 / x4 / x8
- 速率模式: HS200 / HS400
- 读写速度: Sequential / Random
- Boot 支持: Boot Partition 大小
- 寿命: P/E Cycles, TBW
- 可靠性: pSLC / Enhanced Area
- 电源: VCC (3.3V) / VCCQ (1.8V/3.3V)
```

---

## 5. 音频编解码器

适用：ES8388, RT5651, WM8960, ALC5616, SGTL5000 等

### 5.1 关键参数

| 参数 | 含义 | 典型值 |
|------|------|--------|
| DAC SNR | 数模转换信噪比 | 90-110 dB |
| ADC SNR | 模数转换信噪比 | 85-100 dB |
| THD+N | 总谐波失真 + 噪声 | -80 ~ -100 dB |
| Sample Rate | 采样率范围 | 8kHz - 192kHz |
| Bit Depth | 位深度 | 16/24/32 bit |
| Headphone Output | 耳机输出功率 | 25-40 mW @ 32Ω |
| Speaker Output | 喇叭功率 | Class-D: 1-2W |
| I2S Format | 音频接口格式 | I2S/Left-Justified/Right-Justified/PCM/TDM |
| Control Interface | 控制接口 | I2C (地址查 AD 引脚) |
| MCLK | 主时钟要求 | 256fs / 512fs / PLL |

### 5.2 音频信号通路分析

```
分析 Codec Datasheet 时必须理清信号通路:

   MIC IN → PGA → ADC → Digital → I2S TX → (到主控)
   (主控) → I2S RX → Digital → DAC → Mixer → HP/SPK OUT

关键寄存器组:
  - Power Management: 各模块供电开关
  - Clock Control: MCLK/BCLK/LRCK 分频
  - ADC/DAC Control: 采样率、位深
  - Mixer Control: 信号路由
  - Volume Control: 各级音量
  - GPIO/Jack Detection: 耳机插拔检测
```

---

## 6. 显示驱动类

适用：MIPI DSI 面板驱动 IC (如 ILI9881C, ST7789, SSD1306)、HDMI 转换芯片、LVDS 接收器

### 6.1 面板驱动 IC 关键参数

| 参数 | 含义 |
|------|------|
| Resolution | 分辨率 (如 720×1280) |
| Interface | MIPI DSI / SPI / Parallel RGB |
| Color Depth | 色深 (16/18/24 bit) |
| Lane Count | MIPI DSI 通道数 |
| Refresh Rate | 刷新率 |
| Display Timing | HFP/HBP/HSA/VFP/VBP/VSA |
| Init Code Sequence | 初始化命令序列 |

### 6.2 MIPI DSI 面板必查项

```
从 Datasheet 提取 Display Timing:
  - HSYNC Width (HSA): {X} clk
  - HBP (H Back Porch): {X} clk
  - HFP (H Front Porch): {X} clk
  - VSYNC Width (VSA): {X} lines
  - VBP (V Back Porch): {X} lines
  - VFP (V Front Porch): {X} lines
  - Pixel Clock: {X} MHz
  
从初始化代码表提取：
  - 每一行: {Delay, Command, Param_count, Param...}
  - 注意 Generic Write / DCS Write 的区别
```

---

## 7. 时钟与定时器

适用：RTC (DS1307, PCF8563)、晶振、时钟发生器 (Si5351)、看门狗

### 7.1 RTC 关键参数

| 参数 | 含义 |
|------|------|
| Accuracy | 年误差 (ppm → 秒/天) |
| Battery Backup | 备电电流 / 电池寿命 |
| Interface | I2C 地址 |
| Alarm Functions | 闹钟功能数量 |
| Square Wave Output | 方波输出频率选项 |
| Timestamp | 事件时间戳功能 |

---

## 8. 通用分析检查清单

不管什么类型的器件，分析完 Datasheet 后都要过一遍：

### 8.1 硬件设计检查

- [ ] 电源电压在推荐范围内
- [ ] 去耦电容数量、容值、摆放位置符合要求
- [ ] 未使用的输入引脚已正确处理（上拉/下拉/接地）
- [ ] I/O 电平与主控兼容（3.3V vs 1.8V）
- [ ] 复位引脚有正确的上拉/RC 延迟
- [ ] 地址/配置引脚的外部电阻已正确连接
- [ ] ESD 防护满足应用要求（外部接口需额外保护）
- [ ] 封装热阻 × 功耗 < 允许温升

### 8.2 软件/驱动开发检查

- [ ] 已确认芯片 ID (WHO_AM_I / Device ID)
- [ ] 复位后等待时间满足要求
- [ ] 寄存器初始化顺序正确
- [ ] 时钟配置正确（SPI Mode / I2C Speed）
- [ ] 中断配置和清除流程正确
- [ ] 低功耗模式的进出流程已了解
- [ ] 已查看 Errata / Known Issues

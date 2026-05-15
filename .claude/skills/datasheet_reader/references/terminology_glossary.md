# 芯片手册中英文术语对照表

> 本文件是 `datasheet_reader` 技能的参考资料，提供芯片手册和数据手册中常见的中英文术语对照，帮助工程师快速理解英文技术文档。

## 目录

1. [文档结构与章节名称](#1-文档结构与章节名称)
2. [电源与供电](#2-电源与供电)
3. [数字逻辑与接口](#3-数字逻辑与接口)
4. [模拟参数](#4-模拟参数)
5. [时序参数](#5-时序参数)
6. [封装与引脚](#6-封装与引脚)
7. [存储器](#7-存储器)
8. [通信协议](#8-通信协议)
9. [处理器与系统](#9-处理器与系统)
10. [可靠性与测试](#10-可靠性与测试)
11. [PCB 与硬件设计](#11-pcb-与硬件设计)
12. [缩写速查](#12-缩写速查)

---

## 1. 文档结构与章节名称

| 英文 | 中文 | 补充说明 |
|------|------|---------|
| Datasheet | 数据手册 | 器件的完整技术文档 |
| Technical Reference Manual (TRM) | 技术参考手册 | SoC 的寄存器级详细文档 |
| Application Note (AN) | 应用笔记 | 特定应用场景的指导文档 |
| Errata | 勘误表 | 芯片已知问题和临时解决方案 |
| User Guide / User Manual | 用户指南/用户手册 | 使用方法和操作指导 |
| Programming Manual | 编程手册 | 软件编程接口说明 |
| Migration Guide | 迁移指南 | 从旧型号升级的指导 |
| Product Brief | 产品简介 | 1-2 页的快速概览 |
| General Description | 产品概述 | 器件的总体功能描述 |
| Features | 特性列表 | 关键功能点的条目化列表 |
| Block Diagram | 框图/方框图 | 内部架构的示意图 |
| Functional Description | 功能描述 | 工作原理的详细说明 |
| Electrical Characteristics | 电气特性 | 保证的电气参数表格 |
| Absolute Maximum Ratings (AMR) | 绝对最大额定值 | 超过会损坏的极限值 |
| Recommended Operating Conditions | 推荐工作条件 | 保证正常工作的范围 |
| Typical Application | 典型应用/参考电路 | 推荐的应用电路 |
| Register Map | 寄存器映射表 | 寄存器地址和功能概览 |
| Register Description | 寄存器描述 | 各寄存器的位域详细说明 |
| Ordering Information | 订购信息 | 型号编码规则和订购细节 |
| Package Information | 封装信息 | 封装尺寸和焊盘图 |
| Pin Configuration | 引脚配置图 | 引脚排列的顶视图 |
| Pin Description | 引脚描述/引脚定义 | 每个引脚的功能说明 |
| Timing Diagram | 时序图 | 信号时间关系的波形图 |
| Application Circuit | 应用电路 | 推荐的外围电路设计 |
| BOM (Bill of Materials) | 物料清单 | 所需元器件列表 |
| Layout Guidelines | 布局指南 | PCB 放置走线建议 |
| Revision History | 修订历史 | 文档版本变更记录 |
| Table of Contents (TOC) | 目录 | 章节索引 |
| Preliminary | 初步版/预发布 | 参数可能变更 |
| Production | 量产版 | 参数已固化 |

---

## 2. 电源与供电

| 英文 | 中文 | 典型单位 | 说明 |
|------|------|---------|------|
| VDD / VCC | 电源电压 | V | 正电源端 |
| VSS / GND | 地/接地 | - | 参考地端 |
| VDDIO / VCCIO | I/O 电源电压 | V | I/O 域供电 |
| VDDQ | 存储器 I/O 电源 | V | DDR 信号电源 |
| VIN | 输入电压 | V | 电源输入端 |
| VOUT | 输出电压 | V | 电源输出端 |
| VREF | 参考电压 | V | 基准电压 |
| VDD_CORE | 核心电压 | V | CPU/逻辑核心供电 |
| IDD / ICC | 工作电流/电源电流 | mA | 正常工作消耗电流 |
| IQ / IGND | 静态电流/地电流 | μA | 空载时的消耗 |
| ISHUTDOWN | 关断电流 | nA/μA | 关断模式下的漏电流 |
| Power Dissipation (PD) | 功耗 | mW | 器件总消耗功率 |
| Power Supply Rejection Ratio (PSRR) | 电源抑制比 | dB | 抑制电源纹波的能力 |
| Dropout Voltage | 压差/跌落电压 | mV | LDO 最小输入输出压差 |
| Soft Start | 软启动 | ms | 输出电压缓慢上升避免浪涌 |
| UVLO | 欠压锁定 | V | Under-Voltage Lock-Out |
| OVP | 过压保护 | V | Over-Voltage Protection |
| OCP | 过流保护 | A | Over-Current Protection |
| Thermal Shutdown (TSD) | 过温关断 | °C | 温度过高自动关断 |
| Inrush Current | 浪涌电流 | A | 上电瞬间的峰值电流 |
| Ripple | 纹波 | mV | 输出电压的交流分量 |
| Load Regulation | 负载调整率 | %/mV | 负载变化时输出电压变化 |
| Line Regulation | 电源调整率 | %/mV | 输入变化时输出电压变化 |
| Efficiency (η) | 效率 | % | DC-DC 转换效率 |

---

## 3. 数字逻辑与接口

| 英文 | 中文 | 说明 |
|------|------|------|
| VIH | 输入高电平阈值 | 高于此值识别为逻辑 1 |
| VIL | 输入低电平阈值 | 低于此值识别为逻辑 0 |
| VOH | 输出高电平 | 输出逻辑 1 的最低电压 |
| VOL | 输出低电平 | 输出逻辑 0 的最高电压 |
| IOH | 输出高电平电流 | 拉电流 (Source) |
| IOL | 输出低电平电流 | 灌电流 (Sink) |
| Drive Strength | 驱动强度/驱动能力 | 引脚输出电流能力 |
| Pull-Up / Pull-Down | 上拉/下拉 | 内部或外部上/下拉电阻 |
| Open Drain (OD) | 开漏输出 | 只能拉低，高需外部上拉 |
| Push-Pull (PP) | 推挽输出 | 可主动输出高和低 |
| Tri-State / Hi-Z | 三态/高阻态 | 输出断开，呈高阻抗 |
| Schmitt Trigger | 施密特触发器 | 输入带迟滞，抗噪声 |
| Hysteresis | 迟滞 | 上升和下降阈值的差值 |
| Slew Rate | 摆率/转换速率 | 输出电压变化的快慢 |
| Latch-Up | 闩锁效应 | CMOS 寄生晶闸管导通 |
| Leakage Current | 漏电流 | 引脚的寄生泄漏电流 |
| Input Capacitance (CIN) | 输入电容 | 引脚看进去的寄生电容 |
| Fan-Out | 扇出系数 | 一个输出能驱动的输入数 |

---

## 4. 模拟参数

| 英文 | 中文 | 典型单位 | 说明 |
|------|------|---------|------|
| Resolution | 分辨率 | bits | ADC/DAC 的位数 |
| DNL (Differential Nonlinearity) | 微分非线性 | LSB | 相邻码间的误差 |
| INL (Integral Nonlinearity) | 积分非线性 | LSB | 总体线性偏差 |
| SNR (Signal-to-Noise Ratio) | 信噪比 | dB | 信号功率/噪声功率 |
| SFDR | 无杂散动态范围 | dB | 信号/最大杂散 |
| THD (Total Harmonic Distortion) | 总谐波失真 | dB/% | 谐波分量占比 |
| ENOB (Effective Number of Bits) | 有效位数 | bits | 考虑噪声后的实际精度 |
| Offset Error | 偏移误差/零偏 | LSB/mV | 零点的系统偏移 |
| Gain Error | 增益误差 | LSB/% | 满量程的斜率偏差 |
| CMRR (Common Mode Rejection Ratio) | 共模抑制比 | dB | 差分放大器的指标 |
| Bandwidth (-3dB) | 带宽 | Hz/MHz | 频率响应的 -3dB 点 |
| Slew Rate | 压摆率 | V/μs | 运放输出电压变化速率 |
| Input Bias Current | 输入偏置电流 | pA/nA | 运放输入端电流 |
| Input Offset Voltage | 输入失调电压 | μV/mV | 运放输入端电压偏移 |
| Sampling Rate | 采样率 | SPS/kSPS/MSPS | ADC 每秒采样次数 |
| Conversion Time | 转换时间 | μs | 一次 ADC 转换耗时 |

---

## 5. 时序参数

| 英文 | 缩写 | 中文 | 说明 |
|------|------|------|------|
| Setup Time | tSU / tS | 建立时间 | 数据需提前于时钟沿稳定 |
| Hold Time | tHD / tH | 保持时间 | 数据需在时钟沿后保持稳定 |
| Propagation Delay | tPD | 传播延迟 | 输入变化到输出变化的时间 |
| Rise Time | tR / tRISE | 上升时间 | 10%→90% 或 20%→80% |
| Fall Time | tF / tFALL | 下降时间 | 90%→10% 或 80%→20% |
| Clock-to-Output Delay | tCO | 时钟到输出延迟 | 时钟沿到数据输出有效 |
| Access Time | tACC | 访问时间 | 地址/CS 有效到数据输出 |
| Cycle Time | tCYC | 周期时间 | 一个完整操作周期 |
| Clock Frequency | fCLK | 时钟频率 | 最大允许工作频率 |
| Duty Cycle | - | 占空比 | 高电平时间/周期 |
| Jitter | - | 抖动 | 时钟边沿的随机偏移 |
| Skew | - | 偏斜 | 并行信号间的时间差 |
| Clock-to-Data Skew (tSKEW) | tSKEW | 时钟数据偏斜 | 时钟与数据到达时间差 |
| Turn-Around Time | tTAT | 方向切换时间 | 收发方向切换延迟 |
| Recovery Time | tREC | 恢复时间 | 片选释放到下次操作 |
| Power-Up Time | tPU | 上电时间 | 上电到可操作 |
| Wake-Up Time | tWK | 唤醒时间 | 低功耗到活跃模式 |
| Reset Pulse Width | tRST | 复位脉冲宽度 | 最小复位信号持续时间 |

---

## 6. 封装与引脚

| 英文 | 中文 | 说明 |
|------|------|------|
| Package | 封装 | 器件的物理外壳 |
| QFP (Quad Flat Package) | 四侧扁平封装 | 四面有引脚 |
| QFN (Quad Flat No-Lead) | 四侧无引脚封装 | 底部焊盘，节省空间 |
| BGA (Ball Grid Array) | 球栅阵列封装 | 底部焊球，高密度 |
| SOIC (Small Outline IC) | 小外形封装 | 两侧有引脚 |
| TSSOP | 薄型缩小外形封装 | SOIC 的缩小版 |
| DIP (Dual In-line Package) | 双列直插封装 | 传统插件封装 |
| WLCSP (Wafer Level CSP) | 晶圆级芯片封装 | 最小尺寸封装 |
| Die / Bare Die | 裸片 | 未封装的芯片 |
| Land Pad | 焊盘 | PCB 上的连接点 |
| Pin / Lead | 引脚/引线 | 封装的电气连接端 |
| NC (No Connect) | 空脚/未连接 | 无内部连接的引脚 |
| Exposed Pad / Thermal Pad | 散热焊盘 | 底部的散热片 |
| Pitch | 引脚间距 | 相邻引脚的中心距离 |
| Bond Wire | 键合线 | 芯片到引脚的连接线 |
| θJA (Theta Junction-to-Ambient) | 结到环境热阻 | °C/W，散热的关键参数 |
| θJC (Theta Junction-to-Case) | 结到外壳热阻 | °C/W |
| TJ (Junction Temperature) | 结温 | 芯片内部最高温度 |
| TA (Ambient Temperature) | 环境温度 | 芯片周围空气温度 |

---

## 7. 存储器

| 英文 | 中文 | 说明 |
|------|------|------|
| SRAM (Static RAM) | 静态随机存储器 | 无需刷新，速度快 |
| DRAM (Dynamic RAM) | 动态随机存储器 | 需要刷新，密度高 |
| SDRAM | 同步 DRAM | 同步于时钟 |
| DDR (Double Data Rate) | 双倍速率 | 上下沿都传数据 |
| LPDDR (Low Power DDR) | 低功耗 DDR | 移动设备用 |
| NOR Flash | 或非闪存 | 可寻址到字节，支持 XIP |
| NAND Flash | 与非闪存 | 大容量，按页/块操作 |
| eMMC | 嵌入式 MMC | 内置控制器的 NAND |
| EEPROM | 电可擦只读存储器 | 按字节擦写，小容量 |
| OTP (One-Time Programmable) | 一次性编程 | 写入后不可更改 |
| eFuse | 电子熔丝 | 类似 OTP 的熔丝存储 |
| Boot ROM | 启动 ROM | 芯片内置的启动程序 |
| Cache | 高速缓存 | CPU 近端的快速存储 |
| Bank | 存储体 | 存储器的独立分区 |
| Row / Column | 行/列 | DRAM 的地址组织方式 |
| Refresh | 刷新 | DRAM 定期重写以保持数据 |
| P/E Cycle | 编程/擦除循环 | Flash 寿命的度量单位 |
| Endurance | 耐久性 | 可擦写次数 |
| Retention | 数据保持 | 断电后数据保存时间 |
| ECC (Error Correcting Code) | 纠错码 | 检测和纠正存储错误 |

---

## 8. 通信协议

| 英文/缩写 | 中文 | 说明 |
|-----------|------|------|
| I2C (Inter-Integrated Circuit) | I2C 总线 | 两线制串行总线 (SDA+SCL) |
| SPI (Serial Peripheral Interface) | SPI 总线 | 四线制高速串行 (MOSI/MISO/SCK/CS) |
| UART (Universal Async Receiver/Transmitter) | 通用异步收发器 | 串口通信 (TX/RX) |
| I2S (Inter-IC Sound) | I2S 音频总线 | 数字音频传输 |
| CAN (Controller Area Network) | 控制器局域网 | 汽车/工业总线 |
| USB (Universal Serial Bus) | 通用串行总线 | 高速外设接口 |
| PCIe (PCI Express) | PCI Express 总线 | 高速串行互联 |
| MIPI DSI | MIPI 显示接口 | 移动显示串行接口 |
| MIPI CSI | MIPI 摄像头接口 | 移动摄像头串行接口 |
| RGMII | RGMII 以太网接口 | 千兆以太网 MAC-PHY 接口 |
| RMII | RMII 以太网接口 | 百兆以太网精简接口 |
| SDIO | SD 卡接口 | 安全数字卡输入输出 |
| JTAG | 联合测试动作小组 | 调试和边界扫描接口 |
| SWD (Serial Wire Debug) | 串行线调试 | ARM 两线调试接口 |
| MDIO | 管理数据 I/O | 以太网 PHY 管理接口 |
| PWM (Pulse Width Modulation) | 脉冲宽度调制 | 占空比编码的信号 |
| GPIO (General Purpose I/O) | 通用输入输出 | 可编程数字 I/O 引脚 |

---

## 9. 处理器与系统

| 英文 | 中文 | 说明 |
|------|------|------|
| SoC (System on Chip) | 片上系统 | 集成 CPU+外设的芯片 |
| MCU (Microcontroller) | 微控制器/单片机 | 集成 Flash+RAM 的小系统 |
| MPU (Microprocessor Unit) | 微处理器 | 需要外部存储的处理器 |
| CPU (Central Processing Unit) | 中央处理器 | 主运算单元 |
| DSP (Digital Signal Processor) | 数字信号处理器 | 专用算法处理器 |
| GPU (Graphics Processing Unit) | 图形处理器 | 图形加速单元 |
| NPU (Neural Processing Unit) | 神经网络处理器 | AI 推理加速单元 |
| ISP (Image Signal Processor) | 图像信号处理器 | 摄像头图像处理 |
| DMA (Direct Memory Access) | 直接内存访问 | 无需 CPU 的数据搬运 |
| IOMMU | I/O 内存管理单元 | 外设地址转换 |
| MMU (Memory Management Unit) | 内存管理单元 | 虚拟地址翻译 |
| GIC (Generic Interrupt Controller) | 通用中断控制器 | ARM 中断管理 |
| NVIC | 嵌套向量中断控制器 | Cortex-M 中断控制器 |
| CRU (Clock & Reset Unit) | 时钟复位单元 | 时钟/复位管理 |
| PMU (Power Management Unit) | 电源管理单元 | 电源域管理 |
| GRF (General Register File) | 通用寄存器文件 | 系统级杂项配置 |
| Watchdog (WDT) | 看门狗定时器 | 系统异常自动复位 |
| PLL (Phase-Locked Loop) | 锁相环 | 时钟倍频电路 |
| Boot Loader | 引导加载程序 | 启动时加载系统的程序 |
| Firmware | 固件 | 嵌入芯片的底层软件 |
| BSP (Board Support Package) | 板级支持包 | 板卡的驱动和配置集合 |

---

## 10. 可靠性与测试

| 英文 | 中文 | 说明 |
|------|------|------|
| ESD (Electrostatic Discharge) | 静电放电 | 静电损害防护等级 |
| HBM (Human Body Model) | 人体模型 | ESD 测试的人体放电模型 |
| CDM (Charged Device Model) | 带电器件模型 | ESD 测试的器件放电模型 |
| MTBF (Mean Time Between Failures) | 平均无故障时间 | 可靠性度量 |
| FIT (Failures In Time) | 单位时间故障数 | 每 10^9 小时的故障次数 |
| Industrial Grade | 工业级 | -40°C ~ +85°C |
| Commercial Grade | 商业级 | 0°C ~ +70°C |
| Automotive Grade (AEC-Q100) | 车规级 | -40°C ~ +125°C |
| Military Grade | 军工级 | -55°C ~ +125°C |
| Burn-In | 老化测试 | 高温加速筛选 |
| Qualification Report | 认证报告 | 产品合格性测试报告 |
| DPPM | 百万次缺陷数 | 质量水平指标 |
| RoHS | 有害物质限制 | 欧盟环保指令 |
| MSL (Moisture Sensitivity Level) | 湿度敏感等级 | 封装吸潮敏感程度 |

---

## 11. PCB 与硬件设计

| 英文 | 中文 | 说明 |
|------|------|------|
| Decoupling Capacitor | 去耦电容 | 滤除电源噪声 |
| Bypass Capacitor | 旁路电容 | 类似去耦电容 |
| Bulk Capacitor | 储能电容 | 大容量电源滤波 |
| Impedance Matching | 阻抗匹配 | 高速信号的传输线匹配 |
| Termination Resistor | 终端电阻/匹配电阻 | 消除信号反射 |
| Pull-Up Resistor | 上拉电阻 | 引脚拉到高电平 |
| Pull-Down Resistor | 下拉电阻 | 引脚拉到低电平 |
| Ferrite Bead | 磁珠 | 高频噪声抑制 |
| TVS (Transient Voltage Suppressor) | 瞬态抑制二极管 | 过压保护 |
| EMI (Electromagnetic Interference) | 电磁干扰 | 辐射/传导干扰 |
| EMC (Electromagnetic Compatibility) | 电磁兼容性 | 抗干扰和低辐射 |
| Ground Plane | 接地平面 | PCB 的完整地层 |
| Via | 过孔 | PCB 层间连接 |
| Trace | 走线 | PCB 上的导线 |
| Copper Pour | 铜皮/铺铜 | 大面积铜覆盖 |
| Solder Mask | 阻焊层 | PCB 的绿色保护层 |
| Silk Screen | 丝印层 | PCB 上的标识文字 |
| Footprint / Land Pattern | 封装焊盘图 | PCB 上的元件焊盘 |
| Keepout Area | 禁止区域 | 不允许走线/放件的区域 |
| Reference Designator | 位号 | 元件在电路中的编号 (R1, C1, U1) |
| Design Rule Check (DRC) | 设计规则检查 | PCB 设计的自动校验 |

---

## 12. 缩写速查

快速查找常见缩写的全称和含义：

| 缩写 | 全称 | 中文 |
|------|------|------|
| ADC | Analog-to-Digital Converter | 模数转换器 |
| DAC | Digital-to-Analog Converter | 数模转换器 |
| LDO | Low Dropout Regulator | 低压差线性稳压器 |
| DC-DC | DC-DC Converter | 直流-直流转换器 |
| PMIC | Power Management IC | 电源管理芯片 |
| PGA | Programmable Gain Amplifier | 可编程增益放大器 |
| OPA | Operational Amplifier | 运算放大器 |
| MOSFET | Metal-Oxide-Semiconductor FET | 金属氧化物半导体场效应管 |
| BJT | Bipolar Junction Transistor | 双极型晶体管 |
| LED | Light Emitting Diode | 发光二极管 |
| LCD | Liquid Crystal Display | 液晶显示器 |
| OLED | Organic LED | 有机发光二极管 |
| IMU | Inertial Measurement Unit | 惯性测量单元 |
| MEMS | Micro-Electro-Mechanical Systems | 微机电系统 |
| PHY | Physical Layer | 物理层收发器 |
| MAC | Media Access Control | 介质访问控制 |
| FIFO | First In First Out | 先进先出缓冲 |
| FSM | Finite State Machine | 有限状态机 |
| POR | Power-On Reset | 上电复位 |
| BOR | Brown-Out Reset | 欠压复位 |
| ISR | Interrupt Service Routine | 中断服务程序 |
| HAL | Hardware Abstraction Layer | 硬件抽象层 |
| SDK | Software Development Kit | 软件开发套件 |
| IP | Intellectual Property (Core) | 知识产权核 / IP 核 |
| ASIC | Application-Specific IC | 专用集成电路 |
| FPGA | Field-Programmable Gate Array | 现场可编程门阵列 |
| SOI | Silicon On Insulator | 绝缘体上硅 |
| BGA | Ball Grid Array | 球栅阵列 |
| CSP | Chip Scale Package | 芯片级封装 |
| SMT | Surface Mount Technology | 表面贴装技术 |
| THT | Through-Hole Technology | 通孔插装技术 |
| XIP | Execute In Place | 就地执行 |
| AXI | Advanced eXtensible Interface | 高级可扩展接口 |
| AHB | Advanced High-performance Bus | 高性能总线 |
| APB | Advanced Peripheral Bus | 外设总线 |

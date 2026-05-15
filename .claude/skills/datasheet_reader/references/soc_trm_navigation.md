# SoC 技术参考手册 (TRM) 深入导航指南

> 本文件是 `datasheet_reader` 技能的参考资料，提供 SoC TRM 的深入分析方法，包括寄存器级解读、时钟树分析和初始化代码生成。

## 目录

1. [TRM 整体结构与阅读策略](#1-trm-整体结构与阅读策略)
2. [Memory Map 解读](#2-memory-map-解读)
3. [时钟与复位 (CRU) 深入](#3-时钟与复位-cru-深入)
4. [引脚复用 (IOMUX) 分析](#4-引脚复用-iomux-分析)
5. [IP Controller 寄存器级分析](#5-ip-controller-寄存器级分析)
6. [中断系统分析](#6-中断系统分析)
7. [DMA 系统分析](#7-dma-系统分析)
8. [初始化代码生成方法](#8-初始化代码生成方法)
9. [常见 IP Controller 分析模板](#9-常见-ip-controller-分析模板)
10. [SoC Datasheet vs TRM 对照](#10-soc-datasheet-vs-trm-对照)

---

## 1. TRM 整体结构与阅读策略

### 1.1 典型 TRM 章节分布

以 Rockchip RK3568 TRM 为例（Part1 + Part2，共 ~3000 页）:

```
Part1:
  Ch1:  System Overview (系统概述、总线架构)
  Ch2:  System Address Mapping (地址映射)
  Ch3:  CRU (时钟复位单元)
  Ch4:  PMU (电源管理)
  Ch5:  GRF/SGRF (通用寄存器文件)
  Ch6:  GPIO
  Ch7:  I2C
  Ch8:  SPI
  Ch9:  UART
  Ch10: PWM
  Ch11: Timer
  Ch12: WDT (看门狗)
  Ch13: SARADC
  ...

Part2:
  Ch1:  VOP (显示控制器)
  Ch2:  HDMI
  Ch3:  DSI (MIPI 显示)
  Ch4:  VICAP/ISP (摄像头)
  Ch5:  VPU (视频编解码)
  Ch6:  GPU
  Ch7:  USB
  Ch8:  PCIe
  Ch9:  GMAC (以太网)
  Ch10: MMC (eMMC/SD)
  ...
```

### 1.2 高效阅读策略

```
绝不要从头到尾阅读 TRM！正确的方法是：

1. 首先只看 System Overview → 了解芯片整体架构
2. 接下来看 Address Mapping → 记住/收藏常用 IP 的基地址
3. 然后按任务需要，跳到特定 IP 章节

跳到 IP 章节后的阅读顺序：
①  Overview → 了解这个 IP 能做什么
②  Feature List → 确认特性满足需求
③  Block Diagram → 理解内部结构
④  Functional Description → 工作原理
⑤  Programming Guide → 初始化步骤（最有价值的部分！）
⑥  Register Description → 按需查询具体寄存器

最后补充：
⑦  CRU 章节 → 找该 IP 的时钟配置
⑧  IOMUX/GRF 章节 → 找该 IP 的引脚复用配置
⑨  中断映射表 → 找该 IP 的中断号
```

---

## 2. Memory Map 解读

### 2.1 地址空间概念

```
SoC 的所有 IP Controller 都映射在 CPU 的地址空间中。
每个 IP 占用一段连续的地址空间，由 基地址 (Base Address) 确定。

示例 (RK3568):
  0xFDD40000 - UART0 (调试串口)
  0xFE650000 - I2C0
  0xFE660000 - I2C1
  0xFE670000 - I2C2
  0xFE2C0000 - SPI0
  0xFE610000 - UART1
  0xFE620000 - UART2

寄存器物理地址 = 基地址 + 偏移量
例如 UART0 的 RBR 寄存器: 0xFDD40000 + 0x0000 = 0xFDD40000
```

### 2.2 从 Memory Map 快速定位

```
用户问："SPI1 的基地址是多少？"
→ 翻到 Address Mapping 章节
→ 搜索 "SPI" → 找到 SPI1 Base Address
→ 记录: SPI1_BASE = 0x{ADDR}
→ 然后所有 SPI1 寄存器 = SPI1_BASE + offset
```

---

## 3. 时钟与复位 (CRU) 深入

### 3.1 时钟树概念

```
      ┌─────────┐
      │ 外部晶振 │ 24MHz XTAL
      └────┬────┘
           │
    ┌──────┴──────┐
    │  PLL (锁相环) │ ×N 倍频
    ├─ APLL (CPU)  │ → 1.8GHz
    ├─ GPLL (General)│ → 1188MHz
    ├─ CPLL (Codec) │ → 1000MHz
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │  分频器 (DIV) │ ÷N 分频
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │  选择器 (MUX) │ 选择时钟源
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │  门控 (GATE)  │ 开/关时钟
    └──────┬──────┘
           │
        IP Controller
```

### 3.2 使能一个 IP 的时钟步骤

```
要使用某个 IP，必须：
1. 确保 PLL 已锁定 (通常 bootloader 已完成)
2. 配置时钟选择器 (MUX) → 选择合适的时钟源
3. 配置分频器 (DIV) → 设置目标频率
4. 打开门控 (GATE) → 使能时钟输出到 IP

对应寄存器 (以 Rockchip 为例)：
  CRU_CLKSEL_CONxx: 选择时钟源和分频比
  CRU_CLKGATE_CONxx: 控制时钟门控 (0=使能, 1=关闭)
```

### 3.3 复位控制

```
软复位 (Soft Reset):
  CRU_SOFTRST_CONxx: 控制各 IP 的软复位
  写 1 = 复位, 写 0 = 释放

使用流程:
  1. 写 1 → 进入复位
  2. 等待足够时间 (通常 >10 时钟周期)
  3. 写 0 → 释放复位
  4. 等待 IP 就绪
```

---

## 4. 引脚复用 (IOMUX) 分析

### 4.1 IOMUX 概念

```
SoC 引脚数有限，每个物理引脚可以复用为多种功能：

GPIO1_A0:
  func0: GPIO1_A0     (GPIO 模式)
  func1: I2C3_SDA     (I2C 数据线)
  func2: UART3_RX     (串口接收)
  func3: PWM8_M0      (PWM 输出)

同一时刻只能选择一个功能！

引脚复用由 IOMUX 寄存器控制:
  GRF_GPIO1A_IOMUX_L[1:0] = 0b00 → GPIO
  GRF_GPIO1A_IOMUX_L[1:0] = 0b01 → I2C3_SDA
  GRF_GPIO1A_IOMUX_L[1:0] = 0b10 → UART3_RX
  GRF_GPIO1A_IOMUX_L[1:0] = 0b11 → PWM8_M0
```

### 4.2 从 TRM 中提取 IOMUX 信息

```
用户问："I2C3 的引脚在哪里？"

分析步骤：
1. 搜索 "I2C3" 在 IOMUX 章节或 GRF 寄存器中
2. 找到 I2C3_SDA 和 I2C3_SCL 的复用配置
3. 记录：
   - I2C3_SDA = GPIO{X}_{Y}, IOMUX func = {N}
   - I2C3_SCL = GPIO{X}_{Z}, IOMUX func = {N}
4. 如果有多个 MUX 组 (M0/M1)：
   - I2C3_SDA_M0 = GPIO1_A0
   - I2C3_SDA_M1 = GPIO4_C0
   → 需要用户确认使用哪组
```

### 4.3 引脚电气属性配置

```
除了功能选择，还需配置引脚电气属性：

  Pull Control (上下拉):
    GRF_GPIO{X}{Y}_P: 00=None, 01=PullUp, 10=PullDown
    
  Drive Strength (驱动强度):
    GRF_GPIO{X}{Y}_DS: 00=2mA, 01=4mA, 10=8mA, 11=12mA
    
  Schmitt Trigger (施密特触发):
    GRF_GPIO{X}{Y}_SMT: 0=Disable, 1=Enable
    
  Slew Rate (摆率):
    GRF_GPIO{X}{Y}_SL: 0=Slow, 1=Fast
```

---

## 5. IP Controller 寄存器级分析

### 5.1 通用 IP Controller 结构

每个 IP 章节通常包含以下寄存器组：

```
1. 版本/ID 寄存器 (Version/ID)
   → 可做芯片验证，确认 IP 版本

2. 控制寄存器 (Control Register - CTRL/CON)
   → 使能、模式选择、参数配置

3. 状态寄存器 (Status Register - STS/SR)
   → 当前状态、错误标志

4. 中断相关寄存器
   - 中断使能 (Interrupt Enable - IE)
   - 中断状态 (Interrupt Status - IS/ISR)
   - 中断清除 (Interrupt Clear - IC/ICR)
   → 注意 W1C 类型：写 1 清零

5. 数据寄存器 (Data Register - DR/FIFO)
   → 发送/接收数据

6. FIFO 控制 (FIFO Control)
   → FIFO 深度、水线、清空
```

### 5.2 寄存器级初始化通用步骤

```c
/* 通用 IP 初始化模板 */

// 0. 使能时钟 & 释放复位 (在 CRU 配置)
//    → 这一步在 TRM 的 CRU 章节

// 1. 配置 IOMUX (在 GRF 配置)
//    → 这一步在 TRM 的 GRF/IOMUX 章节

// 2. 读版本寄存器确认 IP 存在
version = readl(BASE + VERSION_REG);

// 3. 失能 IP (配置前先停止)
writel(0, BASE + CTRL_REG);

// 4. 配置工作模式和参数
writel(MODE_CONFIG, BASE + CON_REG0);
writel(PARAM_CONFIG, BASE + CON_REG1);

// 5. 配置中断 (如需要)
writel(INT_MASK, BASE + IE_REG);

// 6. 清除残留中断
writel(0xFFFFFFFF, BASE + IC_REG);

// 7. 使能 IP
writel(ENABLE_BIT, BASE + CTRL_REG);
```

---

## 6. 中断系统分析

### 6.1 中断映射表

```
TRM 的中断映射表通常以表格形式给出：

| IRQ# | Source     | Description            |
|------|------------|------------------------|
| 32   | UART0      | UART0 中断             |
| 33   | UART1      | UART1 中断             |
| 34   | UART2      | UART2 中断             |
| 56   | I2C0       | I2C0 中断              |
| 57   | I2C1       | I2C1 中断              |
| 78   | SPI0       | SPI0 中断              |
| ...  | ...        | ...                    |

注意: ARM GIC 中断号通常从 32 开始
      (0-15 是 SGI, 16-31 是 PPI, 32+ 是 SPI)
      Linux 内核的中断号 = GIC SPI 号 + 32
```

### 6.2 IP 内部中断分析

```
每个 IP Controller 内部通常有多个中断源，
通过中断相关寄存器汇聚成一个中断输出到 GIC。

典型中断寄存器组：
  IP_INT_EN:   各中断源使能控制
  IP_INT_STS:  各中断源触发状态
  IP_INT_CLR:  清除中断 (W1C)
  IP_INT_MASK: 中断屏蔽

中断处理流程:
  1. 读 INT_STS → 确认哪些中断触发
  2. 处理对应事件
  3. 写 INT_CLR → 清除已处理的中断 (W1C)
```

---

## 7. DMA 系统分析

### 7.1 DMA 请求映射

```
DMA 控制器为多个 IP 提供数据搬运服务。
每个 IP 的 DMA 请求在映射表中有固定编号：

| DMA Req# | Source        | Direction |
|----------|---------------|-----------|
| 0        | UART0_TX      | MEM→PER  |
| 1        | UART0_RX      | PER→MEM  |
| 4        | SPI0_TX       | MEM→PER  |
| 5        | SPI0_RX       | PER→MEM  |
| ...      | ...           | ...       |

使用 DMA 时需在 DMA 控制器中配置:
  - 通道分配 (Channel)
  - 请求号绑定 (Peripheral Request)
  - 源地址/目标地址
  - 传输长度
  - 突发长度 (Burst Length)
```

---

## 8. 初始化代码生成方法

### 8.1 从 TRM 生成裸机初始化代码

```
给定 IP 和目标功能, 从 TRM 生成代码的步骤:

1. 从 CRU 章节提取:
   - 时钟门控寄存器和位号
   - 复位寄存器和位号
   → 生成时钟使能和复位释放代码

2. 从 GRF/IOMUX 章节提取:
   - IOMUX 寄存器和功能选择值
   - Pull/Drive 配置
   → 生成引脚配置代码

3. 从 IP 章节 Programming Guide 提取:
   - 初始化步骤
   - 各步骤对应的寄存器操作
   → 生成功能初始化代码

4. 从中断映射表提取:
   - GIC IRQ 号
   → 生成中断注册代码
```

### 8.2 代码输出模板

```c
/* ====================================
 * {IP Name} 初始化代码
 * 基于 {SoC} TRM {Version}
 * ==================================== */

#include <stdint.h>

/* 基地址定义 */
#define {IP}_BASE          0x{BASE_ADDR}
#define CRU_BASE           0x{CRU_ADDR}
#define GRF_BASE           0x{GRF_ADDR}

/* 寄存器偏移 */
#define {IP}_CTRL          ({IP}_BASE + 0x{OFF1})
#define {IP}_CON0          ({IP}_BASE + 0x{OFF2})
// ...

/* 位域定义 */
#define {IP}_CTRL_EN       BIT(0)
// ...

/* 内存映射 I/O 操作 */
#define readl(addr)        (*(volatile uint32_t *)(addr))
#define writel(val, addr)  (*(volatile uint32_t *)(addr) = (val))

void {ip}_init(void)
{
    /* Step 1: 使能时钟 */
    writel(/* write enable + gate bit */, CRU_BASE + CRU_CLKGATE_CON{X});
    
    /* Step 2: 释放复位 */
    writel(/* write enable + reset bit */, CRU_BASE + CRU_SOFTRST_CON{X});
    
    /* Step 3: 配置 IOMUX */
    writel(/* mux value */, GRF_BASE + GRF_GPIO{X}{Y}_IOMUX);
    
    /* Step 4: 配置 IP */
    writel(0, {IP}_CTRL);           // 先失能
    writel(CONFIG_VAL, {IP}_CON0);  // 配置参数
    writel({IP}_CTRL_EN, {IP}_CTRL); // 使能
}
```

---

## 9. 常见 IP Controller 分析模板

### 9.1 UART Controller

```
提取要素:
  - 支持的波特率范围
  - FIFO 深度 (TX/RX)
  - 流控支持 (RTS/CTS)
  - DMA 支持
  - 特殊模式 (IrDA, RS485, 9-bit)

关键寄存器:
  - LCR (Line Control): 数据位/停止位/校验
  - DLL/DLH (Divisor Latch): 波特率分频
  - FCR (FIFO Control): FIFO 使能和水线
  - IER (Interrupt Enable): 中断控制
  - LSR (Line Status): 接收/发送状态
```

### 9.2 I2C Controller

```
提取要素:
  - 支持的速率模式 (Standard/Fast/Fast-Plus/High-Speed)
  - 主从模式支持
  - 10-bit 地址支持
  - FIFO 深度
  - 自动拉伸 (Clock Stretching)

关键寄存器:
  - CON (Control): Master/Slave, 速率模式, ACK
  - TAR (Target Address): 目标设备地址
  - DATA_CMD (Data + Command): 读/写数据
  - SS_SCL_HCNT/LCNT: 标准模式时钟高低电平计数
  - FS_SCL_HCNT/LCNT: 快速模式时钟高低电平计数
  - STATUS: 传输状态
  - TXFLR/RXFLR: FIFO 数据量
```

### 9.3 SPI Controller

```
提取要素:
  - Master/Slave 支持
  - 最大时钟频率
  - 数据帧大小 (4-16 bit)
  - FIFO 深度
  - SPI 模式 (Mode 0/1/2/3: CPOL+CPHA 组合)
  - DMA 支持
  - 片选数量 (CS)

关键寄存器:
  - CTRLR0: 数据帧大小, SPI 模式, 传输模式
  - CTRLR1: 接收数据长度 (仅接收模式)
  - ENR: SPI 使能
  - BAUDR: 波特率分频
  - SER: 片选使能
  - TXFTLR/RXFTLR: FIFO 水线
  - SR: 状态寄存器 (BUSY, TXFULL, RXEMPTY)
  - DR: 数据寄存器
```

---

## 10. SoC Datasheet vs TRM 对照

### 10.1 两者的区别

| 内容 | SoC Datasheet | TRM |
|------|--------------|-----|
| 目标读者 | 硬件工程师 | 软件/驱动工程师 |
| 引脚信息 | 完整引脚复用表、Ball Map | 仅 IOMUX 寄存器 |
| 电气特性 | 详细 (I/O 电平、驱动能力) | 无 |
| 封装信息 | 详细 (尺寸图、焊盘) | 无 |
| IP 寄存器 | 简要功能列表 | 完整寄存器级描述 |
| 时钟树 | 框图概览 | 完整 PLL/DIV/MUX/GATE 寄存器 |
| 功耗数据 | 典型功耗表 | 无 |

### 10.2 交叉查询策略

```
硬件设计问题 → 先查 SoC Datasheet
  如: 引脚电平、封装、功耗、温度范围

驱动开发问题 → 先查 TRM
  如: 寄存器配置、初始化步骤、中断处理

共同需要 → 两者交叉查看
  如: 引脚复用 (DS 给物理引脚, TRM 给 IOMUX 寄存器)
```

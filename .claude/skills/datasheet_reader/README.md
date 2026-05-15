# datasheet_reader — 芯片手册与数据手册阅读分析技能

> **Version:** V1.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`datasheet_reader` 技能指导 AI 系统化地分析电子元器件数据手册 (Datasheet) 和 SoC 技术参考手册 (TRM)，帮助嵌入式工程师从几十到几千页的英文手册中快速精确提取关键信息。

**解决的核心痛点：**
- 工程师英文基础薄弱，难以阅读英文数据手册
- 面对数百页手册不知道从哪里入手
- 看不懂电气参数表格、时序图、寄存器定义
- 不清楚哪些参数是设计关键、哪些可以跳过
- SoC TRM 动辄几千页，查找 IP 配置信息效率极低

## 适用场景

| 文档类型 | 典型页数 | 适用场景 |
|----------|---------|---------|
| **外设数据手册** | 10-200 页 | 传感器、PMIC、PHY、Codec、显示驱动 IC 等 |
| **SoC 数据手册** | 50-300 页 | 芯片选型、引脚复用、电气特性查询 |
| **SoC TRM** | 500-5000 页 | IP 寄存器配置、驱动开发、初始化代码 |
| **应用笔记** | 5-50 页 | 参考电路设计、PCB 布局指导 |

## 功能说明

### 功能一：外设数据手册分析

三级递进分析法，从宏观到微观逐层深入。

**你可以这样提问：**
- "帮我分析这个温度传感器的 datasheet"
- "这颗 LDO 的关键参数是什么？"
- "这个 sensor 的 I2C 地址怎么配置？"

**AI 会返回：**
- 器件功能概览卡（一句话说明功能、接口类型、供电范围、封装）
- 关键电气参数提取表（包含测试条件）
- 引脚连接说明和注意事项
- 寄存器快速参考表（按需）
- 初始化代码模板（按需）

### 功能二：SoC TRM 导航与分析

指导 AI 在数千页 TRM 中快速定位目标 IP Controller 的关键信息。

**你可以这样提问：**
- "RK3568 的 SPI 控制器支持什么模式？最大时钟多少？"
- "帮我看看这个 TRM 里 I2C 控制器的寄存器"
- "UART2 的基地址、时钟门控、中断号分别是多少？"

**AI 会返回：**
- IP Controller 摘要卡（基地址、特性、时钟源、中断号、DMA、IOMUX）
- 寄存器快速参考表（地址、位域、读写属性、复位值）
- 初始化步骤和代码模板
- 使用限制和注意事项

### 功能三：术语翻译与解释

中英文技术术语对照，帮助工程师理解手册内容。

**你可以这样提问：**
- "什么是 AMR？和推荐工作条件有什么区别？"
- "Setup Time 和 Hold Time 是啥意思？"
- "这个 datasheet 里 IOH、VOL 这些参数是什么？"

**AI 会返回：**
- 术语中英文对照和含义解释
- 结合具体手册上下文的理解说明
- 相关参数的工程含义和设计影响

### 功能四：参数比较与选型辅助

支持多个器件的参数对比分析。

**你可以这样提问：**
- "帮我比较这两个加速度计的参数"
- "这两颗 LDO 哪个更适合电池供电场景？"

**AI 会返回：**
- 参数对比表格（按关键维度对比）
- 各器件的优缺点分析
- 基于使用场景的推荐

### 功能五：初始化代码生成

基于手册自动生成可用的初始化代码框架。

**你可以这样提问：**
- "根据这个 datasheet 帮我写一个 I2C 初始化代码"
- "从 TRM 里提取 SPI 控制器的初始化序列"

**AI 会返回：**
- 带注释的初始化代码（标注 Datasheet 章节出处）
- 关键配置参数的来源说明
- 需要用户根据实际硬件调整的部分

## 触发方式

以下情况会自动触发本技能：

**关键词触发：**
- 数据手册、datasheet、芯片手册、TRM、reference manual
- 寄存器、register map、引脚复用、pinmux
- 电气特性、时序图、timing diagram
- AMR、绝对最大额定值、典型应用电路
- 初始化序列、init sequence

**场景触发：**
- 用户提供了芯片/器件 PDF 并要求分析
- 用户询问某芯片的技术参数
- 用户要求翻译手册中的英文术语
- 用户要求生成基于手册的初始化代码
- 用户在驱动开发中需要回查手册确认规格

## 文件结构

```
datasheet_reader/
 SKILL.md                                 # 主技能文件 (AI 自动加载, ~450 行)
 README.md                                # 本说明文档 (供人阅读)
 references/                              # 深入参考资料 (AI 按需加载)
     peripheral_datasheet_guide.md        # 各类外设 IC 的详细分析方法
     soc_trm_navigation.md               # SoC TRM 深入导航指南
     terminology_glossary.md             # 中英文电子术语对照表 (200+ 词条)
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含核心知识（手册类型识别、三级分析流程、输出模板、核心术语）
- **references/**：AI 根据具体问题按需加载。例如：
  - 用户分析外设 Datasheet（传感器/PMIC/PHY 等）→ 加载 `peripheral_datasheet_guide.md`
  - 用户导航 SoC TRM、需要寄存器级分析 → 加载 `soc_trm_navigation.md`
  - 用户不认识英文术语、需要翻译对照 → 加载 `terminology_glossary.md`

## 使用示例

### 示例一：分析传感器数据手册

```
用户：帮我看看这个加速度计的 datasheet，关键参数是什么？
AI：
  1. 识别文档类型：外设数据手册（传感器类）
  2. 一级扫描：提取 General Description / Features / Block Diagram
  3. 二级提取：量程、灵敏度、ODR、I2C 地址、供电、功耗
  4. 输出 Quick Summary Card + 关键参数表
  5. 主动提醒：I/O 电平兼容性、上电等待时间、WHO_AM_I 验证
```

### 示例二：从 TRM 查找 IP 配置

```
用户：RK3568 的 I2C2 基地址是多少？怎么初始化？
AI：
  1. 识别文档类型：SoC TRM
  2. 定位 Memory Map 章节 → 找到 I2C2 基地址
  3. 跳转 I2C 章节 → 提取 Feature、Register Map
  4. 查 CRU 章节 → 找到时钟门控和复位寄存器
  5. 查 IOMUX 章节 → 找到 I2C2 的引脚配置
  6. 输出 IP Controller 摘要卡 + 初始化代码
```

### 示例三：术语翻译

```
用户：datasheet 上的 PSRR 和 Load Regulation 是什么？
AI：
  - PSRR (Power Supply Rejection Ratio) = 电源抑制比
    表示 LDO/稳压器抑制输入电源纹波的能力，单位 dB
    数值越高越好，典型 60-80dB
  - Load Regulation = 负载调整率
    负载电流变化时输出电压的稳定性
    数值越小越好，典型 0.1-1%
```

## 知识来源

本技能的知识体系基于以下来源构建：

- **《How to Read a Datasheet》** — D. Grover, WIMS Outreach Program
- **《如何查看数据手册》** — Analog Devices (ADI) 官方培训材料
- **《怎样读芯片数据手册》** — LM555 Datasheet 注释翻译版
- **Rockchip RK3568/RK3588 TRM** — 瑞芯微官方技术参考手册
- **Rockchip RK3568/RK3588 Datasheet** — 瑞芯微官方数据手册
- **Texas Instruments Datasheet Reading Guide** — TI 数据手册阅读指导
- **ARM Architecture Reference Manual** — ARM 架构参考手册
- 多年嵌入式芯片硬件/软件开发实践经验

## License

MIT License

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-04-05 | 首次发布：三级分析流程、SoC TRM 导航、术语对照表、5 种输出模板 |

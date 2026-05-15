# ASoC 框架深度解析

## 1. ASoC 三层驱动结构

### 1.1 Machine Driver (声卡驱动)
```c
/* Machine driver 负责:
 * 1. 定义 CPU DAI 和 Codec 之间的连接 (dai_link)
 * 2. 定义音频路由 (audio_map / routing)
 * 3. 定义外部 widget (Speaker, Headphone, Mic)
 * 4. 可选: 耳机检测, PA 控制等板级逻辑
 */

/* 最简单的方式: 使用 simple-audio-card (DTS 定义, 无需 C 代码) */
/* 复杂场景: 编写自定义 machine driver */

/* dai_link 关键字段: */
struct snd_soc_dai_link {
    const char *name;           /* 链路名称 */
    const char *stream_name;    /* PCM 流名称 */
    /* CPU DAI */
    struct snd_soc_dai_link_component *cpus;
    /* Codec */
    struct snd_soc_dai_link_component *codecs;
    /* Platform (DMA) */
    struct snd_soc_dai_link_component *platforms;
    /* DAI 格式 */
    unsigned int dai_fmt;       /* SND_SOC_DAIFMT_I2S | SND_SOC_DAIFMT_NB_NF | ... */
    /* 操作回调 */
    const struct snd_soc_ops *ops;
};
```

### 1.2 CPU DAI Driver
```
CPU DAI 驱动负责:
- 配置 I2S/TDM/PCM 控制器寄存器
- 设置时钟 (BCLK, LRCK, MCLK)
- DMA 传输控制
- 支持的格式/采样率/声道数声明

关键回调:
- set_fmt():    设置 I2S/LEFT_J/RIGHT_J, master/slave
- set_sysclk(): 设置系统时钟 (MCLK)
- hw_params():  根据采样率/位宽配置 BCLK, LRCK 分频
- trigger():    start/stop DMA 传输
```

### 1.3 Codec Driver
```
Codec 驱动负责:
- Codec 芯片寄存器访问 (通常 I2C, 少数 SPI)
- DAPM widget 和 route 定义
- Mixer 控制 (kcontrol) 定义
- Codec 内部时钟/PLL 配置
- Power management (suspend/resume)

关键组成:
- snd_soc_component_driver: 驱动主体
- snd_soc_dapm_widget[]:    DAPM 部件列表
- snd_soc_dapm_route[]:     DAPM 路由列表
- snd_kcontrol_new[]:       用户可调控制项
- snd_soc_dai_driver:       DAI 接口描述
```

## 2. DAPM Widget 完整说明

### 2.1 Widget 类型
```
类型                    用途                     上电条件
─────────────────────────────────────────────────────────
snd_soc_dapm_input      外部信号输入端口          连接到有效路径
snd_soc_dapm_output     外部信号输出端口          连接到有效路径
snd_soc_dapm_adc        ADC (模→数转换)          有输入信号
snd_soc_dapm_dac        DAC (数→模转换)          有播放数据
snd_soc_dapm_mixer      混音器                   至少一个输入开启
snd_soc_dapm_mux        多选一                   选中的输入有信号
snd_soc_dapm_pga        可编程增益放大            输入有信号
snd_soc_dapm_hp         耳机输出                 连接到耳机
snd_soc_dapm_spk        喇叭输出                 连接到喇叭
snd_soc_dapm_mic        麦克风输入               麦克风使能
snd_soc_dapm_supply     电源供应 (AVDD/DVDD)     被依赖的 widget 需要
snd_soc_dapm_regulator  外部 regulator           被依赖的 widget 需要
snd_soc_dapm_clock      时钟供应                 被依赖的 widget 需要
snd_soc_dapm_aif_in     AI 接口输入 (DAI RX)     CPU 端发送数据
snd_soc_dapm_aif_out    AI 接口输出 (DAI TX)     CPU 端接收数据
```

### 2.2 Route 定义
```c
/* Route 格式: { "sink", "control", "source" }
 * control = NULL 表示直连 (无需开关控制)
 * control = "Switch Name" 表示需要 amixer 控制的开关
 */
static const struct snd_soc_dapm_route audio_routes[] = {
    /* 播放路径: */
    { "DAC", NULL, "AIF1RX" },       /* DAI 输入 → DAC */
    { "Output Mixer", "DAC Switch", "DAC" },  /* DAC → 混音器 (受 Switch 控制) */
    { "SPOL", NULL, "Output Mixer" },  /* 混音器 → SPK 左 */
    { "SPOR", NULL, "Output Mixer" },  /* 混音器 → SPK 右 */

    /* 录音路径: */
    { "BST1", NULL, "IN1P" },        /* MIC 输入 → Boost */
    { "ADC", NULL, "BST1" },         /* Boost → ADC */
    { "AIF1TX", NULL, "ADC" },       /* ADC → DAI 输出 */
};
```

## 3. 时钟体系

```
音频时钟关系:
MCLK (Master Clock) → 通常 11.2896MHz (44.1kHz 系) 或 12.288MHz (48kHz 系)
BCLK (Bit Clock)    = 采样率 × 声道数 × 位宽
                      例: 48000 × 2 × 16 = 1.536MHz
LRCK (L/R Clock)    = 采样率 (48000Hz)
                      也称 WS (Word Select) 或 FS (Frame Sync)

MCLK 来源:
1. SoC I2S 控制器输出 (最常见, DTS 中配 clock-names = "mclk")
2. 外部晶振 (独立时钟, 精度更高)
3. Codec 内部 PLL 从 BCLK 生成 (MCLK-free 模式)

DTS 中 mclk-fs = <256> 含义:
  MCLK = mclk-fs × 采样率 = 256 × 48000 = 12.288MHz
  常见值: 256 (32bit_slot×2ch×4倍频), 384, 512
```

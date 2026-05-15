---
name: linux_audio
description: "通用 Linux 音频问题排查与调试技能，不限于任何特定 SoC 平台。覆盖 ALSA/ASoC 架构调试、声卡识别、codec 驱动、DAI 链路 (I2S/TDM/PCM/PDM/SPDIF)、DAPM 电源管理与音频通路分析、PulseAudio/PipeWire 用户态框架、录音播放工具 (aplay/arecord/amixer)、音频质量 (噪音/爆音/底噪/失真) 排查。触发关键词：音频、audio、ALSA、ASoC、声卡、sound card、aplay、arecord、amixer、codec、I2S、TDM、SPDIF、HDMI 音频、DAI、dai-link、simple-audio-card、DAPM、widget、route、PulseAudio、PipeWire、录音、播放、没有声音、无声、音量、噪音、爆音、底噪、失真、耳机、speaker、麦克风、RT5651、ES8388、WM8960、audio-routing、功放、PA。当用户描述任何 Linux 音频层面的问题（声音不出、录音失败、音质差、声卡不识别等），都应触发本技能。"
---
<!-- ===== QUICK NAVIGATION ===== -->
| 快速导航 | 跳转链接 |
|---------|---------|
| 声卡识别 | [§1](#1-声卡识别与基础检查) |
| ALSA 工具 | [§2](#2-alsa-工具使用) |
| ASoC 架构 | [§3](#3-asoc-架构与-dai-链路) |
| DAPM | [§4](#4-dapm-电源管理) |
| DTS 配置 | [§5](#5-音频-dts-配置) |
| Codec 调试 | [§6](#6-codec-驱动调试) |
| 音质问题 | [§7](#7-音频质量问题排查) |
| 用户态框架 | [§8](#8-pulseaudiopipewire) |
| HDMI 音频 | [§9](#9-hdmi-音频) |
| 常见问题 | [§10](#10-常见音频问题速查) |
| 参考索引 | [§REF](#reference-index) |

---

## 诊断决策树
```
音频问题
├── /proc/asound/cards 为空 → §1 声卡识别 + §6 Codec 驱动
├── 有声卡但 aplay 报错 → §2 ALSA 工具 + §3 DAI 链路
├── aplay 不报错但没声音 → §4 DAPM 通路 + §2 mixer 设置
├── 播放有杂音/爆音/噪音 → §7 音质问题
├── 录音无声或杂音 → §2 录音配置 + §4 DAPM 输入通路
├── HDMI 无声 → §9 HDMI 音频
├── PulseAudio 问题 → §8 用户态框架
├── 耳机检测失效 → §6 Codec 检测功能
└── DTS 音频节点配置 → §5 DTS 配置
```

---

## §1 声卡识别与基础检查

### 1.1 检查声卡
```bash
# 查看系统识别的声卡:
cat /proc/asound/cards
# 正常输出:
#  0 [rockchiprt5651 ]: rockchip_rt5651 - rockchip,rt5651
#                       rockchip,rt5651
#  1 [rockchiphdmi   ]: rockchip_hdmi - rockchip,hdmi
#                       rockchip,hdmi

# 如果为空 → 声卡未注册, 需要检查:
# 1. DTS 中声卡节点是否存在且 status = "okay"
# 2. codec 驱动是否编入内核
# 3. dmesg | grep -i "asoc\|codec\|sound\|audio\|i2s\|dai"
# 4. I2C codec: i2cdetect 检查 codec 芯片是否在总线上

# 查看 PCM 设备:
cat /proc/asound/pcm
# 00-00: xxx : xxx : playback 1 : capture 1

# 查看声卡详细信息:
cat /proc/asound/card0/codec#0       # codec 寄存器 (如果支持)
cat /proc/asound/card0/id            # 声卡 ID
```

### 1.2 驱动加载检查
```bash
# 检查相关模块:
lsmod | grep -i snd
# snd_soc_rt5651   → codec 驱动
# snd_soc_core     → ASoC 核心
# snd_pcm          → PCM 子系统

# 检查设备:
ls /dev/snd/
# controlC0    → 控制设备 (mixer)
# pcmC0D0p     → 播放设备 (Card0 Device0 Playback)
# pcmC0D0c     → 录音设备 (Card0 Device0 Capture)
# timer         → 定时器
```

---

## §2 ALSA 工具使用

### 2.1 播放与录音
```bash
# 播放 WAV 文件:
aplay -D hw:0,0 test.wav                    # 使用硬件设备
aplay -D plughw:0,0 test.wav                # 使用 plughw (自动格式转换)
aplay -D default test.wav                    # 使用默认设备

# 生成测试音并播放:
speaker-test -D hw:0,0 -c 2 -t sine         # 正弦波测试, 2 声道

# 录音:
arecord -D hw:0,0 -f S16_LE -r 48000 -c 2 -d 10 record.wav
# -f S16_LE: 16bit 小端
# -r 48000: 48kHz 采样率
# -c 2: 双声道
# -d 10: 录 10 秒

# 查看支持的格式:
aplay -D hw:0,0 --dump-hw-params /dev/null 2>&1
# 显示支持的格式、采样率、声道数范围
```

### 2.2 Mixer 控制
```bash
# 列出所有控制项:
amixer -c 0 contents                        # 详细信息
amixer -c 0 scontrols                       # 简单控制列表

# 查看/设置音量:
amixer -c 0 get 'Master Playback Volume'
amixer -c 0 set 'Master Playback Volume' 80%
amixer -c 0 set 'DAC Playback Volume' 192   # 或用原始值

# 启用/禁用通路:
amixer -c 0 set 'Speaker' on
amixer -c 0 set 'Headphone' on
amixer -c 0 set 'Capture Switch' on         # 启用录音通道

# 交互式 mixer:
alsamixer -c 0                              # TUI 界面

# 保存/恢复 mixer 设置:
alsactl store -f /etc/asound.state          # 保存
alsactl restore -f /etc/asound.state        # 恢复
```

---

## §3 ASoC 架构与 DAI 链路

### 3.1 ASoC 三层架构
```
┌─────────────────────────────────┐
│         Machine Driver           │  ← 声卡定义 (连接 CPU DAI 和 Codec)
│  (simple-audio-card / 板级驱动)  │
├─────────────────────────────────┤
│       CPU DAI Driver             │  ← SoC 的 I2S/TDM/PCM 控制器驱动
│    (i2s / tdm / spdif)           │
├─────────────────────────────────┤
│       Codec Driver               │  ← 外部 codec 芯片驱动
│  (rt5651 / es8388 / wm8960)     │
└─────────────────────────────────┘

DAI (Digital Audio Interface) 类型:
- I2S:  最常用, PCM 数据 + BCLK + LRCK (WS)
- TDM:  I2S 扩展, 多声道时分复用
- PCM:  短帧同步, 电话/Modem 场景
- PDM:  数字麦克风 (DMIC)
- SPDIF: 数字音频传输 (光纤/同轴)
```

### 3.2 DAI 链路调试
```bash
# 查看 DAI 链路:
cat /sys/kernel/debug/asoc/components
# 列出所有已注册的 ASoC 组件 (CPU DAI / Codec / Platform)

cat /sys/kernel/debug/asoc/<card_name>/dai_links
# 显示 DAI link 状态

# DAI 不匹配常见问题:
# 1. 格式不匹配: CPU DAI 只支持 I2S, Codec 配了 LEFT_J
# 2. 主从不匹配: 两边都配了 master 或都配了 slave
# 3. 采样率/位宽不匹配
# 4. BCLK/LRCK 时钟配置错误
#
# dmesg 中搜:
# "ASoC: xxx <-> yyy No matching rates"
# "ASoC: can't set xxx hw params"
```

---

## §4 DAPM 电源管理

### 4.1 DAPM 概念
```
DAPM = Dynamic Audio Power Management
目的: 自动管理音频通路上的电源, 未使用的 widget 自动关闭

Widget 类型:
- ADC / DAC: 模数/数模转换器
- Mixer:     混音器
- MUX:       多路选择器
- PGA:       可编程增益放大器
- Supply:    电源供应
- Input/Output: 物理输入输出端口
- HP / SPK / MIC: 耳机/喇叭/麦克风

Route (路由): 描述 Widget 之间的连接关系
当一条完整的 route 从 Input → ... → Output 建立时, 路径上所有 widget 自动上电
```

### 4.2 DAPM 调试
```bash
# 查看所有 widget 状态:
cat /sys/kernel/debug/asoc/<card_name>/<codec_name>/dapm_widgets
# 每个 widget 显示:
# "name" - "type" - power: on/off

# 查看路由 (完整音频通路):
cat /sys/kernel/debug/asoc/<card_name>/<codec_name>/dapm_routes

# 典型的播放通路:
# PCM → DAC → Output Mixer → SPK → Speaker Out
# 如果中间任何一环断了 → 没声音

# 手动开关 widget (调试用):
echo "Speaker" > /sys/kernel/debug/asoc/<card_name>/<codec_name>/dapm_widget_on

# 常见 DAPM 问题:
# 1. 播放没声音但 aplay 不报错
#    → 检查 DAPM widget 是否全部 power on
#    → 检查 route 是否完整连通
#    → 检查 mixer 开关 (amixer 有些开关控制 DAPM 路由)
```

---

## §5 音频 DTS 配置

### 5.1 simple-audio-card
```dts
/* 最常用的声卡 DTS 配置方式 */
sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "my-sound-card";
    simple-audio-card,format = "i2s";         /* i2s / left_j / right_j / dsp_a / dsp_b */
    simple-audio-card,mclk-fs = <256>;        /* MCLK = 256 × fs (采样率) */

    /* 声道映射 */
    simple-audio-card,widgets =
        "Speaker", "Speaker Out",
        "Headphone", "Headphone Jack",
        "Microphone", "Mic In";
    simple-audio-card,routing =
        "Speaker Out", "SPOL",        /* 物理端口 ← codec 输出 pin */
        "Speaker Out", "SPOR",
        "Headphone Jack", "HPOL",
        "Headphone Jack", "HPOR",
        "IN1P", "Mic In";             /* codec 输入 pin ← 物理端口 */

    simple-audio-card,cpu {
        sound-dai = <&i2s0>;
    };
    simple-audio-card,codec {
        sound-dai = <&rt5651>;
    };
};
```

### 5.2 多 DAI 链路
```dts
/* 多个声卡或多 DAI link */
sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "multi-codec";

    simple-audio-card,dai-link@0 {
        format = "i2s";
        cpu { sound-dai = <&i2s0>; };
        codec { sound-dai = <&rt5651>; };
    };

    simple-audio-card,dai-link@1 {
        format = "i2s";
        cpu { sound-dai = <&i2s1>; };
        codec { sound-dai = <&hdmi>; };
    };
};
```

### 5.3 Codec I2C 节点
```dts
&i2c1 {
    status = "okay";

    rt5651: rt5651@1a {
        compatible = "realtek,rt5651";
        reg = <0x1a>;                          /* I2C 地址 */
        clocks = <&cru SCLK_I2S_8CH_OUT>;     /* MCLK 来源 */
        clock-names = "mclk";
        #sound-dai-cells = <0>;
    };
};
```

---

## §6 Codec 驱动调试

### 6.1 Codec I2C 通信检查
```bash
# 检查 I2C 总线上是否存在 codec:
i2cdetect -y 1
# 应该在 codec 地址处显示设备 (如 0x1a)

# 读取 codec 寄存器 (调试):
i2cget -y 1 0x1a 0x00                  # 读 vendor ID
cat /sys/kernel/debug/asoc/<codec_name>/codec_reg  # 通过 debugfs
```

### 6.2 常见 Codec 错误
```
dmesg 常见错误:

"rt5651 1-001a: Device with ID register 0x0000 is not rt5651"
→ I2C 通信失败, 读到的 ID 不对
→ 检查: I2C 地址, I2C 总线号, 供电, 上拉电阻

"ASoC: failed to init xxx: -517"
→ -517 = -EPROBE_DEFER, 依赖的资源 (clock/regulator) 未就绪
→ 稍后会重试, 如果一直 defer 需检查依赖链

"xxx_set_dai_sysclk: unsupported clock 12288000"
→ MCLK 频率不被 codec 支持
→ 调整 DTS 中 mclk-fs 或时钟源
```

---

## §7 音频质量问题排查

### 7.1 爆音 / Pop Noise
```
原因及解决:
1. DAPM 上下电顺序不当
   → 确保静音后再切换通路, 或调整 codec 的 DAPM 顺序

2. 播放前后的 pop
   → PA 功放需要延迟使能/禁用
   → DTS 中加 hp-det-gpio, spk-con-gpio 控制时序

3. DMA 欠载 (underrun)
   → aplay -v 看是否有 xrun
   → 增大 ALSA buffer: --buffer-size=4096 --period-size=1024
```

### 7.2 噪音 / 底噪
```
排查方向:
1. 电源噪音 (power supply noise)
   → 检查 codec AVDD/DVDD 电源纹波
   → 尝试加滤波电容

2. 地线环路 (ground loop)
   → 检查数字地和模拟地是否正确分离

3. 时钟抖动 (clock jitter)
   → MCLK 质量差导致采样抖动
   → 使用低 jitter 的时钟源

4. I2S 信号完整性
   → 检查 BCLK/LRCK/SDATA 走线
   → 使用示波器测量信号质量
```

### 7.3 音量过小
```bash
# 逐级检查增益:
amixer -c 0 contents | grep -A 3 -i "volume\|gain"
# 从 DAC → Mixer → AMP 逐级检查是否有衰减
# 外部 PA 功放是否使能 (需要 GPIO 控制)

# 检查 DTS 中的 audio-amplifier:
# audio-amplifier {
#     enable-gpios = <&gpio1 RK_PA4 GPIO_ACTIVE_HIGH>;
# };
```

---

## §8 PulseAudio/PipeWire

### 8.1 PulseAudio
```bash
# 查看状态:
pactl list sinks short                 # 输出设备
pactl list sources short               # 输入设备
pactl info                             # 服务信息

# 设置默认设备:
pactl set-default-sink <sink_name>

# 音量控制:
pactl set-sink-volume @DEFAULT_SINK@ 80%
pactl set-sink-mute @DEFAULT_SINK@ toggle

# 调试:
pulseaudio --kill
pulseaudio --start --log-level=debug --log-target=file:/tmp/pa.log
```

### 8.2 PipeWire
```bash
# 查看状态:
wpctl status                           # 全局状态
pw-cli list-objects                    # 所有对象

# 设置默认:
wpctl set-default <id>

# 音量:
wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.8
```

---

## §9 HDMI 音频

```bash
# HDMI 音频单独声卡:
cat /proc/asound/cards
# 1 [HDMI]: rockchip_hdmi ...

# 播放:
aplay -D hw:1,0 test.wav

# HDMI 音频不出:
# 1. 检查 HDMI 显示是否正常 (音频依赖热插拔检测)
# 2. 检查 DTS 中 HDMI 的声卡节点
# 3. amixer -c 1 检查 HDMI mixer 设置
# 4. 某些 HDMI 显示器不支持音频
```

---

## §10 常见音频问题速查

| 问题 | 可能原因 | 排查方向 |
|------|---------|---------|
| 声卡不存在 | Codec probe 失败 | dmesg + I2C 检测 + DTS |
| aplay 报 "No such device" | PCM 设备号错误 | cat /proc/asound/pcm |
| aplay 报 "Device or resource busy" | 设备被占用 | fuser /dev/snd/* |
| aplay 不报错但无声 | DAPM 通路断/mixer 未开 | DAPM widget + amixer |
| 播放有爆音 | DMA underrun/PA 时序 | buffer-size 调大, PA delay |
| 录音无声 | 输入通路未配/增益为 0 | amixer capture 设置 |
| 音质差/失真 | 采样率不匹配/时钟差 | hw_params 检查, 时钟源 |
| 耳机插入无切换 | jack detect 配置 | codec GPIO/IRQ |

---

## Reference Index

| 参考文件 | 内容概要 |
|---------|---------|
| [asoc_architecture.md](references/asoc_architecture.md) | ASoC 框架深度解析, Machine/CPU DAI/Codec 三层驱动编写, DAPM widget/route 完整说明 |
| [codec_driver_guide.md](references/codec_driver_guide.md) | 常见 Codec 驱动移植指南 (RT5651/ES8388/WM8960/NAU8822 等), regmap 配置, jack 检测 |
| [audio_quality_debug.md](references/audio_quality_debug.md) | 音频质量深度调试, 示波器测量, 信噪比分析, 爆音/底噪/失真根因分析 |

# linux_audio — Linux 音频问题排查与调试技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`linux_audio` 是一个**多平台通用**的 Linux 音频问题排查与调试技能，专注于解决各类音频问题：ALSA 框架与 ASoC 架构调试、声卡识别与配置、Codec 驱动调试、DAI 链路 (I2S/TDM/PCM/PDM/SPDIF) 配置、DAPM 动态电源管理、音频通路分析、PulseAudio/PipeWire 用户态框架、录音播放工具使用、音频质量 (噪音/爆音/底噪/失真) 排查。

## 适用平台

| 平台 | 芯片示例 | 适用性 |
|------|---------|-------|
| Rockchip 瑞芯微 | RK3588 / RK3568 / RK3566 | ✅ |
| AllWinner 全志 | A64 / H616 / T527 | ✅ |
| NXP i.MX | i.MX8M / i.MX6 | ✅ |
| TI Sitara | AM335x / AM62x | ✅ |
| STM32MP | STM32MP157 / STM32MP135 | ✅ |
| Broadcom | BCM2711 (RPi4) | ✅ |
| RISC-V | StarFive JH7110 / T-Head | ✅ |
| Qualcomm | QCS404 / Snapdragon | ✅ |

> 凡运行 Linux 内核且使用 ALSA/ASoC 音频子系统的平台均适用。

## 功能说明

### 1. 声卡识别与基础检查
- **问题**: /dev/snd/ 为空, 声卡不识别
- **方法**: /proc/asound/cards, dmesg 检查 codec probe, I2C 通信验证

### 2. ALSA 工具使用
- **工具**: aplay (播放), arecord (录音), amixer (mixer 控制), speaker-test (测试音)
- **方法**: hw_params 检查, mixer 增益设置, format/rate 匹配

### 3. ASoC 与 DAPM 调试
- **问题**: aplay 不报错但无声, 通路未连通
- **方法**: DAPM widget 状态检查, route 分析, debugfs → dapm_widgets

### 4. DTS 音频配置
- **方法**: simple-audio-card 配置, routing 定义, MCLK/I2S 时钟, codec I2C 节点

### 5. 音频质量问题
- **问题**: 爆音 (pop), 噪音, 底噪, 失真
- **方法**: buffer/period 调优, 电源检查, 时钟 jitter 分析, PA 时序

### 6. 用户态音频框架
- **工具**: PulseAudio (pactl/pacmd), PipeWire (wpctl/pw-cli)

## 触发方式

当用户描述以下类型的问题时，本技能会被自动触发：

- 提到声音不出、没声音、无声、静音
- 提到 ALSA、ASoC、aplay、arecord、amixer
- 提到声卡、sound card、/proc/asound
- 提到 codec、I2S、DAI、DAPM
- 提到音频质量: 爆音、噪音、底噪、失真、音量小
- 提到 PulseAudio、PipeWire
- 提到 HDMI 音频、SPDIF
- 提到具体 codec 芯片: RT5651、ES8388、WM8960 等

## 文件结构

```
linux_audio/
├── SKILL.md                                 # 主技能文件
├── README.md                                # 本说明文档
└── references/
    ├── asoc_architecture.md                 # ASoC 框架深度解析
    ├── codec_driver_guide.md                # Codec 驱动移植指南
    └── audio_quality_debug.md               # 音频质量深度调试
```

## 文件加载机制

- `SKILL.md` 在技能触发时**自动加载**，提供完整的诊断决策树和常用命令
- `references/*.md` 按需加载，当 SKILL.md 中的内容不够详细时引用

## 使用示例

### 示例 1: 声卡不识别
> 用户: "/proc/asound/cards 显示为空，板子上有个 RT5651 codec"

技能响应：排查 I2C 通信 (i2cdetect), 检查 DTS 声卡节点, 分析 dmesg 中 RT5651 probe 日志。

### 示例 2: 播放无声
> 用户: "aplay 播放 WAV 文件不报错，但喇叭没声音"

技能响应：检查 DAPM widget 状态, 验证 amixer 通路开关和增益, 确认 PA 功放 GPIO 是否使能。

### 示例 3: 爆音问题
> 用户: "播放开始和结束时有明显的 pop 声"

技能响应：分析 DAPM 上下电顺序, 检查 PA 使能延迟, 调整 buffer-size, 检查 codec anti-pop 寄存器。

## 知识来源

- Linux kernel Documentation/sound/
- ALSA 官方文档 (alsa-project.org)
- ASoC 内核文档 (Documentation/sound/soc/)
- 各 codec 芯片 datasheet
- 嵌入式 Linux 音频调试实践经验

## License

MIT License — 详见仓库根目录 LICENSE 文件

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

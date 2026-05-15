# 常见 Codec 驱动移植指南

## 1. Codec 移植通用流程

```
Step 1: 硬件确认
  → Codec 芯片型号, I2C 地址, 供电 (AVDD/DVDD 电压)
  → I2S 连接: 哪个 I2S 控制器, MCLK 来源
  → 其他 GPIO: Reset, Power enable, HP-DET

Step 2: 内核配置
  → 确认 codec 驱动在内核中 (menuconfig → Sound → ALSA → ASoC → CODEC)
  → 编为模块 (=m) 或内建 (=y)

Step 3: DTS 配置
  → I2C 节点: codec 芯片
  → I2S 节点: 使能 CPU DAI
  → Sound 节点: simple-audio-card 连接 CPU DAI 和 Codec
  → Pinctrl: I2S 引脚

Step 4: 验证
  → dmesg 检查 probe 日志
  → /proc/asound/cards 确认声卡注册
  → speaker-test 测试播放
  → arecord 测试录音
```

## 2. RT5651 移植

### 2.1 基本信息
```
I2C 地址: 0x1a
供电: AVDD=3.3V, DVDD=1.8V
支持: I2S, 48kHz/44.1kHz 多采样率
功能: 双 ADC/DAC, 耳机检测, 内置 LDO
驱动: sound/soc/codecs/rt5651.c
CONFIG: CONFIG_SND_SOC_RT5651=y
```

### 2.2 DTS 示例
```dts
&i2c1 {
    status = "okay";
    rt5651: rt5651@1a {
        compatible = "realtek,rt5651";
        reg = <0x1a>;
        clocks = <&cru SCLK_I2S_8CH_OUT>;
        clock-names = "mclk";
        #sound-dai-cells = <0>;
        realtek,jd-mode = <2>;  /* jack detect 模式 */
    };
};

sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "rt5651-sound";
    simple-audio-card,format = "i2s";
    simple-audio-card,mclk-fs = <256>;
    simple-audio-card,widgets =
        "Speaker", "Speaker",
        "Headphone", "Headphone",
        "Microphone", "Mic";
    simple-audio-card,routing =
        "Speaker", "SPOL",
        "Speaker", "SPOR",
        "Headphone", "HPOL",
        "Headphone", "HPOR",
        "IN1P", "Mic",
        "IN1N", "Mic";
    simple-audio-card,cpu { sound-dai = <&i2s0>; };
    simple-audio-card,codec { sound-dai = <&rt5651>; };
};
```

## 3. ES8388 移植

### 3.1 基本信息
```
I2C 地址: 0x10 (ADDR pin 接地) 或 0x11 (ADDR pin 接 VCC)
供电: AVDD=3.3V, DVDD=1.8V
支持: I2S/LEFT_J/RIGHT_J, 8~96kHz
功能: 立体声 ADC+DAC, 低功耗
驱动: sound/soc/codecs/es8388.c (或 es8328.c)
CONFIG: CONFIG_SND_SOC_ES8328_I2C=y
```

### 3.2 DTS 示例
```dts
&i2c2 {
    status = "okay";
    es8388: es8388@10 {
        compatible = "everest,es8388";
        reg = <0x10>;
        clocks = <&cru SCLK_I2S_8CH_OUT>;
        clock-names = "mclk";
        #sound-dai-cells = <0>;
    };
};

sound {
    compatible = "simple-audio-card";
    simple-audio-card,name = "es8388-sound";
    simple-audio-card,format = "i2s";
    simple-audio-card,mclk-fs = <256>;
    simple-audio-card,widgets =
        "Speaker", "Speaker",
        "Headphone", "Headphones",
        "Microphone", "Mic";
    simple-audio-card,routing =
        "Speaker", "LOUT1",
        "Speaker", "ROUT1",
        "Headphones", "LOUT2",
        "Headphones", "ROUT2",
        "LINPUT1", "Mic",
        "RINPUT1", "Mic";
    simple-audio-card,cpu { sound-dai = <&i2s0>; };
    simple-audio-card,codec { sound-dai = <&es8388>; };
};
```

## 4. WM8960 移植

### 4.1 基本信息
```
I2C 地址: 0x1a
供电: AVDD=3.3V, DVDD=1.8V
支持: I2S/RIGHT_J/LEFT_J/DSP, 8~48kHz
功能: 立体声 ADC+DAC, 内置 CLASS-D 功放, 耳机驱动
驱动: sound/soc/codecs/wm8960.c
CONFIG: CONFIG_SND_SOC_WM8960=y
```

## 5. Jack 检测 (耳机检测)

```
耳机检测方式:
1. Codec 内置检测 (微电流检测插入):
   → codec 驱动中配置 JD (Jack Detect) 功能
   → DTS 中设 realtek,jd-mode 等属性
   → 中断触发 → ASoC jack event → 切换 DAPM 路由

2. GPIO 检测 (机械开关):
   → 耳机插座的机械开关连接到 GPIO
   → 在 machine driver 中使用 snd_soc_jack_add_gpios()

3. extcon (外部连接器):
   → 某些平台用 extcon 框架统一管理

调试:
cat /sys/kernel/debug/asoc/<card>/dapm_widgets | grep -i jack
# 查看 jack widget 状态
evtest /dev/input/eventX
# 查看耳机插入事件 (EV_SW, SW_HEADPHONE_INSERT)
```

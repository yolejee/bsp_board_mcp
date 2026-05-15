# 音频质量深度调试

## 1. 爆音 (Pop / Click) 详细分析

### 1.1 爆音分类
```
类型           时机              原因                     解决方案
────────────────────────────────────────────────────────────────
开机爆音       系统启动时         codec 上电切换            codec anti-pop 电路/寄存器
关机爆音       系统关闭时         codec 掉电瞬间            shutdown 前先 mute
播放开始爆音   start 时          PA 使能时序不当           PA 使能延迟 (ms 级)
播放结束爆音   stop 时           PA 关闭时序不当           先 mute 再关 PA
切换通路爆音   SPK↔HP 切换       DAPM 切换瞬间             先 mute → 切换 → unmute
音频流爆音     播放中            DMA underrun / 数据不连续  增大 buffer, 检查 CPU 负载
```

### 1.2 Anti-pop 解决方案
```
硬件层面:
1. Codec Anti-pop 电路:
   - 大部分 codec 有内置 anti-pop 电路
   - 上电时缓慢建立偏置电压, 避免直流突变
   - 检查 codec datasheet 的 pop-free 配置

2. PA 使能时序:
   - PA 功放的 ENABLE 引脚应晚于 codec 输出稳定后才使能
   - DTS 中可配置延迟:
     hp-det-gpio / spk-con-gpio 的使能延迟

软件层面:
1. DAPM 顺序控制:
   - SND_SOC_DAPM_PRE_PMU  → 上电前操作
   - SND_SOC_DAPM_POST_PMU → 上电后操作
   - SND_SOC_DAPM_PRE_PMD  → 下电前操作
   - SND_SOC_DAPM_POST_PMD → 下电后操作

2. Mute 控制:
   - 通路切换前调用 codec 的 digital mute
   - snd_soc_dai_digital_mute()
```

## 2. 底噪分析

### 2.1 底噪来源
```
底噪来源及特征:
1. 电源噪声 (Power Supply Noise):
   - 特征: 50Hz/100Hz 哼声 (工频干扰)
   - 排查: 示波器测量 AVDD/DVDD 纹波
   - 解决: 增加滤波电容, 使用低噪声 LDO

2. 地线环路 (Ground Loop):
   - 特征: 恒定低频嗡嗡声
   - 排查: 断开外部连接逐一排除
   - 解决: 单点接地, 模拟地/数字地分离

3. 数字串扰 (Digital Crosstalk):
   - 特征: 与数字信号活动相关的噪声
   - 排查: CPU 高负载时噪声增大
   - 解决: PCB 布局隔离数字/模拟区域

4. 时钟抖动 (Clock Jitter):
   - 特征: 高频噪声, 信噪比劣化
   - 排查: 示波器测 MCLK/BCLK 抖动
   - 解决: 使用低抖动时钟源, 缩短时钟走线

5. ADC/DAC 本底噪声:
   - 特征: 白噪声 (均匀分布)
   - 无法消除, 但可通过提高信号幅度改善 SNR
```

### 2.2 信噪比 (SNR) 测量
```bash
# 在 Linux 上测量底噪:
# 1. 录制静音信号:
arecord -D hw:0,0 -f S16_LE -r 48000 -c 2 -d 10 silence.wav

# 2. 使用 sox 分析:
sox silence.wav -n stats
# 关注 RMS lev dB 和 Pk lev dB

# 3. 使用 ALSA 的 aplayer 验证:
aplay -D hw:0,0 --dump-hw-params /dev/null 2>&1

# 4. 信噪比计算:
# SNR = 20 × log10(信号 RMS / 噪声 RMS)
# 一般要求: DAC > 90 dB, ADC > 80 dB
```

## 3. 失真问题

### 3.1 失真类型
```
THD (Total Harmonic Distortion) 总谐波失真:
- 原因: DAC/ADC 非线性, 功放过载
- 测量: 播放正弦波, 分析频谱中的谐波分量

削波失真 (Clipping):
- 原因: 输入/输出信号超过动态范围
- 现象: 波形顶部/底部被切平, 声音刺耳
- 解决: 降低增益, 增大动态范围

交叉失真 (Crossover Distortion):
- 原因: Class AB 功放偏置不足
- 现象: 小信号时失真明显
- 解决: 调整功放偏置点

互调失真 (IMD):
- 原因: 两个不同频率信号互相影响
- 测量: 双音信号测试
```

### 3.2 示波器测量方法
```
测量点:
1. MCLK: 频率精度, 抖动 (< 1ns peak-to-peak)
2. BCLK/LRCK: 频率, 占空比, 与 MCLK 的关系
3. I2S DATA: 数据变化应在 BCLK 下降沿
4. DAC 模拟输出: 播放正弦波看波形
5. PA 输出: 功放后的信号

测量要点:
- 使用 AC 耦合测量模拟信号
- 带宽 > 20MHz (音频足够)
- 触发源用 LRCK 同步
- 注意探头接地位置
```

## 4. DMA Underrun 处理

```bash
# 检查 xrun:
aplay -v test.wav 2>&1 | grep -i xrun
cat /proc/asound/card0/pcm0p/sub0/status
# 显示: XRUN

# 解决方案:
# 1. 增大 buffer:
aplay --buffer-size=8192 --period-size=2048 test.wav

# 2. asound.conf 全局配置:
# pcm.!default {
#     type plug
#     slave {
#         pcm "hw:0,0"
#         period_size 2048
#         buffer_size 8192
#     }
# }

# 3. 应用程序中设置:
# snd_pcm_hw_params_set_buffer_size()
# snd_pcm_hw_params_set_period_size()

# 4. 检查系统负载:
top                    # CPU 占用
cat /proc/interrupts   # 中断负载
# 如果 CPU 来不及喂数据 → 降低系统负载或提高 audio 线程优先级
```

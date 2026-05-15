# HDMI / DP / eDP 深入调试参考

## 目录

1. [HDMI 深入调试](#1-hdmi-深入调试)
2. [DisplayPort 深入调试](#2-displayport-深入调试)
3. [eDP 调试](#3-edp-调试)
4. [LVDS 配置](#4-lvds-配置)
5. [信号完整性与 PHY 配置](#5-信号完整性与-phy-配置)

---

## 1. HDMI 深入调试

### 1.1 HDMI 版本与带宽

| HDMI 版本 | 最大 TMDS 时钟 | 最大分辨率 | 带宽 |
|----------|--------------|----------|------|
| 1.4 | 340 MHz | 4K@30 | 10.2 Gbps |
| 2.0 | 600 MHz | 4K@60 | 18 Gbps |
| 2.1 (FRL) | - | 8K@60/4K@120 | 48 Gbps |

### 1.2 HDMI DTS 高级配置

```dts
&hdmi {
    status = "okay";
    // 固定输出颜色格式
    // rockchip,color-depth = <10>;       // 8/10/12 bit
    // rockchip,colorimetry = <9>;        // BT2020
    // rockchip,hdmi-output = <1>;        // 0=YCBCR444 1=YCBCR422 2=YCBCR420 3=RGB
};

// HDMI 音频
&hdmi_sound {
    status = "okay";
};
```

### 1.3 HDMI 调试命令

```bash
# Connector 详细信息
cat /sys/class/drm/card0-HDMI-A-1/status
cat /sys/class/drm/card0-HDMI-A-1/modes
cat /sys/class/drm/card0-HDMI-A-1/edid | edid-decode   # 需要 edid-decode 工具

# VOP 显示状态
cat /sys/kernel/debug/dri/0/summary

# HDMI 时钟
cat /sys/kernel/debug/clk/clk_summary | grep -i hdmi

# HPD 状态监控
echo 1 > /sys/kernel/debug/tracing/events/drm/drm_vblank_event/enable

# 强制分辨率 (测试用)
# 在 kernel cmdline 中:
# video=HDMI-A-1:1920x1080@60
```

### 1.4 EDID 问题

```bash
# HDMI 无法读取 EDID:
# → DDC (I2C) 通信失败
# → 检查 HDMI 线缆
# → 部分 HDMI 转 VGA 不支持 DDC

# 读取到的分辨率不对:
# → EDID 中的首选模式可能不是期望的
# → 可通过 baseparameter 强制指定分辨率

# 自定义 EDID (绕过异常 EDID):
# CONFIG_DRM_LOAD_EDID_FIRMWARE=y
# video=HDMI-A-1:e edid/custom.bin
```

### 1.5 HDCP 配置

```bash
# 内核配置
CONFIG_ROCKCHIP_HDMI_HDCP=y

# 需要在 OTP 或 eMMC 中烧录 HDCP key
# RK 提供 HDCP key 写入工具

# 验证
cat /sys/class/drm/card0-HDMI-A-1/content_protection
# Enabled / Desired / Undesired
```

### 1.6 CEC 配置

```bash
# 内核配置
CONFIG_ROCKCHIP_HDMI_CEC=y
CONFIG_CEC_CORE=y
CONFIG_CEC_NOTIFIER=y

# 使用 cec-utils 工具
apt install cec-utils
cec-ctl --list-devices
cec-ctl --playback         # 设置为播放设备
cec-ctl --tv               # 设置为 TV
```

---

## 2. DisplayPort 深入调试

### 2.1 DP 链路训练 (Link Training)

```
Link Training 过程:
1. Clock Recovery (CR) → 调整 voltage swing 和 pre-emphasis
2. Channel Equalization (EQ) → 调整均衡参数
3. Symbol Lock → 信号锁定

dmesg 中观察:
"Link training passed at link rate = 5400, lane count = 4"
→ 5.4 Gbps × 4 lanes = 21.6 Gbps

如果 Link Training 失败:
"Link training failed"
→ 降低 link rate 或 lane count 重试
→ 检查 PHY, 线缆, 接口
```

### 2.2 DP 带宽计算

```
DP 带宽 = link_rate × lanes × 8/10 (8b/10b编码)

DP 1.2: 5.4 Gbps × 4 = 21.6 Gbps → 支持 4K@60 RGB888
DP 1.4: 8.1 Gbps × 4 = 32.4 Gbps → 支持 4K@120 / 8K@30
         (使用 128b/132b: 8.1 × 4 × 128/132 = 31.4 Gbps)

像素带宽需求 = pixel_clock × bpp
4K@60 RGB888 = 594 MHz × 24 = 14.26 Gbps
4K@120 RGB888 = 1188 MHz × 24 = 28.5 Gbps
```

### 2.3 Type-C Alt Mode 调试

```bash
# 查看 Type-C 状态
cat /sys/class/typec/port0/data_role
cat /sys/class/typec/port0/power_role

# DP Alt Mode 需要:
# 1. Type-C PHY 支持 DP Alt Mode
# 2. CC 控制器 (fusb302/TCPM) 协商
# 3. mux 切换到 DP 模式

dmesg | grep -i "typec\|tcpm\|fusb\|alt mode\|dp alt"
```

### 2.4 DP connector-split mode (RK3588)

```dts
// 将一个 4-lane DP 拆分为两个 2-lane 输出
// 用于双屏 DP 显示
// 参考 RK3588 DP 文档
```

---

## 3. eDP 调试

### 3.1 eDP vs DP 区别

| 特性 | eDP | DP |
|------|-----|-----|
| 用途 | 内置面板 (笔记本/平板) | 外接显示器 |
| 连接器 | FPC/直焊 | 标准 DP/Type-C |
| HPD | 通常无 (always connected) | 有 |
| 供电 | 主板供电 | 自供电 |
| 背光 | 需要配置 | 不需要 |

### 3.2 eDP 调试

```bash
# eDP panel 通常是 non-removable
# 不需要 HPD 检测

# 检查 eDP link 状态
cat /sys/kernel/debug/dri/0/summary
dmesg | grep -i edp

# 常见问题:
# AUX CH 通信失败 → 确认 eDP PHY 时钟
# 屏幕闪烁 → 检查 backlight PWM 频率, eDP link 不稳定
# 亮度不可调 → 检查 backlight 节点和 PWM 配置
```

---

## 4. LVDS 配置

### 4.1 LVDS DTS

```dts
&lvds {
    status = "okay";

    ports {
        port@1 {
            reg = <1>;
            lvds_out_panel: endpoint {
                remote-endpoint = <&panel_in_lvds>;
            };
        };
    };
};

&lvds_in_vp2 {
    status = "okay";
};

&route_lvds {
    status = "okay";
    connect = <&vp2_out_lvds>;
};

// LVDS panel
lvds_panel: panel {
    compatible = "simple-panel";
    backlight = <&backlight>;
    power-supply = <&vcc_3v3>;
    // ... timing 参数
};
```

### 4.2 LVDS 调试

```bash
# LVDS 信号无输出:
# → 检查 status, pinctrl, clock
# → 确认 VP 与 LVDS 的连接 (不是所有 VP 都支持 LVDS)

# LVDS 花屏:
# → 检查 data-mapping (jeida vs vesa)
# → 检查 bus-format (18bit vs 24bit)
# → 检查线序
```

---

## 5. 信号完整性与 PHY 配置

### 5.1 HDMI PHY 信号强度

```dts
// 部分平台支持 phy-table 调整信号强度
&hdmi {
    rockchip,phy-table =
        <74250000   0x8009 0x0004 0x0272>,    // 720p
        <165000000  0x802b 0x0004 0x028d>,    // 1080p
        <297000000  0x8039 0x0005 0x028d>,    // 4K@30
        <594000000  0x8039 0x0000 0x019d>;    // 4K@60
    // 列: pixel_clock, reg1, reg2, reg3
    // 具体值需要根据测试调整
};
```

### 5.2 DSI PHY 调试

```bash
# DSI 信号质量问题排查:
# 1. 检查 DSI 走线长度 (建议 < 15cm)
# 2. 检查差分阻抗 (100Ω ±10%)
# 3. 检查电源去耦
# 4. 降低 lane-rate 测试
```

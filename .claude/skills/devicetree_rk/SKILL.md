---
name: devicetree_rk
description: "Rockchip 瑞芯微平台设备树 (Device Tree) 专用技能。针对 RK3566/RK3568/RK3588/RK3399/PX30/RK3308/RK3328 等瑞芯微 SoC 的 DTS 编写、关系梳理和问题排查。触发关键词包括但不限于：RK3566、RK3568、RK3588、RK3399、PX30、Rockchip、瑞芯微、LubanCat、鲁班猫、野火、rk809、rk817、VOP2、VP0、VP1、Combo PHY、combphy、MULTI_PHY、gmac1m0、gmac1m1、route_hdmi、route_dsi0、video_phy0、fiq-debugger 等。当用户明确提到 Rockchip 芯片型号、板卡名称 (如 LubanCat、Rock-3A、EVB)、或 Rockchip 特有的 DTS 属性 (如 rockchip,phy-table、rockchip,camera-module-*)时，优先使用本技能而非通用 devicetree_common。本技能包含 RK 平台的 PMIC 配置、显示通路 (VOP2 VP0/VP1 选择)、Combo PHY 复用、pinctrl mux 组、GPIO 编号体系等平台特化知识。"
---

# Rockchip 瑞芯微平台设备树技能

## 快速导航

```
你需要做什么？
 编写 RK 新板卡 DTS         第 2 节
 配置显示输出 (HDMI/DSI)    第 2.3 节 + references/display-subsystem.md
 排查外设不工作             第 4 节 (诊断清单)
 分析 DTS include 层级      第 3 节
 查找 RK 外设节点模板       references/peripheral-bindings.md
 深度排查案例                references/troubleshooting-guide.md
```

---

## 1. RK 平台基础

### 1.1 编译命令

```bash
# 内核树编译
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs

# 编译单个 DTS
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- rockchip/rk3566-lubancat-1-hdmi.dtb

# 反编译 (调试)
dtc -I dtb -O dts -o output.dts input.dtb
```

### 1.2 GPIO 编号体系

Rockchip GPIO 使用 `GPIOx_Yy` 格式，DTS 中通过宏表示：

| 宏 | 引脚 | 数值 |
|----|------|------|
| `RK_PA0` ~ `RK_PA7` | Px_A0 ~ Px_A7 | 0 ~ 7 |
| `RK_PB0` ~ `RK_PB7` | Px_B0 ~ Px_B7 | 8 ~ 15 |
| `RK_PC0` ~ `RK_PC7` | Px_C0 ~ Px_C7 | 16 ~ 23 |
| `RK_PD0` ~ `RK_PD7` | Px_D0 ~ Px_D7 | 24 ~ 31 |

**用法**：`<&gpio0 RK_PC5 GPIO_ACTIVE_LOW>` = GPIO0_C5, 低电平有效

**Linux GPIO 编号**：`bank  32 + offset`，如 GPIO0_C5 = 032 + 21 = **21**

### 1.3 pinctrl mux 组 (m0/m1/m2)

RK3566/RK3568 很多外设有多个 mux 组，对应不同物理引脚：

```dts
// 选择 mux 组取决于 PCB 走线
&uart3 { pinctrl-0 = <&uart3m0_xfer>; };   // mux 0
&uart3 { pinctrl-0 = <&uart3m1_xfer>; };   // mux 1
```

 两个外设不能使用同一组引脚。mux 组选错是外设不工作的头号原因。

### 1.4 Combo PHY 复用

RK3566 有两个 Combo PHY，每个只能配置为一种功能（**互斥**）：

| Combo PHY | 可选功能 | DTS 节点 |
|-----------|---------|----------|
| combphy1_usq | USB 3.0 HOST **或** SATA1 | `&usbhost30` / `&sata1` |
| combphy2_psq | PCIe 2.0 **或** SATA2 | `&pcie2x1` / `&sata2` |

 同一 Combo PHY 上的功能互斥。例如启用 `&pcie2x1` 就不能启用 `&sata2`。

---

## 2. DTS 编写

### 2.1 RK 设备树层级

```
rk3568.dtsi                        SoC 级 (所有 IP 块, status="disabled")
  rk3566.dtsi                    SoC 变体 (/delete-node/ 不支持的 IP)
      board-core.dtsi            核心板 (PMIC rk809/rk817, CPU 调压, eMMC)
          board-io.dtsi          底板 (LED, USB, ETH, Camera, Audio)
              board-display.dts  顶层 (model, compatible, 显示输出选择)
```

编写步骤：
1. **选 SoC dtsi**  rk3566.dtsi / rk3568.dtsi / rk3588s.dtsi
2. **配 PMIC**  rk809/rk817 的 I2C 地址、中断、regulator 输出
3. **配底板**  启用外设 (`status = "okay"`)、填入 pinctrl mux 组
4. **选显示**  HDMI / MIPI DSI / eDP 通路 (见 2.3 节)

### 2.2 外设节点模板

RK 平台常用外设 (GPIO LED、Regulator、I2C、SPI、UART、GMAC、MIPI DSI、HDMI、CSI 摄像头、PWM、PCIe、USB) 的完整 DTS 模板：

> ** `references/peripheral-bindings.md`**

关键 RK 特有点：
- GPIO 用 `RK_Pxy` 宏而非数字
- GMAC 需配置 `assigned-clocks` + `tx_delay`/`rx_delay` + drive level 后缀
- MIPI DSI 需配合 `video_phy0` 和 VOP route
- HDMI 需 `rockchip,phy-table` 配置
- CSI 摄像头需 `rockchip,camera-module-*` 属性

### 2.3 显示通路选择 (VOP2)

RK3566/RK3568 有两个 Video Port (VP0/VP1)。**同一 VP 不能同时连接两个显示输出。**

| 配置 | VP0 | VP1 | DTS 关键配置 |
|------|-----|-----|-------------|
| HDMI 单屏 | HDMI |  | `&hdmi_in_vp0 { status = "okay"; };` |
| MIPI 单屏 | DSI0 |  | `&dsi0_in_vp0 { status = "okay"; };` `&video_phy0 { status = "okay"; };` |
| HDMI + MIPI 双屏 | HDMI | DSI0 | `&hdmi_in_vp0 { status = "okay"; };` `&dsi0_in_vp1 { status = "okay"; };` |

route 配置模板：

```dts
// HDMI 单屏
&hdmi_in_vp0 { status = "okay"; };
&hdmi_in_vp1 { status = "disabled"; };
&route_hdmi { status = "okay"; connect = <&vp0_out_hdmi>; };

// MIPI DSI0 单屏
&dsi0_in_vp0 { status = "okay"; };
&dsi0_in_vp1 { status = "disabled"; };
&route_dsi0 { status = "okay"; connect = <&vp0_out_dsi0>; };
&video_phy0 { status = "okay"; };

// HDMI + MIPI 双屏
&hdmi_in_vp0 { status = "okay"; };
&dsi0_in_vp0 { status = "disabled"; };
&dsi0_in_vp1 { status = "okay"; };
```

> 详细显示子系统配置：** `references/display-subsystem.md`**

### 2.4 PMIC (rk809/rk817) 要点

```dts
&i2c0 {
    rk809: pmic@20 {
        compatible = "rockchip,rk809";
        reg = <0x20>;
        interrupt-parent = <&gpio0>;
        interrupts = <3 IRQ_TYPE_LEVEL_LOW>;
        rockchip,system-power-controller;
        wakeup-source;

        regulators {
            vdd_logic: DCDC_REG1 { /* 0.5V~1.35V logic 供电 */ };
            vdd_gpu: DCDC_REG2 { /* GPU 供电 */ };
            vcc_ddr: DCDC_REG3 { /* DDR 供电, always-on */ };
            vdd_npu: DCDC_REG4 { /* NPU 供电 */ };
            // LDO_REG1 ~ LDO_REG9 ...
        };
    };
};
```

 PMIC 配置错误会导致系统无法启动。I2C 地址、中断引脚必须与原理图一致。

### 2.5 Overlay (设备树插件)

```dts
/dts-v1/;
/plugin/;

#include <dt-bindings/gpio/gpio.h>
#include <dt-bindings/pinctrl/rockchip.h>

/ {
    compatible = "rockchip,rk3568";

    fragment@0 {
        target = <&uart3>;
        __overlay__ {
            status = "okay";
            pinctrl-0 = <&uart3m1_xfer>;
        };
    };
};
```

---

## 2.6 常用外设 DTS 快速参考

> 完整模板见 `references/peripheral-bindings.md`

#### USB 配置 (RK3568)

```dts
/* USB 2.0 Host */
&usb2phy0 { status = "okay"; };
&u2phy0_host { status = "okay"; };
&usb_host0_ehci { status = "okay"; };
&usb_host0_ohci { status = "okay"; };

/* USB 2.0 OTG */
&u2phy0_otg { status = "okay"; };
&usbdrd_dwc3 { dr_mode = "otg"; };

/* USB 3.0 Host (需 Combo PHY, 与 SATA1 互斥) */
&combphy1_usq { status = "okay"; };
&usbhost30 { status = "okay"; };
```

#### PCIe 配置 (RK3568)

```dts
/* PCIe 2.0 x1 (需 Combo PHY, 与 SATA2 互斥) */
&combphy2_psq { status = "okay"; };
&pcie2x1 {
    status = "okay";
    reset-gpios = <&gpio0 RK_PB6 GPIO_ACTIVE_HIGH>;
    vpcie3v3-supply = <&vcc3v3_pcie>;
    pinctrl-names = "default";
    pinctrl-0 = <&pcie20m2_pins>;
};

/* PCIe 3.0 x2 (RK3568 独有, RK3566 无) */
&pcie30phy { status = "okay"; };
&pcie3x2 {
    status = "okay";
    reset-gpios = <&gpio2 RK_PD6 GPIO_ACTIVE_HIGH>;
    vpcie3v3-supply = <&vcc3v3_pcie>;
};
```

#### GMAC 千兆网 (RK3568)

```dts
&gmac1 {
    status = "okay";
    phy-mode = "rgmii";
    assigned-clocks = <&cru SCLK_GMAC1_RX_TX>, <&cru SCLK_GMAC1>;
    assigned-clock-parents = <&cru SCLK_GMAC1_RGMII_SPEED>;
    assigned-clock-rates = <0>, <125000000>;
    clock_in_out = "output";
    snps,reset-gpio = <&gpio2 RK_PD1 GPIO_ACTIVE_LOW>;
    snps,reset-delays-us = <0 20000 100000>;
    snps,reset-active-low;
    tx_delay = <0x4f>;     /* 需根据 PCB 调试 */
    rx_delay = <0x26>;     /* 需根据 PCB 调试 */
    pinctrl-names = "default";
    pinctrl-0 = <&gmac1m1_miim &gmac1m1_tx_bus2 &gmac1m1_rx_bus2
                 &gmac1m1_rgmii_clk &gmac1m1_rgmii_bus>;
    phy-handle = <&rgmii_phy1>;
};
&mdio1 {
    rgmii_phy1: phy@0 {
        compatible = "ethernet-phy-ieee802.3-c22";
        reg = <0x0>;
    };
};
```

⚠ `gmac1m0` vs `gmac1m1` 取决于 PCB 走线。`tx_delay`/`rx_delay` 必须实测调整。

#### Audio (I2S + ES8388 Codec)

```dts
&i2s1_8ch {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&i2s1m0_sclktx &i2s1m0_lrcktx &i2s1m0_sdi0 &i2s1m0_sdo0>;
    rockchip,clk-trcm = <1>;  /* 0=TX/RX独立, 1=TX->RX, 2=RX->TX */
};
&i2c1 {
    es8388: es8388@10 {
        compatible = "everest,es8388";
        reg = <0x10>;
        #sound-dai-cells = <0>;
        clocks = <&cru I2S1_MCLKOUT>;
        clock-names = "mclk";
    };
};
/ {
    es8388_sound: es8388-sound {
        compatible = "rockchip,multicodecs-card";
        rockchip,card-name = "rockchip-es8388";
        rockchip,codec = <&es8388>;
        rockchip,cpu = <&i2s1_8ch>;
        io-channels = <&saradc 4>;  /* HP detect ADC */
    };
};
```

#### eMMC / SD 卡

```dts
/* eMMC */
&sdhci {
    status = "okay";
    bus-width = <8>;
    max-frequency = <200000000>;
    non-removable;
    mmc-hs200-1_8v;
    vmmc-supply = <&vcc_3v3>;
    vqmmc-supply = <&vcc_1v8>;
};
/* SD 卡 */
&sdmmc0 {
    status = "okay";
    bus-width = <4>;
    cap-sd-highspeed;
    sd-uhs-sdr104;
    vmmc-supply = <&vcc3v3_sd>;
    vqmmc-supply = <&vccio_sd>;
    pinctrl-names = "default";
    pinctrl-0 = <&sdmmc0_bus4 &sdmmc0_clk &sdmmc0_cmd &sdmmc0_det>;
};
```

#### SATA (需 Combo PHY, 与 USB3/PCIe 互斥)

```dts
&combphy1_usq { status = "okay"; };  /* 或 combphy2_psq */
&sata1 {  /* 或 sata2 */
    status = "okay";
};
```

---

## 3. DTS 关系梳理

### 3.1 RK DTS 层级惯例

```
rk3566-lubancat-1-hdmi.dts (顶层)
 rk3566-lubancat-1.dtsi            // 板级 (LED, USB, Audio, Camera, 电源)
    <dt-bindings/gpio/gpio.h>
    <dt-bindings/pinctrl/rockchip.h>
    <dt-bindings/clock/rk3568-cru.h>
    rk3566.dtsi                   // SoC 变体
       rk3568.dtsi              // SoC 基础 (CPU, GIC, 所有外设骨架)
    rk3568-lubancat-csi2.dtsi    // 摄像头通路
 rk3566-android.dtsi               // OS 特有 (chosen, fiq-debugger)
 rk3566-lubancat-hdmi.dtsi         // HDMI 显示通路及音频
```

### 3.2 节点覆盖规则

```
SoC dtsi:   &uart2 { status = "disabled"; clock-frequency = <24000000>; };
板级 dtsi:  &uart2 { status = "okay"; };
最终结果:   &uart2 { status = "okay"; clock-frequency = <24000000>; };
```

- 同名属性：后者覆盖前者
- 不同属性：合并保留
- 子节点：递归合并
- `/delete-node/ &label;`  删除节点
- `/delete-property/ prop-name;`  删除属性

### 3.3 phandle 引用追踪

| 引用类型 | 属性名 | RK 示例 |
|----------|--------|---------|
| 时钟 | `clocks`, `assigned-clocks` | `<&cru SCLK_GMAC1>` |
| 电源 | `*-supply` | `<&vcc3v3_sys>` |
| GPIO | `*-gpios` | `<&gpio0 RK_PC5 GPIO_ACTIVE_LOW>` |
| 复位 | `resets` | `<&cru SRST_I2C1>` |
| pinctrl | `pinctrl-0` | `<&uart3m1_xfer>` |
| PHY | `phys` | `<&u2phy0_otg>` |
| 电源域 | `power-domains` | `<&power RK3568_PD_PIPE>` |
| 显示端点 | `remote-endpoint` | `<&dsi_out_panel>` |

---

## 4. 问题排查

### 4.1 运行时调试

```bash
cat /proc/device-tree/model                                # 板卡名
dtc -I fs -O dts -o running.dts /proc/device-tree/         # 反编译当前 DT
cat /sys/kernel/debug/gpio                                 # GPIO 状态
cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins  # pinctrl
cat /sys/kernel/debug/clk/clk_summary                      # 时钟树
cat /sys/kernel/debug/regulator/regulator_summary           # 电源
i2cdetect -y -r 1                                          # I2C 扫描
dmesg | grep -i "probe\|error\|fail"                       # 内核日志
```

### 4.2 诊断清单

#### 屏幕不亮 (MIPI DSI)

| # | 检查项 | 命令/方法 | 期望 |
|---|--------|----------|------|
| 1 | DSI 控制器 | `xxd /proc/device-tree/soc/dsi@*/status` | `okay` |
| 2 | video_phy | 检查 `&video_phy0` status | `okay` |
| 3 | VP 通路 | `dsi0_in_vp0` 或 `dsi0_in_vp1` | 仅一个 `okay` |
| 4 | route | `&route_dsi0` connect 指向正确 VP |  |
| 5 | 背光 | `cat /sys/class/backlight/*/brightness` | 非零 |
| 6 | 面板电源 | `regulator_summary` | 已启用 |
| 7 | reset-gpios | GPIO 引脚号和极性 | 与原理图一致 |
| 8 | init-sequence | panel-init-sequence | 与屏厂 datasheet 一致 |

#### 触摸失效

| # | 检查项 | 命令 | 期望 |
|---|--------|------|------|
| 1 | I2C 扫描 | `i2cdetect -y -r 1` | 看到 0x5d (GT911) |
| 2 | I2C 控制器 | `&i2c1 { status }` | `okay` |
| 3 | 中断配置 | `interrupt-parent` + `interrupts` | GPIO bank/pin 正确 |
| 4 | reset-gpios | GPIO 和极性 |  |

#### 网络不通 (GMAC)

| # | 检查项 | 关注 |
|---|--------|------|
| 1 | GMAC status | `"okay"` |
| 2 | phy-mode | `"rgmii"` / `"rmii"` |
| 3 | tx_delay / rx_delay | 需根据 PCB 调试 |
| 4 | PHY reset GPIO | `snps,reset-gpio` 正确 |
| 5 | PHY MDIO 地址 | `reg = <0x0>` 或 `<0x1>` |
| 6 | clock 配置 | 125MHz (RGMII) |
| 7 | pinctrl mux | `gmac1m0` vs `gmac1m1` 与走线匹配 |
| 8 | drive level | `_level2` / `_level3` 与 PCB 阻抗匹配 |

#### USB 不识别

| # | 检查项 | 关注 |
|---|--------|------|
| 1 | USB PHY | `usb2phy0`/`usb2phy1`  `okay` |
| 2 | PHY 子节点 | `u2phy0_host`/`u2phy0_otg`  `okay` |
| 3 | EHCI/OHCI | `usb_host0_ehci`/`ohci`  `okay` |
| 4 | Combo PHY | `combphy1_usq` (USB3)  `okay` |
| 5 | 电源 | `vcc5v0_usb*` regulator |
| 6 | Combo PHY 复用 | SATA/USB3/PCIe 不能同时用同一 PHY |

#### 启动挂死

| # | 检查项 | 关注 |
|---|--------|------|
| 1 | PMIC | i2c 地址和中断与原理图一致 |
| 2 | CPU 调压器 | `vdd_cpu` 电压范围正确 |
| 3 | DDR 时序 | `dram-default-timing.dtsi` 匹配 DDR 型号 |
| 4 | chosen/bootargs | console= 波特率和 UART 编号正确 |

### 4.3 常见 DTS 错误

| 错误 | 修复 |
|------|------|
| `status = "ok"` | 改为 `"okay"` |
| 同一 mux 组 pinctrl 冲突 | 同组引脚只能被一个外设使用 |
| GPIO 极性反 | `GPIO_ACTIVE_HIGH` ↔ `GPIO_ACTIVE_LOW` |
| interrupt-parent 指错 | 确认指向正确 GPIO bank |
| Overlay 缺 `/plugin/;` | 在 `/dts-v1/;` 后添加 |
| I2C 地址用了 8 位 | DT 中用 7 位 (右移 1 位) |

⚠ 同一 mux 组的引脚只能分配给一个外设，pinctrl 冲突是 RK 平台最常见的 DTS 错误。

### 4.4 LubanCat 板卡设备树映射

| DTS 文件 | 板卡 | 显示 |
|----------|------|------|
| `rk3566-lubancat-1-hdmi.dts` | LubanCat-1 | HDMI |
| `rk3566-lubancat-1-mipi600p.dts` | LubanCat-1 | 7寸 MIPI (1024600) |
| `rk3566-lubancat-1-mipi800p.dts` | LubanCat-1 | 10.1寸 MIPI (8001280) |
| `rk3566-lubancat-1-mipi1080p.dts` | LubanCat-1 | 5.5寸 MIPI (10801920) |

切换显示：顶层 DTS 通过 `#include` 选择不同的 display dtsi。

---

## 5. 参考资料

### 在线资源
- **设备树规范**: https://devicetree-specification.readthedocs.io/
- **Rockchip 开发者文档**: https://opensource.rock-chips.com/

### 本地参考文件

| 文件 | 内容 | 何时读取 |
|------|------|---------|
| `references/display-subsystem.md` | VOP2、HDMI、DSI、eDP 显示子系统详细配置 | 显示通路问题时 |
| `references/peripheral-bindings.md` | RK 常见外设 DTS 绑定属性完整参考 | 编写外设节点时 |
| `references/troubleshooting-guide.md` | 扩展故障排查案例集 (MIPI 不亮、网络不通等) | 深度排查时 |

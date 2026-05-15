---
name: devicetree_common
description: "通用嵌入式 Linux 设备树 (Device Tree) 技能，不限于任何特定 SoC 平台。用于编写、生成、分析、梳理和诊断 .dts / .dtsi / .dtso (overlay) 文件。触发关键词包括但不限于：设备树、device tree、dts、dtsi、dtb、dtbo、overlay、设备树插件、绑定 (binding)、compatible、pinctrl、regulator、display-timings、MIPI DSI、HDMI、I2C、SPI、UART、GPIO、PCIe、USB、GMAC、摄像头 CSI、RTC、PWM、LED、eMMC、SDMMC、电源管理 PMIC、时钟树 (clock tree)、中断控制器、DMA 等。适用于所有使用 Device Tree 的平台：Rockchip、全志 (Allwinner)、NXP i.MX、TI (AM335x/AM62x/Sitara)、Qualcomm、Broadcom、MediaTek、Samsung Exynos、STM32MP、Microchip/Atmel、Xilinx/AMD Zynq、RISC-V (StarFive/SiFive/T-Head) 等。当用户讨论任何嵌入式 Linux 硬件配置、外设驱动适配、DTS 语法、设备树层级分析、或外设不工作的问题时，即使没有明确说 '设备树'，只要问题可能与 DTS 配置相关，都应触发本技能。如果用户明确提到 Rockchip/RK 芯片型号，应优先使用 devicetree_rk 技能。"
---

# 通用嵌入式 Linux 设备树 (Device Tree) 技能

## 快速导航

根据你的任务类型选择入口：

```
你需要做什么？
 编写新设备树         第 2 节 + references/peripheral-templates.md
 分析 DTS 层级关系    第 3 节
 排查外设不工作       第 4 节 (诊断流程)
 理解 DTS 语法细节    第 1 节 + references/dt-syntax-reference.md
 编写 Overlay 插件    references/overlay-guide.md
 pinctrl 跨平台对比   references/multi-platform-pinctrl.md
 查找外设节点模板     references/peripheral-templates.md
```

---

## 1. 设备树基础

### 1.1 文件类型与编译

| 后缀 | 角色 | 说明 |
|------|------|------|
| `.dts` | 顶层源文件 | 对应一块具体板卡，编译为 `.dtb` |
| `.dtsi` | 可复用包含文件 | 被 `#include` 引入，可多级嵌套 |
| `.dtso` | 设备树插件 (overlay) | 运行时叠加修改，编译为 `.dtbo` |
| `.dtb` / `.dtbo` | 编译后二进制 | 被 bootloader 加载 |

```bash
# 内核树编译 (推荐，自动解析头文件)
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs

# 独立编译
dtc -I dts -O dtb -o output.dtb input.dts

# 反编译 (调试用)
dtc -I dtb -O dts -o output.dts input.dtb

# 编译 Overlay (-@ 生成 __symbols__)
dtc -@ -I dts -O dtb -o overlay.dtbo overlay.dts

# 合并 overlay
fdtoverlay -i base.dtb overlay.dtbo -o merged.dtb
```

### 1.2 DTS 最小骨架

```dts
/dts-v1/;

#include <dt-bindings/gpio/gpio.h>
#include "soc.dtsi"

/ {
    model = "Vendor Board-Name";
    compatible = "vendor,board-name", "vendor,soc";

    aliases {
        serial0 = &uart0;
    };

    chosen {
        stdout-path = "serial0:115200n8";
    };
};

// 启用外设
&uart0 { status = "okay"; };
```

### 1.3 关键属性速查

| 属性 | 含义 | 值类型 | 示例 |
|------|------|--------|------|
| `compatible` | 驱动匹配标识 (最重要) | string-list | `"ti,am335x-uart"` |
| `reg` | 寄存器/I2C 地址 | prop-encoded-array | `<0x0 0x44e09000 0x0 0x1000>` |
| `status` | 节点启用状态 | string | `"okay"` / `"disabled"` |
| `interrupts` | 中断描述 | prop-encoded-array | `<GIC_SPI 72 IRQ_TYPE_LEVEL_HIGH>` |
| `clocks` / `clock-names` | 时钟引用 | phandle + specifier | `<&clk UART0_CLK>` |
| `resets` | 复位信号 | phandle + specifier | `<&cru SRST_UART0>` |
| `pinctrl-names` / `pinctrl-0` | 引脚复用 | string / phandle-list | `"default"` / `<&uart0_pins>` |
| `*-supply` | 电源引用 | phandle | `<&reg_3v3>` |
| `*-gpios` | GPIO 引脚 | phandle + specifier | `<&gpio0 5 GPIO_ACTIVE_HIGH>` |
| `power-domains` | 电源域 | phandle + specifier | `<&pd_peri>` |
| `#address-cells` / `#size-cells` | 子节点寻址格式 | u32 | `<2>` / `<1>` |

⚠ `status` 必须写 `"okay"` 而非 `"ok"`，否则节点不会被启用。

### 1.4 数据类型

| 类型 | 语法 | 示例 |
|------|------|------|
| 空值 (boolean) | `prop-name;` | `regulator-always-on;` |
| u32 | `<value>` | `clock-frequency = <24000000>;` |
| string | `"text"` | `status = "okay";` |
| string-list | `"a", "b"` | `compatible = "ti,omap-uart", "ns16550a";` |
| bytestring | `[xx yy]` | `mac-address = [00 11 22 33 44 55];` |
| phandle | `<&label>` | `clocks = <&osc24m>;` |

> 完整语法参考：`references/dt-syntax-reference.md`

---

## 2. 设备树编写

### 2.1 分层设计

设备树遵循 **SoC  Board  Variant** 分层架构：

```
soc.dtsi                  SoC 级 (芯片厂提供，所有外设 status="disabled")
 soc-variant.dtsi      SoC 变体 (裁剪型号)
 board-common.dtsi     核心板 (PMIC, DDR, eMMC, CPU 调压)
 board-io.dtsi         底板 I/O (LED, USB, ETH, Key)
 board-display.dtsi    显示子系统 (HDMI / DSI / eDP)
 board-variant.dts     最终 DTS (选择特性，编译入口)
```

编写步骤：
1. 选择正确的 SoC dtsi 作为基础
2. 编写核心板 dtsi (PMIC、CPU 调压器、DDR、eMMC)
3. 编写底板 dtsi (LED、USB、网口、摄像头、音频)
4. 编写顶层 dts (设置 model/compatible，选择显示输出)

### 2.2 `#address-cells` 和 `#size-cells` 规则

这两个属性定义**子节点的 `reg` 属性格式**，是写设备树最容易出错的地方：

| 父节点类型 | `#address-cells` | `#size-cells` | 子节点 `reg` 格式 | 示例 |
|-----------|------------------|---------------|------------------|------|
| 根节点 `/` | 2 | 2 | `<addr_hi addr_lo size_hi size_lo>` | `<0x0 0x10000000 0x0 0x1000>` |
| 内存映射总线 | 2 | 1 | `<addr_hi addr_lo size>` | `<0x0 0xfe5a0000 0x1000>` |
| I2C 控制器 | 1 | 0 | `<device_addr>` (7位) | `<0x50>` |
| SPI 控制器 | 1 | 0 | `<chip_select>` | `<0>` |
| GPIO 控制器 | `#gpio-cells` 一般 2 | — | `<bank offset flags>` | `<5 GPIO_ACTIVE_HIGH>` |
| 中断控制器 | — | — | 由 `#interrupt-cells` 定义 | `<GIC_SPI 42 IRQ_TYPE_LEVEL_HIGH>` |

⚠ `reg` 的值数量 = `#address-cells` + `#size-cells`。不匹配会导致 dtc 警告或驱动解析错误。

### 2.3 I2C 设备节点

```dts
&i2c1 {
    status = "okay";
    clock-frequency = <400000>;    // 400kHz Fast Mode (100000=标准, 1000000=FM+, 3400000=HS)
    // pinctrl-names = "default";  // 通常 SoC dtsi 已配好, 板卡若需改 mux 才加
    // pinctrl-0 = <&i2c1_pins>;

    /* 温度传感器 (7 位地址 0x48) */
    tmp102@48 {
        compatible = "ti,tmp102";
        reg = <0x48>;                    // ⚠ 必须 7 位地址
        #thermal-sensor-cells = <0>;
    };

    /* EEPROM */
    eeprom@50 {
        compatible = "atmel,24c256";
        reg = <0x50>;
        pagesize = <64>;
    };

    /* RTC */
    rtc@51 {
        compatible = "nxp,pcf8563";
        reg = <0x51>;
        interrupt-parent = <&gpio0>;
        interrupts = <5 IRQ_TYPE_EDGE_FALLING>;
    };
};
```

### 2.4 SPI 设备节点

```dts
&spi0 {
    status = "okay";
    // pinctrl-names = "default";  // 同 I2C, 通常 SoC dtsi 已有
    // pinctrl-0 = <&spi0_pins>;

    /* SPI NOR Flash */
    flash@0 {
        compatible = "jedec,spi-nor";
        reg = <0>;                      // chip-select 编号
        spi-max-frequency = <50000000>; // 50MHz
        m25p,fast-read;
        #address-cells = <1>;
        #size-cells = <1>;

        partitions {
            compatible = "fixed-partitions";
            #address-cells = <1>;
            #size-cells = <1>;

            partition@0 {
                label = "bootloader";
                reg = <0x0 0x100000>;
            };
            partition@100000 {
                label = "data";
                reg = <0x100000 0x300000>;
            };
        };
    };

    /* SPI 设备 (片选 1) */
    adc@1 {
        compatible = "ti,ads7846";
        reg = <1>;
        spi-max-frequency = <1000000>;
        interrupt-parent = <&gpio1>;
        interrupts = <12 IRQ_TYPE_EDGE_FALLING>;
    };
};
```

### 2.5 UART 节点

```dts
&uart2 {
    status = "okay";
    // pinctrl-names = "default";
    // pinctrl-0 = <&uart2_pins>;
};

// UART 用作蓝牙 HCI
&uart1 {
    status = "okay";

    bluetooth {
        compatible = "brcm,bcm43438-bt";
        max-speed = <3000000>;
        shutdown-gpios = <&gpio2 4 GPIO_ACTIVE_HIGH>;
        device-wakeup-gpios = <&gpio2 5 GPIO_ACTIVE_HIGH>;
    };
};
```

### 2.6 外设节点模板

所有常见外设 (LED、I2C、SPI、UART、Ethernet、eMMC、SD、PWM、USB、PCIe、MIPI DSI、HDMI、音频等) 的完整 DTS 模板参见：

> ** `references/peripheral-templates.md`**

### 2.3 Overlay (设备树插件)

Overlay 允许运行时动态修改设备树，无需重编译 base DTB。详细指南：

> ** `references/overlay-guide.md`**

关键要点：
- 文件开头必须有 `/dts-v1/;` 和 `/plugin/;`
- 编译时 base DTB 和 overlay 都需要 `-@` 参数
- fragment 的 target 必须引用 base DTB 中存在的 label

### 2.4 pinctrl 配置

各平台 pinctrl binding 差异很大。跨平台对比参见：

> ** `references/multi-platform-pinctrl.md`**

通用概念：
```dts
&uart0 {
    pinctrl-names = "default", "sleep";   // 状态名
    pinctrl-0 = <&uart0_default_pins>;    // default 状态的 pin 配置
    pinctrl-1 = <&uart0_sleep_pins>;      // sleep 状态的 pin 配置
};
```

 同一引脚不能被两个外设使用。pinctrl 冲突是外设不工作的常见原因。

---

## 3. 设备树关系梳理

### 3.1 include 层级分析

**分析步骤：**
1. 打开顶层 `.dts` 文件
2. 列出所有 `#include` 指令
3. 对每个被包含的 `.dtsi` 递归执行步骤 2
4. 绘制树状结构

```
board-variant.dts
 soc.dtsi                         SoC 基础
    <dt-bindings/clock/...>      时钟 ID 宏
    <dt-bindings/gpio/gpio.h>    GPIO 标志宏
    <dt-bindings/interrupt-controller/irq.h>
 board-common.dtsi                板级通用
 display.dtsi                     显示子系统
```

### 3.2 节点合并与覆盖规则

设备树不是简单文本拼接，而是节点 **递归合并**：

| 规则 | 描述 | 示例 |
|------|------|------|
| 同名属性覆盖 | 后者覆盖前者 | dtsi: `status="disabled"`  dts: `status="okay"`  最终 `"okay"` |
| 不同属性合并 | 保留所有属性 | dtsi: `#address-cells=<1>` + dts: `clock-frequency=<400000>`  都保留 |
| 子节点递归合并 | 同名子节点按上述规则递归处理 |  |
| 显式删除 | `/delete-node/` 或 `/delete-property/` | `/delete-node/ &label;` / `/delete-property/ prop-name;` |

### 3.3 phandle 引用关系

| 引用类型 | 属性名模式 | 被引用节点类型 |
|----------|-----------|---------------|
| 时钟 | `clocks`, `assigned-clocks` | clock provider |
| 电源 | `*-supply`, `vin-supply` | regulator |
| GPIO | `*-gpios`, `gpios` | gpio controller |
| 复位 | `resets` | reset controller |
| 中断 | `interrupt-parent` | 中断控制器 |
| PHY | `phys`, `phy-handle` | PHY 设备 |
| DMA | `dmas` | DMA 控制器 |
| pinctrl | `pinctrl-0`, `pinctrl-1` | pin 配置组 |
| 电源域 | `power-domains` | power domain controller |
| 显示连接 | `remote-endpoint` | 显示 pipeline 对端 |

### 3.4 endpoint/port 显示连接

显示和媒体子系统使用 `port/endpoint` 描述设备间数据通路（必须双向引用）：

```dts
device_a {
    port {
        a_out: endpoint { remote-endpoint = <&b_in>; };
    };
};
device_b {
    port {
        b_in: endpoint { remote-endpoint = <&a_out>; };
    };
};
```

---

## 4. 问题排查与诊断

### 4.1 运行时调试命令

```bash
# 板卡信息
cat /proc/device-tree/model
cat /proc/device-tree/compatible

# 查看/反编译运行中的设备树
ls /proc/device-tree/
dtc -I fs -O dts -o running.dts /proc/device-tree/

# 硬件状态
cat /sys/kernel/debug/gpio                              # GPIO
cat /sys/kernel/debug/pinctrl/*/pinmux-pins             # pinctrl
cat /sys/kernel/debug/clk/clk_summary                   # 时钟树
cat /sys/kernel/debug/regulator/regulator_summary       # regulator
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary         # 电源域

# I2C 探测
i2cdetect -y -r 0

# 设备/驱动匹配
ls /sys/bus/platform/devices/
ls /sys/bus/i2c/devices/

# 内核日志
dmesg | grep -i "probe\|error\|fail\|OF:"
```

### 4.2 DTS 常见错误

⚠ I2C 地址在设备树中必须使用 **7 位地址**（原理图上的 8 位地址需右移 1 位）。

| 错误 | 症状 | 修复 |
|------|------|------|
| 缺 `/dts-v1/;` | dtc 报 "Unknown version" | 文件首行添加 |
| 缺分号 `;` | "unexpected token" | 检查属性和节点闭合 |
| label 不存在 | "undefined reference to &xxx" | 确认 label 在 include 链中 |
| `status = "ok"` | 节点未启用 | 改为 `"okay"` |
| reg cells 不匹配 | dtc warning | 对齐父节点 `#address-cells`/`#size-cells` |
| GPIO 极性反 | 功能异常 | 检查 `GPIO_ACTIVE_HIGH` vs `LOW` |
| pinctrl 冲突 | 外设不工作 | 同一引脚不能被两个外设使用 |
| I2C 地址用 8 位 | probe 失败 | DT 中用 7 位地址 (右移 1 位) |
| Overlay 缺 `/plugin/;` | dtbo 编译失败 | 添加到 `/dts-v1/;` 之后 |
| 字符串末尾多空格 | compatible 匹配失败 | 去除尾随空格 |

```bash
# 快速验证 DTS 语法
dtc -I dts -O dtb -o /dev/null -W no-unit_address_vs_reg your.dts
```

### 4.3 外设不工作通用排查流程

```
1. 节点存在？         ls /proc/device-tree/.../节点名
2. status="okay"?     xxd /proc/device-tree/.../status
3. compatible 正确？   cat /proc/device-tree/.../compatible
                       grep -r "compatible.*值" drivers/  (内核中搜驱动)
4. 驱动已编译？       grep CONFIG_xxx /boot/config-$(uname -r) 或 lsmod
5. probe 成功？       dmesg | grep -i "xxx.*probe"
6. 电源/时钟到位？    regulator_summary / clk_summary
7. pinctrl 正确？     pinmux-pins
8. 中断配对？         cat /proc/interrupts
```

### 4.4 场景诊断速查

| 场景 | 关键检查项 |
|------|-----------|
| **屏幕不亮** | 显示控制器 status  PHY/桥接 status  VP 通路连接  背光 PWM  面板电源  reset-gpios  panel-init-sequence  display-timings |
| **I2C 设备不识别** | `i2cdetect` 扫描  控制器 status  clock-frequency (降到 100kHz)  pinctrl mux  上拉电阻 (硬件)  电源 supply |
| **网络不通** | 控制器 status  phy-mode  PHY 地址 reg  PHY reset GPIO+delay  TX/RX delay  clock  pinctrl mux+drive strength |
| **USB 不识别** | PHY status  EHCI/OHCI status  Combo PHY 复用冲突  电源 regulator  dr_mode |

### 4.5 工具箱

| 工具 | 用途 | 安装 |
|------|------|------|
| `dtc` | 编译/反编译 | `apt install device-tree-compiler` |
| `fdtdump` / `fdtget` / `fdtput` | DTB 查看/读取/修改 | 随 dtc |
| `fdtoverlay` | DTB + DTBO 合并 | 随 dtc |
| `i2cdetect` / `i2cget` / `i2cset` | I2C 工具 | `apt install i2c-tools` |
| `devmem2` | 寄存器读写 | `apt install devmem2` |
| `gpioinfo` / `gpioget` | GPIO 状态 | `apt install gpiod` |
| `media-ctl` | 媒体拓扑 | `apt install v4l-utils` |
| `ethtool` | 网络 PHY | `apt install ethtool` |

---

## 5. 多平台知识索引

| 平台 | SoC 系列 | pinctrl binding | 内核文档路径 |
|------|---------|-----------------|-------------|
| Rockchip | RK35xx/RK33xx/PX30 | `rockchip,pins` | `bindings/arm/rockchip.yaml` |
| 全志 | A64/H6/H616/D1 | `allwinner,pins` | `bindings/arm/sunxi.yaml` |
| NXP | i.MX6/i.MX8 | `fsl,pins` | `bindings/arm/fsl.yaml` |
| TI | AM335x/AM62x | groups + function | `bindings/arm/ti.yaml` |
| Qualcomm | SDM845/SM8xxx | `qcom,pins` + function | `bindings/arm/qcom.yaml` |
| Samsung | Exynos | `samsung,pins` | `bindings/arm/samsung.yaml` |
| ST | STM32MP1/MP2 | ST pinctrl | `bindings/arm/stm32.yaml` |
| Broadcom | BCM2835 (RPi) | `brcm,pins` | `bindings/arm/bcm.yaml` |
| Microchip | SAMA5/SAM9 | Atmel pinctrl | `bindings/arm/atmel-at91.yaml` |
| Xilinx/AMD | Zynq/ZynqMP | Xilinx pinctrl | `bindings/arm/xilinx.yaml` |
| StarFive | JH71x0 | StarFive pinctrl | `bindings/riscv/starfive.yaml` |

不同厂商差异主要在：pinctrl 语法、时钟 ID 宏、中断编号、电源域 binding、显示 pipeline 架构、PHY 组合策略。

---

## 6. 参考资料

### 标准规范
- **Device Tree Specification**: https://devicetree-specification.readthedocs.io/
- **内核 DT Bindings**: https://www.kernel.org/doc/Documentation/devicetree/bindings/
- **eLinux DT Usage**: https://elinux.org/Device_Tree_Usage

### 本地参考文件

| 文件 | 内容 | 何时读取 |
|------|------|---------|
| `references/dt-syntax-reference.md` | DTS 语法完整参考 (数据类型、特殊节点、`/delete-*`) | 需要理解语法细节时 |
| `references/peripheral-templates.md` | 所有常见外设 DTS 节点模板 (LED/I2C/SPI/UART/ETH/USB/DSI/HDMI 等) | 编写新设备树时 |
| `references/overlay-guide.md` | 设备树 Overlay 编写与调试完整指南 | 编写或调试 overlay 时 |
| `references/multi-platform-pinctrl.md` | 各平台 pinctrl binding 对比与示例 | 跨平台 pinctrl 问题时 |

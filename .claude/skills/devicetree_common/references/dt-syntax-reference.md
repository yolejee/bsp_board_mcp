# DTS 语法完整参考

## 1. 文件结构

每个 `.dts` 文件的基本骨架：

```dts
/dts-v1/;     // 版本声明 (必须在首行)

// C 预处理器 include
#include <dt-bindings/gpio/gpio.h>
#include "soc.dtsi"

/ {
    // 根节点内容
};

// 在根节点外部通过 label 引用覆盖
&label_name {
    property = "value";
};
```

## 2. 数据类型详解

### 2.1 空值 (Empty / Boolean)
```dts
// 属性存在即为 true，不存在即为 false
regulator-always-on;     // 等效于 true
non-removable;           // eMMC 不可拔出
```

### 2.2 无符号整数 u32
```dts
clock-frequency = <24000000>;    // 24MHz
reg = <0x10000>;                 // 单个 u32
```

### 2.3 无符号 64 位整数
```dts
// 用两个 u32 表示：<高32位 低32位>
reg = <0x00 0x80000000 0x00 0x40000000>;  // 地址 0x80000000，大小 1GB
```

### 2.4 字符串
```dts
model = "My Custom Board";
status = "okay";
```

### 2.5 字符串列表
```dts
// 逗号分隔
compatible = "vendor,device-v2", "vendor,device-v1", "generic-device";
clock-names = "core_clk", "iface_clk";
```

### 2.6 字节串 (bytestring)
```dts
// 方括号内的十六进制字节
mac-address = [00 11 22 33 44 55];
local-mac-address = [AA BB CC DD EE FF];
```

### 2.7 phandle 引用
```dts
// 尖括号内用 & 引用 label
interrupt-parent = <&gic>;
clocks = <&cru CLK_UART0>, <&cru PCLK_UART0>;
```

### 2.8 混合类型
```dts
// 数组内可混合 phandle 和整数
clocks = <&cru 100>;   // phandle + specifier
```

### 2.9 数组
```dts
brightness-levels = <0 4 8 16 32 64 128 255>;
```

## 3. 节点命名规则

```
node-name@unit-address {
    ...
};
```

| 规则 | 说明 | 正确示例 | 错误示例 |
|----|------|---------|---------|
| lowercase + hyphen | 节点名小写字母和连字符 | `serial@44e09000` | `Serial@44e09000` |
| `@unit-address` | 必须与 reg 首值匹配 | `i2c@10050000 { reg = <0x10050000 ...>; }` | 不匹配 |
| 无 reg 则无 @address | 无地址节点不加 @ | `leds { ... }` | `leds@ { }` |
| 同级唯一 | 同级不能有两个同名节点 | — | — |
| 推荐用通用名 | `serial` 而非 `uart8250` | `serial@44e09000` | `uart8250@44e09000` |

### 通用设备类型名 (推荐前缀)

```
adc, audio-codec, audio-controller, backlight, bluetooth,
bus, cache-controller, camera, can, clock, cpu, crypto,
dma-controller, display, dsi, edp, ehci, emmc, ethernet,
ethernet-phy, flash, gpio, gpu, hdmi, i2c, interrupt-controller,
iommu, led, lvds, mailbox, mdio, memory, memory-controller,
mmc, nand-controller, nor-flash, ohci, pci, phy, pinctrl,
pmu, power-controller, pwm, regulator, reset-controller,
rng, rtc, sata, scsi, serial, sound, spi, syscon, timer,
touchscreen, usb, usb-phy, video-codec, watchdog, wifi
```

## 4. Label (标签)

```dts
// 定义 label (在节点定义处)
uart0: serial@44e09000 {
    compatible = "ti,am3352-uart";
    reg = <0x44e09000 0x1000>;
    status = "disabled";
};

// 通过 label 引用并覆盖 (在另一文件中)
&uart0 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&uart0_pins>;
};
```

## 5. 属性删除与节点删除

```dts
// 删除属性
&node_label {
    /delete-property/ some-property;
};

// 删除节点 (通过 label)
/delete-node/ &unwanted_node;

// 删除节点 (通过路径，在父节点内)
&parent {
    /delete-node/ child-name@address;
};
```

## 6. 特殊属性

### 6.1 `#address-cells` 和 `#size-cells`

定义子节点 `reg` 属性的解释方式：

```dts
// 父节点
soc {
    #address-cells = <2>;   // reg 地址用 2 个 u32 (64 位)
    #size-cells = <2>;      // reg 大小用 2 个 u32

    device@10050000 {
        reg = <0x0 0x10050000 0x0 0x1000>;
        //     ^ address (2 cells)  ^ size (2 cells)
    };
};

// I2C 总线常用
i2c {
    #address-cells = <1>;   // I2C 设备地址只有 1 个 u32
    #size-cells = <0>;      // I2C 设备无 size

    sensor@44 {
        reg = <0x44>;       // I2C 7 位地址
    };
};
```

### 6.2 `ranges`

地址空间映射（子 → 父地址转换）：

```dts
soc {
    #address-cells = <1>;
    #size-cells = <1>;
    // ranges = <子地址 父地址 大小>;
    ranges = <0x0 0x0 0x44e00000 0x10000000>;

    // 空 ranges: 1:1 映射
    // ranges;
};
```

### 6.3 `compatible`

```dts
// 从最具体到最通用 — 驱动按顺序匹配
compatible = "vendor,board-specific-uart",
             "vendor,soc-uart",
             "ns16550a";
```

### 6.4 `phandle`

通常由 dtc 自动生成，不需要手写：
```dts
// 手动指定 (不推荐)
node {
    phandle = <0x1>;
};
```

## 7. 条件编译 (预处理器)

因为 DTS 使用 C 预处理器，可以用 `#ifdef`/`#if`:

```dts
#include <dt-bindings/gpio/gpio.h>

// 头文件中的宏定义可以在 DTS 中使用
gpios = <&gpio0 5 GPIO_ACTIVE_HIGH>;  // GPIO_ACTIVE_HIGH = 0

// 部分平台 BSP 会用 #ifdef 做条件编译
#ifdef CONFIG_DISPLAY_HDMI
    &hdmi { status = "okay"; };
#endif
```

> 注意：标准内核构建不支持 `#ifdef CONFIG_xxx`，这是某些厂商 BSP 的扩展行为。

## 8. Overlay 特有语法

```dts
/dts-v1/;
/plugin/;        // 声明这是 overlay

/ {
    // 方式 1: target 引用 label
    fragment@0 {
        target = <&uart1>;
        __overlay__ {
            status = "okay";
        };
    };

    // 方式 2: target-path 路径
    fragment@1 {
        target-path = "/soc/serial@44e09000";
        __overlay__ {
            status = "disabled";
        };
    };

    // 方式 3: 新语法 (简化 — dtc >= 1.5.1)
    // 直接用 &label，无需 fragment 包装
    // (取决于工具链支持)
};
```

## 9. 常用 dt-bindings 头文件

| 头文件 | 定义的宏 |
|--------|---------|
| `dt-bindings/gpio/gpio.h` | `GPIO_ACTIVE_HIGH`, `GPIO_ACTIVE_LOW`, `GPIO_OPEN_DRAIN` 等 |
| `dt-bindings/interrupt-controller/irq.h` | `IRQ_TYPE_LEVEL_HIGH`, `IRQ_TYPE_EDGE_FALLING` 等 |
| `dt-bindings/interrupt-controller/arm-gic.h` | `GIC_SPI`, `GIC_PPI` |
| `dt-bindings/input/input.h` | `KEY_POWER`, `KEY_VOLUMEUP` 等 |
| `dt-bindings/leds/common.h` | LED function 和 color 宏 |
| `dt-bindings/clock/vendor-xxx.h` | 平台特定时钟 ID |
| `dt-bindings/pinctrl/xxx.h` | 平台特定 pinctrl 宏 |
| `dt-bindings/power/xxx.h` | 电源域 ID |
| `dt-bindings/phy/phy.h` | `PHY_TYPE_USB2`, `PHY_TYPE_PCIE` 等 |
| `dt-bindings/usb/pd.h` | USB PD 相关宏 |
| `dt-bindings/display/drm_mipi_dsi.h` | `MIPI_DSI_MODE_VIDEO` 等 |

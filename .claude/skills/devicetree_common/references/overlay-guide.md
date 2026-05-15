# 设备树 Overlay 编写与调试完整指南

## 1. 什么是 Device Tree Overlay

Device Tree Overlay (设备树插件/覆盖) 允许在运行时或 bootloader 阶段动态修改基础设备树 (base DTB)，无需重新编译整个 DTB。

**典型使用场景：**
- 扩展板/Hat 检测后动态加载对应 DTS
- 用户可选功能模块 (屏幕、摄像头、CAN 总线等)
- 引脚复用冲突管理 (UART 和 SPI 复用同一组引脚)
- 快速原型验证，无需修改主 DTS

## 2. Overlay 文件结构

### 2.1 标准 fragment 语法

```dts
/dts-v1/;
/plugin/;    // 必须！声明这是 overlay

#include <dt-bindings/gpio/gpio.h>
#include <dt-bindings/interrupt-controller/irq.h>

/ {
    compatible = "vendor,board-name";  // 可选：限定适用板卡

    // 修改已有节点
    fragment@0 {
        target = <&uart3>;        // 通过 label 引用
        __overlay__ {
            status = "okay";
            pinctrl-names = "default";
            pinctrl-0 = <&uart3_xfer>;
        };
    };

    // 添加新的子节点
    fragment@1 {
        target = <&i2c1>;
        __overlay__ {
            #address-cells = <1>;
            #size-cells = <0>;

            sensor@48 {
                compatible = "ti,tmp102";
                reg = <0x48>;
            };
        };
    };

    // 在根节点下添加新节点
    fragment@2 {
        target-path = "/";
        __overlay__ {
            ext_leds: extension-leds {
                compatible = "gpio-leds";
                led-ext0 {
                    gpios = <&gpio3 5 GPIO_ACTIVE_HIGH>;
                    label = "ext:green:user";
                    linux,default-trigger = "default-on";
                };
            };
        };
    };

    // 禁用冲突外设
    fragment@3 {
        target = <&spi1>;
        __overlay__ {
            status = "disabled";
        };
    };
};
```

### 2.2 简化语法 (dtc >= 1.5.1)

较新版本 dtc 支持直接使用 `&label` 而无需 `fragment` 包装：

```dts
/dts-v1/;
/plugin/;

&uart3 {
    status = "okay";
};

&i2c1 {
    sensor@48 {
        compatible = "ti,tmp102";
        reg = <0x48>;
    };
};
```

> 注意：并非所有 bootloader/工具链都支持简化语法，建议保持兼容性时使用标准 fragment 格式。

### 2.3 target 引用方式

| 方式 | 语法 | 适用场景 |
|------|------|---------|
| phandle | `target = <&label>` | 引用 base DTB 中有 label 的节点 |
| 路径 | `target-path = "/soc/serial@..."` | 引用没有 label 的节点 |

## 3. 编译指南

### 3.1 编译 Overlay

```bash
# 必须使用 -@ 选项生成 __symbols__ 节点
dtc -@ -I dts -O dtb -o overlay.dtbo overlay.dts

# 如果有 include 头文件，需要预处理
cpp -nostdinc -I include -undef -x assembler-with-cpp \
    overlay.dts overlay.dts.preprocessed
dtc -@ -I dts -O dtb -o overlay.dtbo overlay.dts.preprocessed

# 在内核源码树中编译
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs
# overlay 文件通常放在 arch/arm64/boot/dts/overlays/ 下
```

### 3.2 编译 Base DTB (启用 symbols)

```bash
# Base DTB 也必须用 -@ 编译，才能接受 overlay 的 label 引用
dtc -@ -I dts -O dtb -o base.dtb base.dts

# 内核 Makefile 中默认可能不带 -@
# 在 scripts/Makefile.lib 中检查 DTC_FLAGS
```

### 3.3 合并验证

```bash
# 离线合并 (用于测试)
fdtoverlay -i base.dtb overlay.dtbo -o merged.dtb

# 多个 overlay 依次合并
fdtoverlay -i base.dtb ov1.dtbo ov2.dtbo ov3.dtbo -o merged.dtb

# 反编译验证
dtc -I dtb -O dts -o merged.dts merged.dtb
```

## 4. 加载方式

### 4.1 U-Boot 中加载

```
# 在 U-Boot 命令行
load mmc 0:1 $fdt_addr base.dtb
load mmc 0:1 $overlay_addr overlay.dtbo

# 设置并应用 overlay
fdt addr $fdt_addr
fdt resize 8192
fdt apply $overlay_addr

# 继续启动
bootz $kernel_addr - $fdt_addr
```

U-Boot 环境变量配置自动加载：
```
# boot.cmd / boot.scr
setenv fdtfile board.dtb
setenv overlay_files "uart3-enable.dtbo can-bus.dtbo"

load mmc 0:1 ${fdt_addr_r} ${fdtfile}
fdt addr ${fdt_addr_r}
fdt resize 65536

for overlay in ${overlay_files}; do
    load mmc 0:1 ${fdtoverlay_addr_r} overlays/${overlay}
    fdt apply ${fdtoverlay_addr_r}
done
```

### 4.2 Linux 运行时加载 (ConfigFS)

需要内核编译了 `CONFIG_OF_OVERLAY` 和 `CONFIG_OF_CONFIGFS`:

```bash
# 创建 overlay 实例
mkdir -p /sys/kernel/config/device-tree/overlays/my-overlay

# 加载 dtbo
cat overlay.dtbo > /sys/kernel/config/device-tree/overlays/my-overlay/dtbo

# 检查状态
cat /sys/kernel/config/device-tree/overlays/my-overlay/status
# 应显示 "applied"

# 移除 overlay
rmdir /sys/kernel/config/device-tree/overlays/my-overlay
```

### 4.3 Raspberry Pi 方式

```ini
# /boot/config.txt (Raspberry Pi)
dtoverlay=uart3
dtoverlay=i2c-sensor,addr=0x48
dtparam=i2c_arm=on
```

### 4.4 Rockchip 方式

Rockchip 平台通常在 U-Boot 的 extlinux.conf 或 env 中指定：
```
# /boot/extlinux/extlinux.conf
fdtoverlays /boot/dtbo/uart3-enable.dtbo /boot/dtbo/can-bus.dtbo
```

## 5. 常见问题与调试

### 5.1 "undefined reference" 错误

```
Error: overlay.dts:8: undefined reference to &uart3
```

**原因：** Base DTB 没有用 `-@` 编译，缺少 `__symbols__` 节点。
**解决：** 重新编译 base DTB 时加 `-@` 选项。

### 5.2 overlay 加载后不生效

**排查步骤：**
```bash
# 1. 确认 overlay 已正确加载
cat /sys/kernel/config/device-tree/overlays/my-overlay/status

# 2. 反编译运行时设备树，验证修改是否生效
dtc -I fs -O dts -o running.dts /proc/device-tree/

# 3. 检查内核日志
dmesg | tail -20
```

### 5.3 fragment target 节点不存在

```
Error: Failed to apply overlay
```

**原因：** overlay 引用的 target label 在 base DTB 中不存在。
**解决：** 
- 检查 base DTB 中是否定义了该 label
- 使用 `fdtdump base.dtb | grep -i label_name` 查找
- 改用 `target-path` 替代

### 5.4 pinctrl 冲突

当两个 overlay 试图将同一引脚配置给不同外设时，后加载的 overlay 可能导致第一个外设失效。

**最佳实践：**
- 在 overlay 中显式 disable 冲突外设
- 使用互斥 overlay 组（如 spi1 和 uart3 二选一）

### 5.5 移除 overlay 后设备仍存在

某些驱动不支持热插拔移除。重启后生效是最可靠的方式。

## 6. 最佳实践

1. **命名规范**：overlay 文件名应描述功能，如 `enable-uart3.dtbo`、`mipi-dsi-7inch.dtbo`
2. **compatible 限制**：在 overlay 根节点加 `compatible` 限定适用板卡
3. **禁用冲突**：显式 disable 引脚冲突的外设
4. **版本注释**：在 overlay 头部注释支持的 base DTB 版本
5. **测试**：先用 `fdtoverlay` 离线合并验证，再部署到设备
6. **文档**：每个 overlay 附带简短说明文档

## 7. Overlay 参数化 (DT Parameters)

某些实现 (如 Raspberry Pi) 支持可参数化的 overlay：

```dts
/dts-v1/;
/plugin/;

/ {
    fragment@0 {
        target = <&i2c1>;
        __overlay__ {
            #address-cells = <1>;
            #size-cells = <0>;
            
            sensor: sensor@0 {
                compatible = "ti,tmp102";
                reg = <0x48>;
                status = "okay";
            };
        };
    };

    __overrides__ {
        addr = <&sensor>, "reg:0";
        status = <&sensor>, "status";
    };
};
```

使用：`dtoverlay=my-sensor,addr=0x49,status=disabled`

> 注意：`__overrides__` 是 Raspberry Pi / Broadcom 的扩展，非标准 DT 功能，其他平台通常不支持。

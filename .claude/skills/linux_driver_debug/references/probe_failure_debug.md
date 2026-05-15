# Probe 失败深度排查参考

## 目录

1. [Linux 设备/驱动匹配机制详解](#1-linux-设备驱动匹配机制详解)
2. [Deferred Probe 机制](#2-deferred-probe-机制)
3. [initcall 级别与加载顺序](#3-initcall-级别与加载顺序)
4. [模块加载调试](#4-模块加载调试)
5. [Probe 错误码完整参考](#5-probe-错误码完整参考)
6. [实战诊断案例](#6-实战诊断案例)

---

## 1. Linux 设备/驱动匹配机制详解

### 1.1 Platform Bus 匹配流程

```c
// drivers/base/platform.c: platform_match()
static int platform_match(struct device *dev, struct device_driver *drv)
{
    struct platform_device *pdev = to_platform_device(dev);
    struct platform_driver *pdrv = to_platform_driver(drv);

    /* 1. 优先: of_match_table (Device Tree) */
    if (of_driver_match_device(dev, drv))
        return 1;

    /* 2. ACPI style match */
    if (acpi_driver_match_device(dev, drv))
        return 1;

    /* 3. id_table match */
    if (pdrv->id_table)
        return platform_match_id(pdrv->id_table, pdev) != NULL;

    /* 4. fallback: driver name match */
    return (strcmp(pdev->name, drv->name) == 0);
}
```

### 1.2 of_match_table 匹配规则

```c
static const struct of_device_id my_of_match[] = {
    { .compatible = "vendor,exact-model" },      // 精确匹配
    { .compatible = "vendor,family-name" },       // 家族匹配
    { },                                         // 终止符必须有
};
MODULE_DEVICE_TABLE(of, my_of_match);
```

**匹配规则：**
- DTS 中 `compatible` 是一个字符串列表，从最具体到最通用
- 内核按列表顺序逐个与 `of_match_table` 比对
- 第一个匹配的项决定使用哪个驱动
- 匹配是**精确字符串比较**，大小写敏感

```dts
// 示例: DTS 中
compatible = "bosch,bme280", "bosch,bmp280";
// 优先匹配 bme280 的驱动, 如果没有则 fallback 到 bmp280
```

### 1.3 I2C/SPI Bus 匹配

```c
// I2C 匹配流程:
// 1. of_match_table (compatible)
// 2. i2c_device_id table (name)
// 3. ACPI match

// SPI 匹配流程:
// 1. of_match_table (compatible)
// 2. spi_device_id table (name)

// 重要: I2C/SPI 设备地址由 DTS 中的 reg 属性指定
// 如果地址错误, 设备可以注册但通信会失败
```

### 1.4 确认匹配的调试方法

```bash
# 查看驱动支持的 compatible 列表
modinfo <module_name> | grep alias
# 输出: alias: of:N*T*Cvendor,device-name*

# 查看 DTS 中某设备的 compatible
cat /sys/firmware/devicetree/base/<path>/compatible

# 查看匹配结果
cat /sys/bus/platform/devices/<dev>/modalias
# 比对 modalias 和 modinfo alias

# 强制指定驱动 (绕过匹配, 仅调试)
echo <driver_name> > /sys/bus/platform/devices/<dev>/driver_override
echo <dev_id> > /sys/bus/platform/drivers/<driver>/bind
```

---

## 2. Deferred Probe 机制

### 2.1 工作原理

```
driver.probe() 返回 -EPROBE_DEFER
  ↓
设备加入 deferred_probe_pending_list
  ↓
当有新设备成功 probe 时,
触发 deferred_probe_work_func()
  ↓
重新尝试所有 pending 设备的 probe
  ↓
如果依赖已满足 → probe 成功
如果依赖仍未满足 → 继续 defer
```

### 2.2 常见 defer 依赖链

| 依赖资源 | 获取函数 | 提供者 |
|---------|---------|-------|
| regulator | `devm_regulator_get()` | PMIC 驱动 |
| clock | `devm_clk_get()` | Clock controller |
| GPIO | `devm_gpiod_get()` | GPIO controller |
| Reset | `devm_reset_control_get()` | Reset controller |
| PHY | `devm_phy_get()` | PHY provider |
| Pinctrl | 自动 (probe 时) | Pinctrl driver |
| Power domain | 自动 (genpd) | PM domain controller |

### 2.3 排查 deferred probe

```bash
# 1. 查看哪些设备在等待
cat /sys/kernel/debug/devices_deferred
# 输出: <device_name>  <driver_name>

# 2. 找到卡住的原因 (5.9+ 内核)
# 打开 deferred probe 原因日志
echo 'file drivers/base/dd.c +p' > /sys/kernel/debug/dynamic_debug/control
echo 'file drivers/base/core.c +p' > /sys/kernel/debug/dynamic_debug/control
# 然后 dmesg 中会显示具体哪个资源 defer 了

# 3. 查看 probe 尝试顺序
# 启动参数加: initcall_debug
# 或: echo 'file drivers/base/dd.c +p' > /sys/kernel/debug/dynamic_debug/control

# 4. 打印供电链
cat /sys/kernel/debug/regulator/regulator_summary
# 如果某个 regulator 的 consumer 还没 probe, 说明 PMIC 驱动滞后

# 5. 循环 defer 死锁 (罕见)
# A 等 B, B 等 A → 两个都永远 pending
# 解法: 调整 initcall level 或用 probe_type = PROBE_PREFER_ASYNCHRONOUS
```

---

## 3. initcall 级别与加载顺序

### 3.1 initcall 级别

```c
// 从内核源码 include/linux/init.h
#define pure_initcall(fn)        __define_initcall(fn, 0)    // 最早
#define core_initcall(fn)        __define_initcall(fn, 1)
#define postcore_initcall(fn)    __define_initcall(fn, 2)
#define arch_initcall(fn)        __define_initcall(fn, 3)
#define subsys_initcall(fn)      __define_initcall(fn, 4)    // 子系统
#define fs_initcall(fn)          __define_initcall(fn, 5)
#define device_initcall(fn)      __define_initcall(fn, 6)    // = module_init
#define late_initcall(fn)        __define_initcall(fn, 7)    // 最晚
```

### 3.2 常见子系统的 initcall 级别

| 子系统 | initcall 级别 | 说明 |
|--------|-------------|------|
| 中断控制器 | `core/arch` | 最早初始化 |
| Clock controller | `core/postcore` | 很早 |
| Pinctrl | `core/postcore` | 很早 |
| PMIC (I2C) | `subsys` | 依赖 I2C bus |
| GPIO controller | `subsys/postcore` | 依赖 pinctrl |
| 大多数外设驱动 | `module_init (6)` | 默认级别 |
| 延迟初始化 | `late_initcall` | 最后 |

### 3.3 查看 initcall 执行

```bash
# 内核启动参数加:
initcall_debug

# dmesg 中会看到:
# calling  xxxxxx_init+0x0/0x... @ 1
# initcall xxxxxx_init+0x0/0x... returned 0 after XXXX usecs

# 解析: returned 0 = 成功, returned -ENODEV = 设备不存在 (正常), 其他 = 错误
```

---

## 4. 模块加载调试

### 4.1 模块加载失败

```bash
# 查看模块依赖
modinfo <module.ko>          # 查看 vermagic, depends, alias 等
modprobe -v <module>         # verbose 加载

# 常见失败原因:
# "Invalid module format" → 内核版本不匹配 (vermagic)
# "Unknown symbol" → 依赖模块未加载
# "Operation not permitted" → CONFIG_MODULE_SIG_FORCE=y, 签名校验失败

# 查看模块符号依赖
modprobe --show-depends <module>

# 手动加载时加调试
insmod <module.ko>
dmesg | tail -20             # 查看内核日志

# 查看可用模块
ls /lib/modules/$(uname -r)/
find /lib/modules/$(uname -r)/ -name "*.ko" | grep <keyword>
```

### 4.2 编译为 builtin vs module

```bash
# 查看某个 CONFIG 编译为什么
grep CONFIG_XXX /boot/config-$(uname -r)
# =y → 内建, =m → 模块, 不存在 → 未编译

# 如果驱动编译为 builtin, 不需要 insmod/modprobe
# 如果编译为 module, probe 时机取决于 modprobe 调用时间
```

---

## 5. Probe 错误码完整参考

| 错误码 | 值 | 含义 | 排查方向 |
|--------|---|------|---------|
| -EPROBE_DEFER | -517 | 依赖资源未就绪 | 查 deferred list, 检查依赖链 |
| -ENODEV | -19 | 设备不存在 | 检查 compatible / DTS status |
| -ENOMEM | -12 | 内存分配失败 | 检查系统内存, KMEMLEAK |
| -EINVAL | -22 | 参数无效 | DTS 属性缺失或格式错误 |
| -EIO | -5 | I/O 错误 | 硬件通信失败, 检查总线 |
| -EBUSY | -16 | 资源被占用 | GPIO/IRQ/IO region 冲突 |
| -ENXIO | -6 | 无此设备 | 地址/通道号错误 |
| -EACCES | -13 | 权限不足 | 安全限制, SELinux |
| -ENOSPC | -28 | 空间不足 | IRQ/DMA channel 耗尽 |
| -ETIMEDOUT | -110 | 超时 | 硬件未响应, 时钟/供电问题 |
| -ENOENT | -2 | 资源不存在 | DTS 中缺少引用 (clocks/resets等) |

---

## 6. 实战诊断案例

### 案例 1: I2C 设备 probe 失败返回 -EIO

```bash
# 症状: dmesg 显示 "xxx: probe failed with error -5"
# 诊断:
i2cdetect -y <bus>        # 看设备在不在
# 如果地址位 "--" → 设备不在总线上
#   检查: 供电、I2C 地址(硬件引脚)、上拉电阻

# 如果地址位 "03" → 设备在但驱动通信失败
#   可能: 寄存器地址/格式与驱动不匹配 (芯片版本不对)
```

### 案例 2: 设备存在但不 probe

```bash
# 症状: /sys/bus/platform/devices/ 有设备但没有 driver 链接
# 诊断:
cat /sys/bus/platform/devices/<dev>/modalias
modinfo <module> | grep alias
# 比对两者, 确认 compatible 字符串是否完全一致

# 如果 modalias 不匹配:
# 检查 DTS 中 compatible 拼写
# 检查驱动中 of_match_table 是否有对应项
# 检查 CONFIG_xxx 是否开启
```

### 案例 3: Deferred Probe 卡住

```bash
# 症状: 设备一直在 devices_deferred 列表中
# 诊断:
cat /sys/kernel/debug/devices_deferred
# 找到卡住的设备名

# 打开 dynamic debug
echo 'file drivers/base/dd.c +p' > /sys/kernel/debug/dynamic_debug/control
# 重新触发 probe
echo <dev_id> > /sys/bus/platform/drivers/<drv>/bind
# dmesg 中查看具体哪个 devm_xxx_get 返回了 -EPROBE_DEFER
```

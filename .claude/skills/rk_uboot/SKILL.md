---
name: rk_uboot
description: "Rockchip 瑞芯微平台 U-Boot 引导加载器技能。覆盖 RK3588/RK3568/RK3566/RK3399/RK3288/PX30/RV1126/RK3308 等全系列芯片的 U-Boot 启动流程、编译打包、FIT 固件格式、SPL/TPL 开源引导、安全启动 (Secure Boot/AVB)、AB 系统、分区管理、驱动调试、固件升级方案。触发关键词：U-Boot、uboot、bootloader、启动流程、boot flow、SPL、TPL、FIT、miniloader、idbloader、Maskrom、rockusb、fastboot、烧写、boot_android、distro_bootcmd、extlinux、GPT 分区、parameter.txt、Secure Boot、AVB、vbmeta、AB 系统、slot_a、slot_b、DTBO、HW-ID DTB、SD 卡启动、OTA 升级、TFTP 升级、充电动画、AMP、dm tree、U-Boot 死机、开机慢。当用户在 Rockchip 平台遇到 U-Boot 配置、编译、启动、升级、安全引导或调试相关的问题时触发。"
---

# Rockchip U-Boot 引导加载器技能

## 1. 平台概览与启动路径

### 1.1 两条启动路径

| 路径 | 流程 | 适用平台 |
|------|------|---------|
| Miniloader (闭源) | BOOTROM → ddr bin → Miniloader → Trust → U-Boot → Kernel | RK3399, RK3288 等老平台 |
| SPL+FIT (开源) | BOOTROM → TPL → SPL → Trust → U-Boot → Kernel | RV1126, RK3568, RK3588 等新平台 |

- **TPL**: 运行在 SRAM，负责 DDR 初始化（代替闭源 ddr bin）
- **SPL**: 运行在 DDR，负责加载 Trust + U-Boot（代替闭源 Miniloader）
- **U-Boot proper**: 加载并引导 Kernel

> **闭源 vs 开源 TPL/SPL**: RK SDK 的 rkbin/ 目录提供闭源二进制 (rk3568_ddr_xxx/rk356x_spl_x)；
> 也可用 U-Boot 编译开源 TPL+SPL (`./make.sh rk3566`)。可混用（如闭源 TPL + 开源 SPL）。
> 注意：部分平台（如 RK3566）开源 TPL 暂不可用，需使用闭源 ddr bin。

### 1.2 ATAGS 传参机制

RK 固件间通过 ATAGS 传递参数（DDR 信息、串口配置、启动介质等）：
```
内存布局: DDR_BASE + (2MB - 8KB), 总大小 8KB
CONFIG_ROCKCHIP_PRELOADER_ATAGS=y (U-Boot 默认启用)
API: atags_get_tag() / atags_set_tag()
传递方向: TPL → SPL → Trust → U-Boot
```

### 1.2 U-Boot 版本

| 分支 | 基础版本 | 状态 |
|------|---------|------|
| next-dev | v2017.09 | **当前主线**，支持 DM 框架、FIT、AVB、SPL/TPL |
| rkdevelop | v2014.10 | 旧版本，不再更新 |

### 1.3 Boot 命令优先级

```
boot_android → bootrkp → run distro_bootcmd
```

- **boot_android**: Android 格式 (magic "ANDROID!")
- **bootrkp**: RK 格式 (magic "KRNL"/"LOADER"/"BL3X")
- **distro_bootcmd**: Distro 格式 (extlinux.conf)
- **FIT**: FIT 格式 (magic 0xd00dfeed)，通过 `boot_fit` 命令

### 1.4 热键快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+C | 进入 U-Boot 命令行 |
| Ctrl+D | 进入 Loader 烧写模式 |
| Ctrl+B | 进入 Maskrom 模式 |
| Ctrl+F | 进入 Fastboot 模式 |
| Ctrl+M | 显示 bidram 信息 |
| Ctrl+S | 停在 kernel 加载前 |

## 2. 编译与打包

### 2.1 编译环境与流程

```bash
# 前置条件: rkbin 仓库与 U-Boot 同级目录，GCC 工具链在 prebuilts/
# 首次编译 (defconfig + 编译):
./make.sh rk3568

# 重编译 (不触发 defconfig):
./make.sh

# Config fragment (叠加配置):
./make.sh rv1126-emmc-tb    # 叠加 rv1126-emmc-tb.config 到 rv1126_defconfig
```

### 2.2 编译产物

| 产物 | 说明 |
|------|------|
| `uboot.img` | FIT 方案: trust + u-boot.bin；传统方案: 仅 U-Boot |
| `trust.img` | 仅传统方案需要 (FIT 方案已合并到 uboot.img) |
| `rkXXXX_loader_vX.XX.XXX.bin` | Loader (ddr bin + miniloader/SPL) |
| `spl/u-boot-spl.bin` | SPL 固件 |
| `tpl/u-boot-tpl.bin` | TPL 固件 |

### 2.3 特殊打包命令

```bash
./make.sh trust     # 单独打包 trust.img
./make.sh loader    # 单独打包 loader
./make.sh spl       # 打包 SPL loader (TPL+SPL)
./make.sh itb       # 单独打包 uboot.itb
./make.sh env       # 生成 fw_printenv 工具
./make.sh elf       # 反汇编 u-boot
./make.sh elf-x spl # 反汇编 spl
```

### 2.4 烧写模式

| 模式 | 进入方式 | 说明 |
|------|---------|------|
| Loader | Vol+ 按键 / Ctrl+D / `download` 命令 | 可烧写所有分区 |
| Maskrom | Ctrl+B / `rbrom` 命令 | 最底层烧写模式 |
| Fastboot | Ctrl+F / `reboot fastboot` / `fastboot usb 0` | 支持 flash/erase/getvar |

## 3. 内存布局与 DTS 双机制

### 3.1 内存布局 (64 位平台示例)

```
0x00000000 ┌─────────────────┐
           │ ATF (BL31)      │ ~1MB
0x00100000 ├─────────────────┤
           │ SHM             │ ~1MB
0x00200000 ├─────────────────┤
           │ Kernel / U-Boot │
           │ ...             │
0x08400000 ├─────────────────┤
           │ OP-TEE (BL32)   │ 2~30MB
           ├─────────────────┤
           │ (gap)           │
  TOP-16MB ├─────────────────┤
           │ Video/FB        │
  TOP-xxMB ├─────────────────┤
           │ Malloc          │
           │ U-Boot code     │
  TOP      └─────────────────┘
```

### 3.2 Kernel DTB 双机制

U-Boot 使用 **两份 DTB**:
1. **U-Boot DTB** (`dt-spl.dtb`): 仅包含 storage + uart 等启动必需节点
2. **Kernel DTB** (`dt.dtb`): 包含所有外设信息

**关键函数**: `init_kernel_dtb()` 在 `board_init()` 阶段加载 Kernel DTB，之后所有外设驱动使用 Kernel DTB。

**Live Device Tree**: 采用 `ofnode` 联合类型 (`device_node*` + fdt offset`)，支持 `CONFIG_OF_LIVE`。

**DTS 标记规则**:
- `u-boot,dm-pre-reloc`: 在 relocation 前就需要的节点 (SPL/TPL 也用到)
- `u-boot,dm-spl`: 仅 SPL 阶段使用
- `u-boot,dm-tpl`: 仅 TPL 阶段使用

## 4. 分区表

### 4.1 GPT vs RK Parameter

| 特性 | GPT | RK Parameter |
|------|-----|-------------|
| 标准 | UEFI 标准 | RK 私有 |
| 标识 | `TYPE: GPT` | 无 TYPE 或无此行 |
| 推荐 | **推荐** (新平台) | 兼容旧平台 |
| 分区工具 | gdisk, parted | parameter.txt |
| 最后分区 | 需加 `:grow` | 使用 `-` |

**两者共存时 GPT 优先**。

### 4.2 分区格式 (Parameter)

```
# 格式: size@offset(name)  单位: sector (512B)
CMDLINE:mtdparts=rk29xxnand:0x00002000@0x00004000(uboot),0x00002000@0x00006000(trust),...
```

### 4.3 GPT 分区对齐要求

- 起始地址: 32KB (64 sectors) 对齐
- 分区大小: 32KB 整数倍
- sparse 格式镜像的分区: 建议 4MB 对齐

## 5. ENV 环境变量

### 5.1 ENV 存储

| 配置 | 说明 |
|------|------|
| `CONFIG_ENV_IS_IN_MMC` | 存储在 eMMC/SD |
| `CONFIG_ENV_IS_IN_SPI_FLASH` | 存储在 SPI Flash |
| `CONFIG_ENV_IS_NOWHERE` | 仅在 DDR 中 (默认) |

**存储偏移**: 0x3F8000，大小 0x8000 (32KB)

### 5.2 核心接口

```c
char *env_get(const char *name);
int env_set(const char *name, const char *value);
int env_load(void);    // 从存储加载
int env_save(void);    // 保存到存储
```

### 5.3 ENVF (Environment Fragment)

ENVF 是 RK 扩展的环境变量白名单机制:
- `CONFIG_ENVF_LIST`: 定义允许的 ENV 变量白名单
- 只有在白名单中的变量才会在 `env_update` 时被更新
- 可通过 `./make.sh env` 生成 `fw_printenv` 工具用于用户空间读写

## 6. FIT 固件格式

### 6.1 概念

FIT (Flattened Image Tree) 是 U-Boot 主推的新固件格式:
- 使用 `.its` 文件 (DTS 语法) 描述 → `mkimage` 生成 `.itb` 文件
- 支持多镜像打包、SHA256 校验、RSA2048 签名、防回滚

### 6.2 镜像组成

```
uboot.img = uboot.itb × N 份 (N=2，多备份防掉电损坏)
uboot.itb = trust (ATF+OP-TEE) + u-boot.bin [+ mcu.bin]

boot.img  = boot.itb × M 份 (M=1)
boot.itb  = kernel + fdt + resource [+ ramdisk]
```

### 6.3 its 文件结构

```dts
/ {
    images {
        uboot   { data = /incbin/("u-boot-nodtb.bin"); load = <0x00200000>; ... };
        atf@1   { data = /incbin/("bl31.bin"); type = "firmware"; ... };
        optee@1 { data = /incbin/("bl32.bin"); os = "op-tee"; ... };
        fdt@1   { data = /incbin/("rk3568-evb.dtb"); type = "flat_dt"; ... };
    };
    configurations {
        default = "config@1";
        config@1 {
            firmware = "atf@1";
            loadables = "uboot", "atf@2", "optee@1";
            fdt = "fdt@1";
            signature { algo = "sha256,rsa2048"; key-name-hint = "dev"; };
        };
    };
};
```

### 6.4 FIT 安全启动

**校验链**: Maskrom → 校验 Loader(SPL) → SPL 校验 uboot.img → U-Boot 校验 boot.img

**密钥准备**:
```bash
mkdir -p keys
# 使用 rk_sign_tool 生成 RSA2048 密钥对
../rkbin/tools/rk_sign_tool kk --bits 2048 --out .
cp privateKey.pem keys/dev.key && cp publicKey.pem keys/dev.pubkey
openssl req -batch -new -x509 -key keys/dev.key -out keys/dev.crt
```

**编译签名固件**:
```bash
# 非安全启动
./make.sh rv1126 --spl-new
# 安全启动 + 防回滚
./make.sh rv1126 --spl-new --boot_img boot.img --recovery_img recovery.img \
    --rollback-index-uboot 10 --rollback-index-boot 12
# 烧写 key hash 到 OTP
./make.sh rv1126 --spl-new --boot_img boot.img --burn-key-hash
```

**固件解包/替换**:
```bash
./scripts/fit-unpack.sh -f boot.img -o out/     # 解包
./scripts/fit-repack.sh -f uboot.img -d out/    # 替换子固件
./scripts/fit-resign.sh -f fit/uboot.itb -s uboot.sig  # 重签名
```

> 深入了解请查阅 `references/boot_flow_fit.md`

## 7. AB 系统

### 7.1 数据结构

AB 数据 (AvbABData) 存储在 **misc 分区偏移 2KB**:

| 字段 | 说明 |
|------|------|
| `magic` | "\0AB0" |
| `slots[2]` | 两个 slot 的引导信息 |
| `last_boot` | 上次成功启动的 slot (0=A, 1=B) |
| `crc32` | CRC 校验 |

AvbABSlotData:

| 字段 | 说明 |
|------|------|
| `priority` | 0=不可启动, 1~15 优先级 |
| `tries_remaining` | 剩余尝试次数 (最大 7) |
| `successful_boot` | 1=成功启动过 |
| `is_update` | 1=正在升级 |

### 7.2 两种引导模式

| 模式 | 优点 | 缺点 |
|------|------|------|
| successful_boot | 正常启动后不回退旧版本 | 存储异常时反复重启 |
| reset_retry | 保持 retry 机制应对存储异常 | 可能回退到旧版本 |

### 7.3 U-Boot 配置

```
CONFIG_AVB_LIBAVB=y
CONFIG_AVB_LIBAVB_AB=y
CONFIG_AVB_LIBAVB_ATX=y
CONFIG_AVB_LIBAVB_USER=y
CONFIG_RK_AVB_LIBAVB_USER=y
CONFIG_ANDROID_AB=y          # 启用 A/B
CONFIG_ANDROID_AVB=y         # 启用 AVB 校验
```

## 8. 升级方案

### 8.1 Fastboot 常用命令

```bash
fastboot flash boot boot.img        # 烧写分区
fastboot erase userdata              # 擦除分区
fastboot getvar all                  # 获取设备信息
fastboot set_active _a               # 设置活跃 slot
fastboot reboot                      # 重启
fastboot oem at-lock-vboot           # 锁定设备
fastboot oem at-unlock-vboot         # 解锁设备
fastboot oem format                  # 重新格式化分区
```

### 8.2 SD 卡启动/升级

4 种 SD 卡类型:
1. **普通卡**: 无特殊标记
2. **升级卡**: IDB flag=0，用于固件升级
3. **启动卡**: IDB flag=1，从 SD 卡启动系统
4. **修复卡**: IDB flag=2，用于修复系统

制作工具: **SDDiskTool** (Windows)

### 8.3 TFTP 升级

```bash
# U-Boot 命令行中:
tftpflash 0x20000000 uboot.img uboot
tftpflash 0x20000000 boot.img boot
tftpflash 0x20000000 rootfs.img rootfs
```

配置要求: `CONFIG_DM_ETH=y`, 设好 `CONFIG_IPADDR`/`CONFIG_SERVERIP`

### 8.4 Linux OTA 升级 (updateEngine)

```bash
# Recovery 模式:
updateEngine --image_url=/userdata/update.img --misc=update --reboot

# Linux A/B 模式:
updateEngine --image_url=/userdata/update_ota.img --update --reboot
```

## 9. 驱动模块速查

> 详细驱动配置和接口请查阅 `references/uboot_drivers_debug.md`

### 9.1 常用驱动 CONFIG 速查

| 模块 | 关键 CONFIG |
|------|------------|
| Display | `CONFIG_DRM_ROCKCHIP`, logo.bmp/logo_kernel.bmp 在 resource.img |
| PMIC | `CONFIG_PMIC_RK8XX`, `regulator-init-microvolt`, `regulator-boot-on` |
| Clock | `rkclk_init()` → `clk_set_defaults()`, CPU 提频: APLL/SCMI CLK |
| Storage | `CONFIG_MMC_DW_ROCKCHIP` (eMMC/SD), `CONFIG_MTD` (Nand/Nor) |
| USB | DWC2/DWC3 gadget (rockusb), Host (OHCI/EHCI/xHCI) |
| Ethernet | `CONFIG_DWC_ETH_QOS`, DHCP/PING/TFTP 命令 |
| Crypto | `CONFIG_DM_CRYPTO`, v1/v2 SHA/RSA |
| UART | 串口替换: 单路替换 (5 步) / 全局替换 (ddrbin_tool + CONFIG_ROCKCHIP_PRELOADER_SERIAL) |
| Vendor Storage | `vendor_storage_read/write`，4 分区轮转机制 |
| Watchdog | `wdt_start()`, `wdt_stop()`, `wdt_reset()` |

### 9.2 Display (开机 Logo)

- Logo 文件: `logo.bmp` (U-Boot 阶段) + `logo_kernel.bmp` (Kernel 阶段)
- 存放位置: resource.img 中，或独立 LOGO 分区 (支持动态更新)
- BMP 格式: 8bit 或 24bit，不支持压缩

## 10. 调试方法

### 10.1 常用调试命令

```bash
# 内存读写
md.l 0xff770000 10          # 读内存
mw.l 0xff770000 0x12345678  # 写内存

# iomem (DTS compatible 自动解析)
iomem rockchip,rk3399-grf 0 0x10

# I2C
i2c dev 0                   # 选择 I2C 总线
i2c md 0x1b 0x00 0x10       # 读寄存器
i2c mw 0x1b 0x00 0x55       # 写寄存器

# GPIO
gpio status -a              # 查看所有 GPIO 状态
gpio set GPIO1_A0           # 设置 GPIO 输出高
gpio input GPIO1_A0         # 读取 GPIO 输入

# MMC
mmc info                    # 查看 eMMC/SD 信息
mmc dev 0                   # 选择 mmc 设备
mmc read 0x20000000 0 0x10  # 读 sector

# FDT
fdt addr $fdt_addr_r        # 设置 DTB 地址
fdt print                   # 打印完整 DTB

# DM 框架
dm tree                     # 查看设备-驱动绑定树
dm uclass                   # 查看 uclass 列表
```

### 10.2 开机时间分析

```
CONFIG_BOOTSTAGE_PRINTF_TIMESTAMP=y    # 每行打印加相对时间戳
# initcall 分析: 修改 initcall_run_list() 中 debug() 为 printf()
```

### 10.3 系统 Hang 调试

```
CONFIG_ROCKCHIP_DEBUGGER=y   # 系统 hang 时每 5 秒自动 dump 信息
```

### 10.4 Stacktrace 解析

```bash
# 在 U-Boot 根目录执行:
./scripts/stacktrace.sh u-boot <paste_backtrace_here>
```

### 10.5 固件校验

```
CONFIG_ROCKCHIP_CRC=y    # RK 格式固件 CRC 校验
# Android 格式固件: HASH 校验
```

### 10.6 开机信息关键行解读

```
U-Boot 2017.09-03033-g81b79f7-dirty   # 版本 + commit + 编译时间
Model: Rockchip RK3399 Evaluation Board  # U-Boot DTS model
PreSerial: 2                           # 串口号 (UART2)
DRAM: 2 GiB                           # DDR 容量
Relocation Offset is: 7dbe2000         # 代码重定位地址
dwmmc@fe320000: 1, sdhci@fe330000: 0  # 存储设备
Bootdev(atags): mmc 0                 # 启动介质 (miniloader 传参)
MMC0: HS400, 150Mhz                   # eMMC 工作模式
PartType: EFI                         # GPT 分区表
boot mode: normal                     # 启动模式
DTB: rk-kernel.dtb                    # Kernel DTB 加载成功
PMIC: RK818 (on=0x20 off=0x40)        # PMIC 上电/断电原因
Total: 367.128 ms                     # U-Boot 阶段耗时
Starting kernel ...                   # 跳转到 Kernel
```

## 10.7 快速开机 / 充电动画 / AMP

→ 详细内容见 `references/boot_flow_fit.md` §4 和 `references/uboot_drivers_debug.md`

**快速开机 (Thunder Boot)**: 适用于 RV1126/RV1106 等 IPC 平台, 目标 < 500ms 出图。
核心: TPL/SPL 阶段提前初始化 Camera+ISP, Kernel 接管后无缝衔接。

```bash
# 使用 thunder boot config fragment:
./make.sh rv1126-emmc-tb          # 叠加 rv1126-emmc-tb.config
```

**充电动画**: 低电量开机时 U-Boot 拦截并显示充电 UI (charge_0.bmp~charge_5.bmp), 电池电量达标后继续开机。

**AMP (多核异构)**: RK3568/RK3588 可将部分 CPU 核心分配给 RTOS, FIT 打包 amp.img (MCU 固件)。

## 11. 常见问题排查

### 11.1 不开机 / 卡在 Trust

- 检查 trust 打印的 **U-Boot 启动地址** (64 位: 0x200000, 32 位: 0x60000000)
- 确认 uboot.img、trust.img 固件是否匹配
- 检查 DDR 容量是否正确传递

### 11.2 MMC 初始化失败

```
# CMD0 失败: 检查硬件连接
# CMD8 失败: 检查安全相关配置
# CMD18 失败: 检查电源/电压/时钟配置
```

### 11.3 Kernel DTB 加载失败

- 确认 resource.img 包含正确的 rk-kernel.dtb
- 检查 `CONFIG_USING_KERNEL_DTB=y`
- 确认 boot.img/recovery.img 中有 DTB

### 11.4 ENV 丢失 / 不生效

- `Using default environment`: ENV 使用默认值 (未从存储加载)
- 检查 `CONFIG_ENV_IS_IN_*` 配置
- ENVF 白名单: 确认变量在 `CONFIG_ENVF_LIST` 中

### 11.5 安全启动校验失败

- `sha256,rsa2048:dev-`: 签名校验失败，检查密钥是否匹配
- `rollback index: X < Y`: 固件版本低于最小版本号，需更新固件
- 确认 OTP/efuse 中的 key hash 与 loader 中的公钥一致

## 12. 平台 Defconfig 速查

| 芯片 | 通用 defconfig | SPL/FIT | 备注 |
|------|---------------|---------|------|
| RK3399 | rk3399_defconfig | 否 (Miniloader) | |
| RK3288 | rk3288_defconfig | 否 (Miniloader) | |
| PX30 | px30_defconfig | 否 (Miniloader) | |
| RV1126 | rv1126_defconfig | 是 | 支持快速开机 (tb configs) |
| RK3568 | rk3568_defconfig | 是 | |
| RK3566 | rk3566.config | 是 | 基于 rk3568_defconfig |
| RK3588 | rk3588_defconfig | 是 | |
| RV1106 | rv1106_defconfig | 是 | 支持快速开机 |
| RK3528 | rk3528_defconfig | 是 | |
| RK3562 | rk3562_defconfig | 是 | |

## 13. Trust 概要

- **64 位平台**: ARM Trusted Firmware (BL31) + OP-TEE OS (BL32)
- **32 位平台**: 仅 OP-TEE OS
- **运行内存**: ATF 在 DRAM 0~2MB, OP-TEE 在 132M~148M
- **功能**: PSCI (CPU 电源管理)、Secure Monitor、安全信息配置、安全数据保护
- **DTS 使能**: 添加 `psci` 节点 + CPU 节点 `enable-method = "psci"`
- **PANIC 识别**: ATF 打印 `INFO:` 前缀, OP-TEE 打印 `INF [0x0] TEE-CORE:` 前缀

## 14. 工具链速查

| 工具 | 功能 |
|------|------|
| `trust_merger` | 打包 bl30/bl31/bl32 → trust.img |
| `boot_merger` | 打包 miniloader + ddr + usbplug → loader |
| `loaderimage` | 打包 u-boot.bin → uboot.img (传统方案) |
| `resource_tool` | 打包资源文件 → resource.img |
| `mkimage` | 生成 FIT (itb) 固件 / IDBLOCK 格式 |
| `stacktrace.sh` | 解析 U-Boot abort/dump_stack 调用栈 |
| `SDDiskTool` | Windows SD 卡启动盘制作工具 |
| `rk_sign_tool` | RSA 密钥生成 + loader 签名 |
| `fit-unpack.sh` | FIT 固件解包 |
| `fit-repack.sh` | FIT 固件替换子固件 |
| `fit-resign.sh` | FIT 固件重签名 (远程签名) |
| `buildman` | 批量编译所有平台验证兼容性 |
| `patman` | Patch 格式化 + checkpatch + 提交 upstream |

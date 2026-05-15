# Boot Flow、FIT 格式与安全启动详解

## 1. 启动流程详解

### 1.1 U-Boot proper 初始化流程

```
board_init_f()
  ├── init_sequence_f[]    # 前初始化序列
  │   ├── serial_init()
  │   ├── dram_init()
  │   └── ...
  └── relocate_code()      # 代码重定位到 DDR 高端

board_init_r()
  ├── init_sequence_r[]    # 后初始化序列
  │   ├── board_init()
  │   │   ├── init_kernel_dtb()    # 加载 Kernel DTB
  │   │   ├── clks_probe()         # 时钟初始化
  │   │   ├── regulators_enable_boot_on()  # 使能必须上电的 regulator
  │   │   └── dvfs_init()          # DVFS 初始化
  │   ├── board_late_init()
  │   │   ├── setup_boot_mode()    # 解析启动模式 (normal/loader/fastboot...)
  │   │   ├── charge_display()     # 充电/低电检测
  │   │   └── rockchip_show_logo() # 显示开机 LOGO
  │   └── run_main_loop()         # 进入启动循环
  └── boot_android / bootrkp / distro_bootcmd
```

### 1.2 SPL 启动流程 (FIT 方案)

```
board_init_f()
  ├── spl_early_init()     # 早期初始化
  ├── preloader_console_init()  # 串口初始化
  └── spl_board_init()     # Board 级初始化

board_init_r()
  └── spl_boot_device()    # 根据 u-boot,spl-boot-order 确定启动设备
      ├── SPL_BOOT_SPI_FLASH
      ├── SPL_BOOT_SDIO_0/1
      └── SPL_BOOT_EMMC
  └── spl_load_image()     # 加载 uboot.itb (包含 trust + u-boot)
      └── 跳转 ATF → U-Boot proper
```

### 1.3 TPL 启动流程

```
board_init_f()
  ├── spl_early_init()
  ├── sdram_init()         # DDR 初始化 (核心功能)
  └── 跳转 SPL
```

### 1.4 SPL 存储优先级

通过 DTS `u-boot,spl-boot-order` 属性指定:

```dts
chosen {
    u-boot,spl-boot-order = &sdmmc, &sfc, &nandc, &sdhci;
    // sd卡 > spi nor > spi nand > emmc
};
```

### 1.5 ATAGS 传参机制

SPL 和 Miniloader 通过 ATAGS（0x200000 起始）向 U-Boot 传递参数:
- **ATAG_SERIAL**: 串口信息
- **ATAG_BOOTDEV**: 启动设备类型
- **ATAG_DDR_MEM**: DDR 信息
- **ATAG_TOS_MEM**: Trust 内存信息
- **ATAG_RAM_PARTITION**: 内存分区信息

## 2. FIT 格式深入

### 2.1 FIT 结构

```
itb 文件结构:
┌──────────────────────┐
│ fdt_header (FDT blob)│  → 包含 /images 和 /configurations 的元数据
├──────────────────────┤
│ image 1 (u-boot.bin) │  → 外部数据区域
│ image 2 (bl31.bin)   │
│ image 3 (bl32.bin)   │
│ image 4 (xxx.dtb)    │
│ ...                  │
└──────────────────────┘
```

### 2.2 its 各字段含义

```dts
images {
    uboot {
        data = /incbin/("u-boot-nodtb.bin");   // 二进制数据
        type = "standalone";                     // 类型
        arch = "arm64";                          // 架构
        os = "U-Boot";                           // 操作系统
        compression = "none";                    // 压缩方式 (支持 gzip)
        load = <0x00200000>;                     // 加载地址
        hash { algo = "sha256"; };               // 哈希算法
    };
};
configurations {
    default = "config@1";
    config@1 {
        firmware = "atf@1";                      // 首个执行的固件
        loadables = "uboot", "optee@1";          // 其余需加载的固件
        fdt = "fdt@1";                           // DTB
        signature {
            algo = "sha256,rsa2048";             // 签名算法
            key-name-hint = "dev";               // 密钥名称
            sign-images = "firmware", "loadables", "fdt";  // 签名范围
            padding = "pkcs-v2.1";               // 填充方式 (PSS)
        };
    };
};
```

### 2.3 uboot.img vs boot.img 对比

| 属性 | uboot.img | boot.img |
|------|-----------|----------|
| 内容 | trust (ATF+OPTEE) + u-boot.bin + [mcu] | kernel + fdt + resource + [ramdisk] |
| 备份数 | N=2 (防掉电) | M=1 |
| itb 来源 | uboot.its | boot.its |
| 校验者 | SPL 校验 (CONFIG_SPL_FIT_SIGNATURE) | U-Boot 校验 (CONFIG_FIT_SIGNATURE) |
| 生成方式 | `./make.sh` 自动生成 | 需外部工具 (如 mkbootimg) |

### 2.4 MCU 固件配置 (AMP)

通过 RKTRUST ini 文件中 MCU 段配置:

```ini
[MCU]
NUM=1
MCUIMAGE0=MCU/rk3568_mcu_rv32m1_full.bin
MCU0_LOAD_ADDR=0xFFE00000
MCU0_RUN=0
MCU0_SLEEP=0
MCU0_ARCH=1
MCU0_NAME=mcu0
```

FIT 中对应 its：
```dts
mcu0 {
    data = /incbin/("rk3568_mcu_rv32m1_full.bin");
    type = "standalone";
    arch = "riscv";
    compression = "none";
    load = <0xFFE00000>;
};
```

### 2.5 压缩支持

its 中添加 `compression = "gzip"`:
```dts
optee@1 {
    data = /incbin/("bl32.bin.gz");
    compression = "gzip";
    load = <0x08400000>;
    ...
};
```

## 3. 安全启动详解

### 3.1 校验链完整流程

```
BootROM
  └── 校验 idbloader (SPL)        [BootROM 根密钥]
      └── SPL 校验 uboot.img      [SPL 内嵌公钥]
          ├── 校验 trust (ATF+OPTEE)
          └── 校验 u-boot.bin
              └── U-Boot 校验 boot.img [U-Boot 内嵌公钥]
                  ├── 校验 kernel
                  ├── 校验 FDT
                  └── 校验 ramdisk
                      └── Kernel dm-verify rootfs
```

### 3.2 密钥体系

**FIT 签名**: SHA256 + RSA2048 + PKCS v2.1 (PSS padding)
- `keys/dev.key`: 私钥 (签名用)
- `keys/dev.pubkey`: 公钥 (内嵌到固件)
- `keys/dev.crt`: X509 证书

**AVB 密钥** (Android 验证启动):
- **PRK** (Product Root Key): 根密钥，hash 烧写入 OTP
- **PIK** (Product Intermediate Key): 中间密钥
- **PSK** (Product Signing Key): 签名密钥
- **PUK** (Product Unlock Key): 解锁密钥

### 3.3 签名编译完整步骤

```bash
# 步骤 1: 生成密钥
mkdir -p keys
../rkbin/tools/rk_sign_tool kk --bits 2048 --out .
cp privateKey.pem keys/dev.key
cp publicKey.pem keys/dev.pubkey
openssl req -batch -new -x509 -key keys/dev.key -out keys/dev.crt

# 步骤 2: 配置 defconfig
CONFIG_FIT_SIGNATURE=y         # U-Boot 校验 boot.img
CONFIG_SPL_FIT_SIGNATURE=y     # SPL 校验 uboot.img
CONFIG_FIT_ROLLBACK_PROTECT=y  # 防回滚

# 步骤 3: 编译签名固件
./make.sh rk3568 --spl-new \
    --boot_img boot.img \
    --recovery_img recovery.img \
    --rollback-index-uboot 1 \
    --rollback-index-boot 1

# 步骤 4 (可选): 烧写 key hash 到 OTP
./make.sh rk3568 --spl-new --burn-key-hash
```

### 3.4 远程签名流程

用于密钥不出服务器的安全场景:

```
开发机                              签名服务器
  │                                     │
  ├── 生成临时密钥编译固件                │
  ├── 提取 data2sign 文件  ──────────→  │
  │                                     ├── 使用正式私钥签名
  │  ←──────────  签名文件             ←┤
  ├── fit-resign.sh 替换签名            │
  └── 最终签名固件                       │
```

```bash
# 开发机: 提取待签名数据
./scripts/fit-unpack.sh -f uboot.img -o out/
# (发送 out/ 中的 data2sign 文件给服务器)

# 签名服务器: 签名
openssl dgst -sha256 -sign real.key -out uboot.sig data2sign

# 开发机: 重签名
./scripts/fit-resign.sh -f fit/uboot.itb -s uboot.sig
```

### 3.5 AVB Secure Boot

**配置要求**:
```
CONFIG_AVB_LIBAVB=y
CONFIG_AVB_LIBAVB_AB=y
CONFIG_AVB_LIBAVB_ATX=y
CONFIG_AVB_LIBAVB_USER=y
CONFIG_RK_AVB_LIBAVB_USER=y
CONFIG_ANDROID_AVB=y
CONFIG_OPTEE_V1=y    # 或 CONFIG_OPTEE_V2=y
```

**AVB 密钥生成**:
```bash
# 生成 RSA 4096 位密钥
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 \
    -outform PEM -out testkey_atx_prk.pem

# 生成各级证书
avbtool make_atx_certificate --output=atx_prk_certificate.bin \
    --subject=atx_product_id.bin --subject_key=testkey_atx_prk.pem \
    --subject_is_intermediate_authority --subject_key_version 42 \
    --authority_key=testkey_atx_prk.pem

avbtool make_atx_permanent_attributes --output=permanent_attributes.bin \
    --product_id=atx_product_id.bin \
    --root_authority_key=testkey_atx_prk.pem

avbtool make_atx_metadata --output=atx_metadata.bin \
    --intermediate_key_certificate=atx_pik_certificate.bin \
    --product_key_certificate=atx_psk_certificate.bin
```

**固件签名**:
```bash
# boot.img 签名
avbtool add_hash_footer --image boot.img --partition_size 33554432 \
    --partition_name boot --key testkey_atx_psk.pem \
    --algorithm SHA256_RSA4096

# system.img 签名
avbtool add_hashtree_footer --image system.img --partition_size 536870912 \
    --partition_name system --key testkey_atx_psk.pem \
    --algorithm SHA256_RSA4096

# 生成 vbmeta.img
avbtool make_vbmeta_image --output vbmeta.img \
    --include_descriptors_from_image boot.img \
    --include_descriptors_from_image system.img \
    --key testkey_atx_psk.pem --algorithm SHA256_RSA4096 \
    --public_key_metadata atx_metadata.bin
```

### 3.6 锁定/解锁设备

```bash
# 锁定
fastboot oem at-lock-vboot

# 解锁 (需要 PUK 签名的 unlock credential)
avbtool make_atx_unlock_credential \
    --output=unlock_credential.bin \
    --intermediate_key_certificate=atx_pik_certificate.bin \
    --unlock_key_certificate=atx_puk_certificate.bin \
    --challenge=$(fastboot oem at-get-vboot-unlock-challenge | awk '{print $5}') \
    --unlock_key=testkey_atx_puk.pem

fastboot stage unlock_credential.bin
fastboot oem at-unlock-vboot
```

## 4. 快速开机 (Fast Boot / Thunder Boot)

### 4.1 概述

适用于需要快速启动 Camera 的 IPC 场景 (如 RV1126)，跳过 U-Boot proper 阶段:

```
Maskrom → ddr bin → SPL → Trust → 直接启动 Kernel
```

### 4.2 SPL 关键配置

```
CONFIG_SPL_KERNEL_BOOT=y           # SPL 直接引导 Kernel
CONFIG_SPL_BLK_READ_PREPARE=y      # 预加载 (提前读取 ramdisk)
CONFIG_SPL_MISC_DECOMPRESS=y       # 使用硬件解压
```

### 4.3 预加载配置 (its)

```dts
ramdisk {
    data = /incbin/("ramdisk.gz");
    type = "ramdisk";
    compression = "gzip";
    load = <0x2800000>;
    preload = <1>;         // 使能预加载
    decomp-async = <1>;    // 异步解压
};
```

### 4.4 Kernel 配置

```
CONFIG_ROCKCHIP_THUNDER_BOOT=y
CONFIG_ROCKCHIP_THUNDER_BOOT_MMC=y     # eMMC 平台
CONFIG_ROCKCHIP_THUNDER_BOOT_SFC=y     # SPI Nor 平台
```

DTS 节点:
```dts
thunder-boot-mmc {
    compatible = "rockchip,thunder-boot-mmc";
    reg = <0xffc50000 0x4000>;  // eMMC 寄存器基址
};
```

## 5. Kernel 参数传递

### 5.1 Cmdline 来源 (按优先级)

1. **parameter.txt** `CMDLINE:` 行
2. **Kernel DTS** `/chosen/bootargs`
3. **U-Boot 动态追加** (androidboot.* 系列)
4. **boot.img / recovery.img header** cmdline 字段

### 5.2 U-Boot 动态追加的 Cmdline 参数

| 参数 | 示例 | 来源 |
|------|------|------|
| `storagemedia=` | `emmc` / `sd` / `nand` | 启动介质 |
| `androidboot.mode=` | `normal` / `charger` | 启动模式 |
| `androidboot.slot_suffix=` | `_a` / `_b` | AB 系统当前 slot |
| `androidboot.serialno=` | vendor storage SN | 序列号 |
| `androidboot.mac=` | vendor storage MAC | MAC 地址 |

### 5.3 Memory Fixup

U-Boot 根据实际 DDR 容量自动修正 Kernel DTB 的 `memory` 节点:

```dts
memory {
    device_type = "memory";
    reg = <0x0 0x0 0x0 0x80000000>;  // U-Boot 自动修正
};
```

## 6. Vendor Storage

### 6.1 接口

```c
int vendor_storage_read(u16 id, void *buf, u16 size);
int vendor_storage_write(u16 id, void *buf, u16 size);
```

### 6.2 常用 ID

| ID | 用途 |
|----|------|
| VENDOR_SN_ID (1) | 序列号 |
| VENDOR_WIFI_MAC_ID (2) | WiFi MAC |
| VENDOR_LAN_MAC_ID (3) | Ethernet MAC |
| VENDOR_BT_MAC_ID (4) | Bluetooth MAC |
| VENDOR_HDCP_14_HDMI_ID | HDCP 1.4 key |
| VENDOR_HDCP_22_HDMI_ID | HDCP 2.2 key |

### 6.3 读写机制

- 4 个分区 (partition0~3) 轮转写入
- 每个分区 64KB
- 写入时选择最旧的分区
- 读取时选择最新有效的分区
- 支持从 U-Boot 命令行: `vendor_storage read/write`

## 7. DTBO/DTO (Device Tree Overlay)

### 7.1 原理

将基础 DTB 和覆盖 DTBO 分离，运行时动态合并:
```
base.dtb + overlay.dtbo → 合并后的 DTB
```

### 7.2 U-Boot 实现

`board_select_fdt_index()` 函数根据硬件配置选择 DTBO:
- 基于 GPIO 检测
- 基于 ADC 值检测
- 基于 Vendor Storage 信息

### 7.3 HW-ID DTB (多 DTB 检测)

```bash
# 使用 mkmultidtb.py 生成多 DTB 镜像
python3 scripts/mkmultidtb.py -d dtbs/ -o multi.dtb -c hwid.json

# hwid.json 格式:
{
    "dtbs": [
        {"file": "board_revA.dtb", "hwid": [{"type": "gpio", "net": "GPIO0_A3", "value": 0}]},
        {"file": "board_revB.dtb", "hwid": [{"type": "gpio", "net": "GPIO0_A3", "value": 1}]}
    ]
}
```

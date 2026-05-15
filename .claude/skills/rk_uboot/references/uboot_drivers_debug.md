# U-Boot 系统模块、驱动与调试详解

## 1. BCB (Bootloader Control Block)

### 1.1 BCB 位置

| Android 版本 | misc 分区偏移 |
|-------------|---------------|
| ≥ Android 10 | 偏移 0 |
| < Android 10 | 偏移 16KB |

### 1.2 BCB 结构

```c
struct bootloader_message {
    char command[32];     // "boot-recovery", "boot-fastboot", ""
    char status[32];
    char recovery[768];   // recovery 参数 "--update_package=xxx"
    char stage[32];
    char reserved[224];
};
```

### 1.3 U-Boot 启动模式解析

`setup_boot_mode()` 读取 BCB 确定启动模式:
- `command = ""` → 正常启动
- `command = "boot-recovery"` → 进入 recovery
- `command = "boot-fastboot"` → 进入 fastboot
- 也通过 Loader key / reboot 命令参数设置

## 2. ENV/ENVF 框架详解

### 2.1 ENV 搜索与保存

```
CONFIG_ENV_IS_IN_MMC=y        # eMMC/SD 卡
CONFIG_ENV_IS_IN_SPI_FLASH=y  # SPI Flash
CONFIG_ENV_IS_IN_FAT=y        # FAT 文件系统
CONFIG_ENV_IS_NOWHERE=y       # 仅内存 (默认)
```

偏移与大小:
```
CONFIG_ENV_OFFSET=0x3F8000
CONFIG_ENV_SIZE=0x8000         # 32KB
CONFIG_ENV_OFFSET_REDUND       # 冗余 ENV 偏移 (防掉电)
```

### 2.2 ENV 关键函数

```c
// 基本读写
char *env_get(const char *name);
int env_set(const char *name, const char *value);

// 存储操作
int env_load(void);    // 从存储介质加载 ENV
int env_save(void);    // 保存 ENV 到存储介质

// RK 扩展
void env_update(const char *name, const char *value);
void env_update_filter(const char *name, const char *old, const char *new_val);
```

### 2.3 ENVF (ENV Fragment) 白名单

```
CONFIG_ENVF=y
CONFIG_ENVF_LIST="bootcmd bootargs ethaddr"   # 白名单列表
```

规则:
- 只有在 `CONFIG_ENVF_LIST` 中的变量才能被 `env_update()` 更新
- 防止非预期的 ENV 变量被修改
- `fw_printenv` / `fw_setenv` 在 Linux 用户空间操作 ENV

生成 fw_printenv:
```bash
./make.sh env
# 产物: tools/env/fw_printenv (Linux 用户空间工具)
```

## 3. 存储驱动架构

### 3.1 BLK 层抽象

```
应用层: bootrkp / boot_android / distro
    ↕
BLK 层: blk_dread() / blk_dwrite()
    ↕
驱动层:
├── MMC (DW MMC / SDHCI): eMMC, SD卡
├── MTD_BLK: SPI Nand / SLC Nand / SPI Nor
└── rknand / rkflash: 传统闭源 NAND 驱动
```

### 3.2 存储设备类型映射

| devtype | 设备 | 说明 |
|---------|------|------|
| `mmc 0` | eMMC | 通常 dev 0 |
| `mmc 1` | SD卡 | 通常 dev 1 |
| `mtd 0` | SPI Nand | 统一 MTD 接口 |
| `mtd 1` | SLC Nand | 统一 MTD 接口 |
| `mtd 2` | SPI Nor | 统一 MTD 接口 |
| `rknand 0` | NAND (闭源) | 旧平台 |
| `rkflash 0` | NAND/Nor (闭源) | 旧平台 |

### 3.3 MTD 块设备 (SPL 统一接口)

```
CONFIG_SPL_MTD_SUPPORT=y
# 支持的 Flash 类型:
#   SPI Nand: CONFIG_NAND + CONFIG_MTD_SPI_NAND
#   SLC Nand: CONFIG_NAND + CONFIG_NAND_ROCKCHIP
#   SPI Nor:  CONFIG_SPI_FLASH + CONFIG_MTD_SPI_NOR
```

## 4. Display 驱动 (开机 Logo)

### 4.1 Logo 文件

| 文件 | 阶段 | 说明 |
|------|------|------|
| `logo.bmp` | U-Boot 显示 | 第一个可见画面 |
| `logo_kernel.bmp` | Kernel 显示 | Kernel 接替显示 |
| `charge_X.bmp` | 充电动画 | X = 0~5 |

- 格式: BMP 8-bit 或 24-bit，**不支持压缩**
- 存放: resource.img 打包 或 LOGO 分区 (支持 FAT 文件系统动态更新)

### 4.2 显示接口配置

```
CONFIG_DRM_ROCKCHIP=y
CONFIG_DRM_ROCKCHIP_DW_MIPI_DSI=y    # MIPI DSI
CONFIG_DRM_ROCKCHIP_LVDS=y           # LVDS
CONFIG_DRM_ROCKCHIP_DW_HDMI=y        # HDMI
CONFIG_DRM_ROCKCHIP_ANALOGIX_DP=y    # DP/eDP
CONFIG_DRM_ROCKCHIP_RGB=y            # RGB
```

### 4.3 充电显示

当低电量开机时进入充电动画模式:
```
charge_display() → 检测电池电量 → 低于阈值 → 显示充电动画 → 等待充电
```

## 5. Clock 驱动

### 5.1 时钟初始化

`rkclk_init()` → `clk_set_defaults()` 使用 DTS 默认频率

### 5.2 CPU 提频 (3 种方式)

| 方式 | 适用平台 | 方法 |
|------|---------|------|
| 普通 APLL 提频 | PX30, RK3326, RK3399, RK3288 | 修改 PLL 直接提频 |
| SCMI CLK 提频 | RK3568, RK3566 | 通过 ARM SCMI 接口在 OP-TEE 中提频 |
| 自动提频 | 支持 `cpu-supply` | 自动查找 opp-table 匹配电压提频 |

### 5.3 SCMI 提频配置

```dts
// 修改 cpu 时钟频率
rk3568.dtsi: arm-clk = <xxx>;  // 目标频率 (Hz)
```

## 6. UART 串口配置

### 6.1 单路串口替换 (5 步)

1. 修改 `RKXXXX.dtsi` 中 `chosen/stdout-path` 和 `fiq-debugger/rockchip,serial`
2. 修改 `rkXXXX_common.h` 中 `CONFIG_DEBUG_UART_BASE` 和 `CONFIG_DEBUG_UART_CHANNEL`
3. U-Boot defconfig 中修改 `CONFIG_DEBUG_UART_BASE`
4. 用 `ddrbin_tool` 修改 ddr bin 的串口 (新平台无需)
5. 修改 kernel DTS 的 `stdout-path`

### 6.2 全局串口替换

```
CONFIG_ROCKCHIP_PRELOADER_SERIAL=y   # 自动继承 pre-loader 的串口配置
```

配合 rkbin tools 修改 ddr bin 串口号:
```bash
../rkbin/tools/ddrbin_tool -g rk3568_ddr_xxx.bin  # 查看当前配置
../rkbin/tools/ddrbin_tool -uart 4 rk3568_ddr_xxx.bin  # 修改为 UART4
```

## 7. USB 驱动

### 7.1 Device (Gadget)

```
CONFIG_USB_GADGET=y
CONFIG_USB_GADGET_DWC2_OTG=y    # DWC2 (USB 2.0)
CONFIG_USB_GADGET_DOWNLOAD=y
CONFIG_USB_FUNCTION_ROCKUSB=y    # Rockusb 协议
CONFIG_USB_FUNCTION_FASTBOOT=y   # Fastboot 协议
CONFIG_USB_FUNCTION_MASS_STORAGE=y
```

Rockusb 支持的功能: 烧写/擦除/读取 flash、读写 efuse/otp、设备信息获取

### 7.2 Host

```
CONFIG_USB_HOST=y
CONFIG_USB_OHCI_HCD=y        # USB 1.1
CONFIG_USB_EHCI_HCD=y        # USB 2.0
CONFIG_USB_XHCI_HCD=y        # USB 3.0
CONFIG_USB_STORAGE=y          # U盘启动/升级
CONFIG_USB_KEYBOARD=y         # USB 键盘
```

### 7.3 PHY 配置

```
CONFIG_PHY_ROCKCHIP_INNO_USB2=y      # USB 2.0 PHY
CONFIG_PHY_ROCKCHIP_TYPEC=y          # Type-C PHY
CONFIG_PHY_ROCKCHIP_NANENG_USB2=y    # 新平台 USB 2.0 PHY
```

## 8. PMIC/Regulator 驱动

### 8.1 配置

```
CONFIG_PMIC_RK8XX=y
CONFIG_REGULATOR_RK8XX=y
CONFIG_DM_REGULATOR_FIXED=y
CONFIG_DM_REGULATOR_GPIO=y
```

### 8.2 DTS 关键属性

```dts
regulator-xxx {
    regulator-always-on;           // 常开
    regulator-boot-on;             // U-Boot 阶段使能
    regulator-init-microvolt = <900000>;  // U-Boot 阶段初始电压
    regulator-min-microvolt = <750000>;
    regulator-max-microvolt = <1350000>;
};
```

### 8.3 Regulator 初始化流程

```
regulators_enable_boot_on()  → 遍历所有 regulator
  ├── 有 regulator-boot-on → 使能
  ├── 有 regulator-always-on → 使能
  └── 有 regulator-init-microvolt → 设置初始电压
```

## 9. PCIe / NVMe

```
CONFIG_PCI=y
CONFIG_DM_PCI=y
CONFIG_PCIE_DW_ROCKCHIP=y       # DesignWare PCIe 控制器
CONFIG_PCI_INIT_R=y
CONFIG_CMD_PCI=y
CONFIG_NVME=y                    # NVMe SSD 支持
CONFIG_BLK=y
```

## 10. 以太网 (Ethernet)

```
CONFIG_DM_ETH=y
CONFIG_DWC_ETH_QOS=y              # GMAC 控制器
CONFIG_DWC_ETH_QOS_ROCKCHIP=y
CONFIG_PHY_REALTEK=y               # PHY 驱动
CONFIG_CMD_DHCP=y
CONFIG_CMD_PING=y
CONFIG_CMD_TFTPBOOT=y
```

网络参数 (defconfig 或 ENV):
```
CONFIG_IPADDR="192.168.1.100"
CONFIG_SERVERIP="192.168.1.1"
CONFIG_GATEWAYIP="192.168.1.1"
CONFIG_ETHADDR="02:00:00:00:00:01"
```

## 11. OP-TEE Client 接口

### 11.1 V1/V2 区别

| 特性 | V1 (CONFIG_OPTEE_V1) | V2 (CONFIG_OPTEE_V2) |
|------|------|------|
| 接口 | SMC 直接调用 | libteec (GlobalPlatform API) |
| 安全数据存储 | efuse/otp/rpmb | efuse/otp/rpmb + TA 扩展 |
| 适用 | 旧平台 | 新平台 (RV1126 及以后) |

### 11.2 OEM OTP 加密写入

V2 平台支持通过 TA (Trusted Application) 对 OTP 数据进行加密:
```c
// U-Boot 侧调用流程:
trusty_oem_otp_key_cipher(key_buf, key_len, cipher_buf, cipher_len);
```

## 12. 升级方案详解

### 12.1 Recovery 模式升级

```
Normal Boot → updateEngine --misc=update → 重启 → Recovery 模式 → 升级各分区 → 重启
```

```bash
# 完整 OTA 升级
updateEngine --image_url=/userdata/update.img --misc=update --reboot

# 指定分区升级 (partition bitmap)
# bit0=loader, bit1=parameter, bit2=uboot, bit3=trust, bit4=boot, ...
updateEngine --image_url=/userdata/update.img --partition=0x3FFC00 --misc=update --reboot

# 恢复出厂
updateEngine --misc=wipe_userdata --reboot
```

### 12.2 Linux A/B 模式升级

```bash
# 升级备用 slot，切换并重启
updateEngine --image_url=/userdata/update_ota.img --update --reboot

# 升级到自定义 URL
updateEngine --image_url=http://192.168.1.100:8080/update.img --update --reboot
```

### 12.3 差分 OTA 升级

```bash
# 在 PC 上生成差分包:
./tools/linux/Linux_Diff_Firmware/mk-diff-ota.sh old_firmware/ new_firmware/ diff_ota.img

# 在设备上应用:
updateEngine --image_url=/userdata/diff_ota.img --misc=update --reboot
```

### 12.4 TFTP 网络升级

手动升级:
```bash
# U-Boot CLI:
setenv ipaddr 192.168.1.100
setenv serverip 192.168.1.1
tftpflash 0x20000000 uboot.img uboot
tftpflash 0x20000000 boot.img boot
tftpflash 0x20000000 rootfs.img rootfs
reset
```

自动升级:
```c
// 修改 RKIMG_BOOTCOMMAND 宏:
#define RKIMG_BOOTCOMMAND \
    "if ping ${serverip}; then " \
    "tftpflash 0x20000000 uboot.img uboot; " \
    "tftpflash 0x20000000 boot.img boot; " \
    "fi; " \
    "boot_android ${devtype} ${devnum};"
```

ARP 超时优化: `CONFIG_ARP_TIMEOUT=200UL` (默认 5000ms)

## 13. 调试命令汇总

### 13.1 内存/IO 操作

```bash
md[.b/.w/.l] <addr> [count]          # 查看内存 (字节/半字/字)
mw[.b/.w/.l] <addr> <value> [count]  # 写内存
iomem <compatible> <offset> <size>   # 按 DTS compatible 读寄存器
```

### 13.2 设备树操作

```bash
fdt addr $fdt_addr_r                 # 设置 FDT 地址
fdt print [path [prop]]              # 打印 FDT 节点/属性
fdt list /                           # 列出根节点子节点
fdt set /chosen bootargs "..."       # 修改属性
```

### 13.3 I2C

```bash
i2c bus                              # 列出所有 I2C 总线
i2c dev <bus>                        # 选择总线
i2c probe                            # 扫描 I2C 地址
i2c md <chip> <addr>[.1/.2] <len>    # 读寄存器
i2c mw <chip> <addr>[.1/.2] <val>    # 写寄存器
```

### 13.4 DM 框架

```bash
dm tree                              # 显示设备驱动绑定树
dm uclass                            # 显示所有 uclass
dm status                            # 显示设备状态 (active/inactive)
```

### 13.5 MMC/存储

```bash
mmc info                             # 当前 MMC 设备信息
mmc dev <num> [part]                 # 切换设备
mmc list                             # 列出所有设备
mmc read <addr> <blk#> <cnt>         # 读 block
mmc write <addr> <blk#> <cnt>        # 写 block
mmc part                             # 显示分区表
```

### 13.6 GPIO

```bash
gpio status -a                       # 显示所有 GPIO 状态
gpio set <pin>                       # 输出高电平
gpio clear <pin>                     # 输出低电平
gpio input <pin>                     # 读取输入
gpio toggle <pin>                    # 翻转
```

### 13.7 时间分析

```bash
# 开启方式:
CONFIG_BOOTSTAGE=y
CONFIG_BOOTSTAGE_PRINTF_TIMESTAMP=y

# U-Boot CLI:
bootstage report                     # 显示各阶段耗时
time <command>                       # 测量命令执行时间
```

### 13.8 CRC/HASH 校验

```bash
crc32 <addr> <size>                  # CRC32 校验
md5sum <addr> <size>                 # MD5 校验
sha1sum <addr> <size>                # SHA1 校验
sha256sum <addr> <size>              # SHA256 校验
```

### 13.9 常用网络命令

```bash
dhcp                                 # DHCP 获取 IP
ping <ip>                            # Ping 测试
tftpboot <addr> <file>               # TFTP 下载文件到内存
```

## 14. 工具使用详解

### 14.1 trust_merger

```bash
# 打包 trust.img (64 位平台)
trust_merger RKTRUST/RK3399TRUST.ini
# ini 格式:
[BL30_OPTION]
SEC=1, PATH=bin/rk33/rk3399_bl30_vx.xx.bin, ADDR=0x00010000
[BL31_OPTION]
SEC=1, PATH=bin/rk33/rk3399_bl31_vx.xx.elf, ADDR=0x00010000
[BL32_OPTION]
SEC=1, PATH=bin/rk33/rk3399_bl32_vx.xx.bin, ADDR=0x08400000

# 解包
trust_merger -unpack trust.img
```

### 14.2 boot_merger

```bash
# 打包 loader
boot_merger RKBOOT/RK3399MINIALL.ini

# 解包
boot_merger -unpack rk3399_loader_vx.xx.xxx.bin
```

### 14.3 loaderimage

```bash
# 打包 uboot.img (32 位传统方案)
loaderimage --pack --uboot u-boot.bin uboot.img 0x60000000

# 打包 trust.img (32 位)
loaderimage --pack --trustos tee.bin trust.img 0x68400000

# 解包
loaderimage --unpack --uboot uboot.img uboot.bin
```

### 14.4 resource_tool

```bash
# 打包 resource.img
resource_tool rk-kernel.dtb logo.bmp logo_kernel.bmp

# 解包
resource_tool --unpack resource.img
```

### 14.5 mkimage (FIT)

```bash
# 编译 its → itb
mkimage -f uboot.its -E uboot.itb

# 查看 itb 信息
mkimage -l uboot.itb
```

### 14.6 buildman (批量编译)

```bash
# 编译所有 rockchip 平台:
tools/buildman/buildman -b test_branch -o ../build -T 8 rockchip

# 查看编译结果:
tools/buildman/buildman -sde -b test_branch rockchip
```

### 14.7 patman (补丁管理)

```bash
# 检查最近 N 个 commit:
patman -n <N> --no-check -t "your test tag"
# 生成并发送 patch:
patman -n <N>
```

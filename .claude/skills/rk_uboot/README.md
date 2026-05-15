# rk_uboot  Rockchip U-Boot 引导加载器技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_uboot` 是一个面向 Rockchip 瑞芯微 SoC 平台的 U-Boot 引导加载器 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip 平台的 U-Boot 启动流程、固件编译打包、FIT 镜像格式、SPL/TPL 开源引导、安全启动（Secure Boot/AVB）、AB 系统、分区管理、U-Boot 驱动调试、固件升级方案等问题时，AI 会自动加载本技能，提供 RK 平台特有的启动架构、rkbin 工具链、分区表配置等深度知识。

## 覆盖芯片

| 芯片 | 架构 | 启动方式 |
|------|------|---------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | SPL/TPL 或 Miniloader, FIT |
| **RK3568** | 4A55, Mali-G52 | SPL/TPL 或 Miniloader, FIT |
| **RK3566** | 4A55, Mali-G52 | SPL/TPL 或 Miniloader, FIT |
| **RK3399 / RK3399Pro** | 2A72 + 4A53, Mali-T860 | SPL/TPL 或 Miniloader |
| **PX30 / RK3326** | 4A35, Mali-G31 | SPL 或 Miniloader |
| **RK3328** | 4A53, Mali-450 | SPL/TPL 或 Miniloader |

## 功能说明

### 功能 1：启动流程与 FIT 固件

Rockchip 完整启动流程（Maskrom → Loader → Trust → U-Boot → Kernel）和 FIT 镜像打包。

**你可以这样提问：**
- "RK3588 的完整启动流程是什么？"
- "SPL/TPL 和 Miniloader 引导有什么区别？"
- "FIT 镜像 (u-boot.itb) 是怎么打包的？"
- "idbloader.img 里包含什么？怎么生成？"
- "怎么进 Maskrom 模式和 Loader 模式？"

**AI 会返回：**
- RK 平台启动流程图（BootROM → SPL → ATF → U-Boot → Kernel）
- SPL/TPL vs Miniloader 对比和选型建议
- FIT 镜像打包流程（mkimage、its 配置文件、trust.img 合并）
- idbloader 生成方法和烧写位置

### 功能 2：编译配置与驱动调试

U-Boot defconfig 定制、config fragment、驱动调试（MMC/USB/网络/显示）。

**你可以这样提问：**
- "RK3568 U-Boot 怎么编译？defconfig 用哪个？"
- "怎么在 U-Boot 里添加自定义命令？"
- "U-Boot 下 eMMC 识别不了怎么排查？"
- "U-Boot 的 kernel DTB 加载流程是什么？"
- "dm-pre-reloc 和 u-boot,dm-pre-reloc 什么时候需要加？"

**AI 会返回：**
- `./make.sh` 编译命令和 defconfig 选择
- config fragment 定制方法
- U-Boot 驱动调试方法（MMC/USB/网络/显示的 debug 开关和排查步骤）
- kernel DTB 加载机制（init_kernel_dtb、live device tree）

### 功能 3：安全启动与 AB 系统

Secure Boot（FIT 签名/AVB/防回滚）和 AB 系统启动切换。

**你可以这样提问：**
- "RK 平台怎么开启 Secure Boot？"
- "FIT 签名和 AVB 验证有什么区别？"
- "AB 系统怎么实现启动切换？"
- "防回滚 (rollback) 怎么配置？"
- "vbmeta 分区是做什么的？"

**AI 会返回：**
- Secure Boot 完整流程（KeyGen → 签名 → 烧写 → 验证链）
- FIT RSA 签名 vs AVB 验证的适用场景
- AB 系统启动逻辑（slot_a/slot_b、BCB、misc 分区、retry 机制）
- 防回滚计数器配置

### 功能 4：分区管理与固件升级

GPT 分区表、parameter 文件、OTA 升级、Recovery、TFTP / SD 卡升级方案。

**你可以这样提问：**
- "RK 的 GPT 分区表怎么配？"
- "parameter.txt 的格式说明一下"
- "怎么做 Linux OTA 升级？"
- "TFTP 网络升级怎么配置？"
- "SD 卡升级方案怎么做？SDDiskTool 怎么用？"

**AI 会返回：**
- GPT 分区表和 parameter.txt 格式详解
- 分区烧写偏移地址和大小配置
- OTA 升级方案对比（Recovery 模式 vs AB 系统 vs 差分升级）
- TFTP 升级配置步骤和命令
- SD 卡升级制作流程

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **U-Boot / uboot / bootloader / 引导 / 启动流程 / boot flow** 等关键词
- 提到 **SPL / TPL / FIT / itb / its / miniloader / idbloader** 等启动组件
- 提到 **Maskrom / Loader 模式 / rockusb / fastboot / 烧写** 等烧写概念
- 提到 **Secure Boot / AVB / vbmeta / FIT 签名 / 防回滚** 等安全启动
- 提到 **AB 系统 / slot_a / slot_b / BCB / misc 分区 / OTA** 等升级系统
- 提到 **GPT / parameter.txt / 分区表 / TFTP 升级 / SD 卡升级** 等分区管理

## 文件结构

```
rk_uboot/
├── SKILL.md                              # 主技能文件 (AI 自动加载, ~550 行)
├── README.md                             # 本说明文档 (供人阅读)
└── references/                           # 深入参考资料 (AI 按需加载)
    ├── boot_flow_fit.md                  # 启动流程详解、FIT 打包、SPL/TPL、Secure Boot/AVB、AB 系统
    └── uboot_drivers_debug.md            # U-Boot 驱动调试、分区管理、固件升级、ENV 环境变量
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 U-Boot 核心知识（启动流程、编译方法、分区概要、安全启动框架）
- **references/**：AI 根据问题按需加载。例如：
  - 用户问启动流程/FIT/安全启动 → 加载 `boot_flow_fit.md`
  - 用户问驱动调试/分区/升级 → 加载 `uboot_drivers_debug.md`

## 使用示例

### 示例 1：RK3588 启动流程分析

**用户提问：**
> RK3588 从上电到内核启动的完整流程是什么？每个阶段加载什么？

**AI 行为：**
1. 自动触发 `rk_uboot` 技能
2. 画出完整启动链：BootROM → TPL (DDR init) → SPL (ATF+OP-TEE) → U-Boot → Kernel
3. 说明各阶段固件的存储位置和加载方式
4. 对比 SPL/TPL 路径和 Miniloader 路径的差异

### 示例 2：Secure Boot 开启

**用户提问：**
> RK3568 产品需要开启 Secure Boot 防止固件被篡改，怎么做？

**AI 行为：**
1. 介绍 FIT 签名方案的完整流程
2. 给出密钥生成、固件签名、OTP 烧写的步骤
3. 说明验证链（BootROM 验证 Loader → Loader 验证 U-Boot → U-Boot 验证 Kernel）
4. 加载 `references/boot_flow_fit.md` 提供详细命令和配置

### 示例 3：OTA 升级方案

**用户提问：**
> RK3566 产品要做远程 OTA 升级，用 Recovery 模式还是 AB 系统？

**AI 行为：**
1. 对比两种方案的优劣（升级可靠性、存储开销、开发复杂度）
2. 根据用户场景给出推荐
3. 提供对应方案的分区表配置和 DTS/defconfig 修改
4. 加载 `references/uboot_drivers_debug.md` 提供升级流程细节

## 知识来源

| 文档 | 说明 |
|------|------|
| Rockchip_Developer_Guide_UBoot_Nextdev_CN | U-Boot next-dev 开发指南 (270p, 主文档) |
| Rockchip_Developer_Guide_UBoot_Nextdev_vs_RKDEV_CN | rkdevelop vs next-dev 差异对比 |
| Rockchip_Developer_Guide_Trust_CN | ARM TrustZone / ATF / OP-TEE |
| Rockchip_Developer_Guide_Partition_CN | 分区表 (GPT / Parameter) |
| Rockchip_Developer_Guide_Linux_Upgrade_CN | Linux OTA / Recovery / A/B 升级 |
| Rockchip_Developer_Guide_Secure_Boot_for_UBoot_Next_Dev_CN | FIT 安全启动 / 签名 / 防回滚 |
| Rockchip_Developer_Guide_TFTP_Upgrade_CN | TFTP 网络升级 |
| Rockchip_Developer_Guide_Linux_AB_System_CN | A/B 系统启动与升级 |

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

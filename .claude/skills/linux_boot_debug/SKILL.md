---
name: linux_boot_debug
description: "通用 Linux 启动流程调试与开机优化技能，不限于任何特定 SoC 平台。用于分析 Linux 系统启动过程中的问题（bootloader 到 kernel 到 init 到 userspace 全流程）、串口日志分析、开机速度优化、initcall 耗时分析、systemd 启动分析、rootfs 挂载失败、init 进程问题。触发关键词：启动调试、boot debug、开机慢、boot time、开机优化、boot failure、启动失败、无法启动、串口日志、earlycon、initcall_debug、bootchart、systemd-analyze、启动卡住、rootfs 挂载失败、init not found、VFS: Cannot open root device、bootargs、initrd、initramfs、kernel panic on boot、Freeing unused kernel memory、deferred probe delay、开机时序、fsck 慢。当用户拿到串口开机日志分析问题或者想加速开机速度时触发本技能。"
---

# Linux 启动流程调试与开机优化技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| 启动卡住 / 无法进入系统 | §3 |
| 串口无输出 / earlycon | §2.1 |
| kernel panic on boot | §3.2 |
| rootfs 挂载失败 | §3.3 |
| init 进程找不到 | §3.4 |
| 开机慢想优化 | §4 |
| initcall 耗时分析 | §4.2 |
| systemd 启动分析 | §4.3 |
| DTB 加载/解析失败 | §3.5 |
| 查看完整启动流程 | §1 |

---

## 1. Linux 启动流程全景

```
┌──────────────────────────────────────────────────────────┐
│  电源上电 (Power On)                                       │
│    │                                                      │
│    ▼                                                      │
│  BootROM → 片内固化代码, 选择启动介质 (eMMC/SD/SPI/USB)      │
│    │                                                      │
│    ▼                                                      │
│  SPL/TPL → 初始化 DRAM, 加载 U-Boot                        │
│    │                                                      │
│    ▼                                                      │
│  U-Boot → 初始化外设, 加载 kernel + DTB + ramdisk           │
│    │       设置 bootargs (kernel command line)              │
│    ▼                                                      │
│  Kernel → 解压 → start_kernel() → 子系统初始化              │
│    │       → initcall levels (0-7) → 驱动 probe             │
│    ▼                                                      │
│  Init → /sbin/init 或 systemd → mount rootfs              │
│    │                                                      │
│    ▼                                                      │
│  Userspace → 服务启动 → 用户登录 / 应用启动                  │
└──────────────────────────────────────────────────────────┘
```

### 1.1 initcall 级别详解

内核通过 initcall 分级机制控制初始化顺序：

| 级别 | 宏 | 数值 | 典型内容 |
|------|-----|------|---------|
| early | `early_initcall` | 0 | 内存管理、早期中断 |
| core | `core_initcall` | 1 | 核心子系统 (irqchip, clocksource) |
| postcore | `postcore_initcall` | 2 | 总线注册 (platform_bus) |
| arch | `arch_initcall` | 3 | 架构特定初始化 |
| subsys | `subsys_initcall` | 4 | 子系统 (i2c_init, spi_init) |
| fs | `fs_initcall` | 5 | 文件系统注册 |
| device | `device_initcall` | 6 | 大部分驱动 (module_init) |
| late | `late_initcall` | 7 | 延迟初始化、非关键驱动 |

### 1.2 关键时间节点

```bash
# 内核启动关键时间点 (dmesg 筛选)
dmesg | grep -E "Booting Linux|Freeing unused|Run .* as init|systemd.*running"
```

| 日志标记 | 含义 |
|---------|------|
| `Booting Linux on physical CPU` | 内核开始执行 |
| `Calibrating delay loop` | CPU 频率校准 |
| `Freeing unused kernel memory` | initcall 执行完毕 |
| `Run /init as init process` | 开始执行 init |
| `systemd[1]: Startup finished` | systemd 启动完成 |

---

## 2. 串口日志分析

### 2.1 串口无输出的排查

```
串口无输出？
├── 检查波特率 (通常 115200, 有些平台 1500000)
├── 检查 TX/RX 是否接反
├── 检查内核 bootargs 中 console= 参数
│   └── console=ttyS2,1500000n8
│   └── console=ttyFIQ0 (某些平台的 FIQ debugger)
├── 检查 U-Boot 是否有输出
│   └── 有 U-Boot 无 kernel → earlycon/console 配置问题
│   └── 完全无输出 → 硬件问题或 BootROM 未选中该串口
└── 使用 earlycon 获取最早期日志
    └── bootargs: earlycon=uart8250,mmio32,0xfe660000
```

### 2.2 earlycon 配置

```bash
# bootargs 中添加: earlycon=uart8250,mmio32,0xfe660000 或直接 earlycon
# 常见 UART 类型: uart8250,mmio32,<addr> | pl011,<addr> | msm_serial_dm,<addr>
```

### 2.3 日志级别与 quiet 模式

```bash
# bootargs 中控制日志级别:
loglevel=7               # 显示所有级别日志
loglevel=4               # 只显示 warning 及以上
quiet                    # 几乎不显示 (loglevel=4 + 隐藏大量信息)

# 调试时建议:
# 移除 quiet, 设置 loglevel=7
# 生产环境想加速: 加上 quiet
```

### 2.4 串口日志关键信息提取

```bash
# 从串口日志文件中提取关键信息
grep -n "error\|fail\|panic\|oops\|warn\|timeout\|refused" boot.log
grep -n "probe\|deferred" boot.log          # 驱动加载问题
grep -n "mount\|rootfs\|VFS" boot.log       # 文件系统问题
grep -n "init\|systemd" boot.log            # init 启动问题
```

---

## 3. 启动失败诊断

### 3.1 诊断决策树

```
启动失败
├── 串口完全无输出
│   ├── 电源/供电问题 → 测量核心电压
│   ├── DRAM 初始化失败 → 检查 DDR 颗粒兼容性
│   ├── 启动介质选择错误 → 检查 boot pin / eFuse
│   └── 串口接线错误 → 检查 TX/RX/GND
│
├── 有 BootROM/SPL 输出，U-Boot 阶段停止
│   ├── DDR 训练失败 → DDR bin / ddr parameter
│   ├── U-Boot 镜像损坏 → 重新烧写
│   └── 存储介质读取失败 → eMMC/SD 硬件问题
│
├── 有 U-Boot 输出，内核阶段失败
│   ├── kernel panic 早期 → §3.2
│   ├── DTB 加载/解析失败 → §3.5
│   ├── rootfs 挂载失败 → §3.3
│   └── init 找不到 → §3.4
│
├── 内核启动完成但系统不可用
│   ├── systemd 启动失败 → §4.3
│   ├── 关键服务失败 → journalctl -p err
│   └── 启动卡在某处 → §3.6
│
└── 启动成功但耗时太长
    └── §4 开机优化
```

### 3.2 Kernel Panic on Boot

```bash
# 常见早期 panic 原因:
# 1. "Unable to mount root fs" → rootfs 路径或文件系统类型错误
# 2. "VFS: Cannot open root device" → root= 参数错误或存储驱动未编译
# 3. "Kernel panic - not syncing: No working init found" → init 程序丢失或损坏
# 4. "Attempted to kill init!" → init 进程崩溃
# 5. 页表异常 / 空指针 → 驱动 bug 或 DTB 错误

# 调试方法:
# 1) 添加 bootargs: panic=10 (panic 后 10 秒重启, 方便看日志)
# 2) 添加 bootargs: initcall_debug (打印每个 initcall 调用)
# 3) 如果 rootfs 相关, 先用 initramfs 验证内核本身是否正常
```

### 3.3 Rootfs 挂载失败

```bash
# 排查步骤:
# 1. 检查 bootargs 中 root= 参数
#    root=/dev/mmcblk0p8            # eMMC 分区
#    root=/dev/mmcblk1p2            # SD 卡分区
#    root=PARTUUID=xxxx-xxxx-xx    # UUID 方式 (推荐)
#    root=/dev/nfs nfsroot=...      # NFS 网络启动

# 2. 检查分区号是否正确
cat /proc/partitions               # 查看内核识别的分区

# 3. 检查文件系统类型
#    bootargs 中可能需要 rootfstype=ext4

# 4. 检查存储驱动是否编入内核 (非模块)
#    eMMC: CONFIG_MMC, CONFIG_MMC_SDHCI 等
#    NVMe: CONFIG_BLK_DEV_NVME
#    USB:  CONFIG_USB_STORAGE (如果 USB 根文件系统)

# 5. rootwait vs rootdelay
#    rootwait                       # 无限等待 root 设备 (推荐)
#    rootdelay=5                    # 等待 5 秒
```

### 3.4 Init 进程找不到

```bash
# 常见错误:
# "No working init found. Try passing init= option to kernel."
# "Run /init as init process" 后崩溃

# 排查方向:
# 1. init 程序是否存在
ls -la /sbin/init /init /linuxrc

# 2. init 程序架构是否匹配 (ARM64 内核 + ARM32 init = 失败)
file /sbin/init
# 应该显示: ELF 64-bit LSB ... ARM aarch64 (ARM64 平台)

# 3. 动态链接库是否存在
ldd /sbin/init                      # 确认 libc 等库存在

# 4. 通过 bootargs 指定 init:
init=/bin/sh                        # 最小 init, 直接进 shell
init=/sbin/init
init=/lib/systemd/systemd

# 5. 权限问题
ls -la /sbin/init                   # 确保有执行权限
```

### 3.5 DTB 加载失败

```bash
# 设备树相关启动失败:
# "FDT header is not valid"         → DTB 文件损坏
# "Error: FDT at ... is invalid"    → 加载地址错误
# 某驱动 probe 失败导致功能缺失      → DTB 属性错误

# 排查步骤:
# 1. U-Boot 中检查 DTB 加载
=> fdt addr $fdt_addr_r
=> fdt print /                      # 打印设备树根节点

# 2. 确认 DTB 与内核版本匹配
# 3. 反编译 DTB 检查内容
dtc -I dtb -O dts -o output.dts /boot/dtb/xxx.dtb

# 4. 检查 chosen 节点中的 bootargs
dtc -I dtb -O dts xxx.dtb | grep -A5 "chosen"
```

### 3.6 启动卡住不动

```bash
# 启动卡住的排查方法:
# 1. 如果卡在内核阶段:
#    加 initcall_debug 看卡在哪个 initcall
#    加 loglevel=7 看有无被抑制的错误

# 2. 如果卡在 systemd 阶段:
systemd-analyze                      # 总启动时间
systemd-analyze blame                # 各服务耗时
systemd-analyze critical-chain       # 关键路径

# 3. 如果卡在 splash/logo:
#    可能是 display 相关驱动问题
#    移除 splash 和 quiet 参数查看实际日志

# 4. 如果卡在 fsck:
#    大分区 ext4 首次检查耗时很长
#    可考虑 tune2fs -c 0 -i 0 /dev/xxx 禁用定期检查
```

---

## 4. 开机速度优化

### 4.1 优化方法论

```
开机时间 = bootloader + kernel + init/systemd + 应用
         每个阶段各自优化:

Bootloader 阶段:
 - 裁剪 U-Boot 不必要的初始化
 - 使用 Falcon mode (SPL 直接加载 kernel)
 - 减少 boot delay (bootdelay=0)

Kernel 阶段:
 - 裁剪不必要的驱动 (编译为模块或去掉)
 - 优化 initcall (延迟非关键驱动)
 - 启用 kernel 压缩优化 (LZ4 比 GZIP 快)
 - 使用 quiet 减少 console 输出

Init/Systemd 阶段:
 - 分析 critical-chain, 移除不必要的服务
 - 使用 systemd-analyze 找最慢的服务
 - 并行启动服务
 - 延迟非关键服务 (systemd timer)

应用阶段:
 - 预链接 (prelink)
 - 应用自身优化启动逻辑
 - 使用 readahead 预读磁盘
```

### 4.2 Initcall 耗时分析

```bash
# 内核启动时添加 bootargs:
initcall_debug                     # 打印每个 initcall 的调用和耗时

# 从 dmesg 提取 initcall 耗时:
dmesg | grep "initcall" | sort -k4 -t= -n -r | head -20
# 输出格式: initcall xxx_init+0x0/0x20 returned 0 after 12345 usecs

# 使用内核 scripts/bootgraph.pl 生成可视化:
dmesg > boot.log
perl scripts/bootgraph.pl boot.log > bootgraph.svg

# 使用 ftrace 追踪 initcall (更精确):
# bootargs 中添加:
trace_event=initcall:initcall_start,initcall:initcall_finish initcall_debug
```

### 4.3 Systemd 启动分析

```bash
# 总启动时间:
systemd-analyze
# Startup finished in 1.5s (kernel) + 3.2s (userspace) = 4.7s

# 各服务耗时排序:
systemd-analyze blame
# 找出最耗时的服务, 考虑禁用或延迟

# 关键路径分析:
systemd-analyze critical-chain
# 找出阻塞启动的关键链

# 可视化 (生成 SVG):
systemd-analyze plot > startup.svg

# 检查不必要的服务:
systemctl list-unit-files --state=enabled
# 禁用不需要的:
systemctl disable <service-name>

# 查看某个服务的依赖导致的等待:
systemd-analyze critical-chain <service-name>
```

### 4.4 Bootchart 启动分析

```bash
# bootargs: init=/lib/systemd/systemd-bootchart → 图表保存 /run/log/
# 或: apt install bootchart2 → 自动在下次启动时收集
```

### 4.5 常用优化手段速查表

| 优化手段 | 阶段 | 预期收益 | 风险 |
|---------|------|---------|------|
| `bootdelay=0` | U-Boot | 2-3s | 无法中断进入 U-Boot |
| 裁剪无用驱动 | Kernel | 0.5-2s | 需要仔细评估 |
| `quiet` | Kernel | 0.2-1s | 无法看到启动日志 |
| LZ4 内核压缩 | Kernel | 0.3-0.5s | 镜像稍大 |
| 禁用无用服务 | Systemd | 1-5s | 某些功能不可用 |
| `readahead` | Systemd | 0.5-1s | 首次启动无效 |
| Falcon mode (SPL 直引内核) | Bootloader | 1-2s | 灵活性降低 |
| 延迟非关键驱动 (module) | Kernel | 0.5-3s | 功能延迟可用 |

---

## 5. Kernel Command Line (bootargs) 速查

### 5.1 启动调试相关参数

| 参数 | 功能 |
|------|------|
| `console=ttyS0,115200` | 指定串口控制台 |
| `earlycon` | 启用早期控制台 |
| `earlyprintk` | 更早的打印 (某些架构) |
| `loglevel=7` | 设置控制台日志级别 |
| `initcall_debug` | 打印所有 initcall 耗时 |
| `ignore_loglevel` | 忽略日志级别过滤 |
| `debug` | 等同于 loglevel=7 |
| `quiet` | 减少控制台输出 |
| `panic=10` | panic 后 10s 重启 |
| `oops=panic` | oops 也触发 panic |
| `no_console_suspend` | 休眠时保持 console |

### 5.2 Rootfs 相关参数

| 参数 | 功能 |
|------|------|
| `root=/dev/mmcblk0p8` | 指定 root 设备 |
| `rootfstype=ext4` | 指定文件系统类型 |
| `rootwait` | 等待 root 设备就绪 |
| `rootdelay=5` | 等待 N 秒 |
| `rw` / `ro` | 读写/只读挂载 rootfs |
| `init=/sbin/init` | 指定 init 程序 |

### 5.3 调试启动流程的 bootargs 模板

```bash
# 最大化调试信息:
console=ttyS2,1500000n8 earlycon loglevel=7 initcall_debug
panic=10 no_console_suspend

# 快速启动 (生产环境):
console=ttyS2,1500000n8 quiet loglevel=4 rootwait

# 当 rootfs 有问题时用 initramfs 紧急修复:
console=ttyS2,1500000n8 root=/dev/ram0 rdinit=/bin/sh
```

---

## 6. 嵌入式常见启动问题速查

### 6.1 常见错误码与含义

| 错误信息 | 原因 | 解决方向 |
|---------|------|---------|
| `VFS: Cannot open root device` | root= 参数指定的设备不存在 | 检查存储驱动、分区号 |
| `No working init found` | init 程序缺失或不可执行 | 检查 rootfs 完整性 |
| `Kernel panic - not syncing: Attempted to kill init!` | init 进程崩溃 | 检查 libc、init 程序 |
| `end Kernel panic - not syncing: VFS:` | 文件系统挂不上 | rootfstype=? |
| `request_module: runaway loop` | 模块依赖循环 | 检查 modules.dep |
| `RAMDISK: incomplete write` | initrd 加载不完整 | 检查 initrd 大小和加载地址 |
| `FDT header is not valid` | DTB 损坏或加载地址错 | 重新编译/烧写 DTB |

### 6.2 启动阶段硬件检查清单

```
□ 供电电压正常 (VDDCORE, VDDIO, VDDR 等)
□ 时钟晶振工作 (24MHz / 32.768KHz)
□ DRAM 初始化成功 (看 bootloader 输出)
□ 启动介质正常 (eMMC/SD 卡/SPI Flash)
□ 串口线材和波特率正确
□ 复位电路正常
□ Boot 模式引脚电平正确
```

---

## 7. deferred probe 导致的启动延迟

### 7.1 什么是 deferred probe

```
deferred probe 是内核设备模型的机制:
- 当驱动 probe() 时依赖的资源还没准备好 (如 clock/regulator/GPIO)
- 驱动返回 -EPROBE_DEFER (-517)
- 内核将设备放入 deferred list
- 等所有 initcall 完成后重试
- 过多 deferred probe 会显著延长启动时间
```

### 7.2 诊断和优化

```bash
# 查看哪些设备被 deferred:
cat /sys/kernel/debug/devices_deferred

# 查看 deferred probe 的原因:
grep "probe deferral" /sys/kernel/debug/devices_deferred
# 或:
dmesg | grep -i "defer"

# 使用 initcall_debug 看 probe 顺序:
dmesg | grep -E "probe|defer" | head -30

# 优化方法:
# 1. 确保依赖的驱动级别更高 (subsys_initcall vs device_initcall)
# 2. 在 DTS 中正确声明依赖关系
# 3. 将不需要的驱动改为模块, 在启动后加载
```

---

## 8. 文件系统相关启动问题

### 8.1 常见文件系统类型和 CONFIG

| 文件系统 | CONFIG | 用途 |
|---------|--------|------|
| ext4 | `EXT4_FS` | 通用 rootfs |
| squashfs | `SQUASHFS` | 只读压缩 rootfs |
| ubifs | `UBIFS_FS` | NAND flash |
| jffs2 | `JFFS2_FS` | NOR flash |
| f2fs | `F2FS_FS` | Flash-friendly |
| overlayfs | `OVERLAY_FS` | 叠加文件系统 |
| tmpfs | `TMPFS` | 内存文件系统 |
| nfs | `NFS_FS` | 网络调试 |

### 8.2 NFS 根文件系统启动

```bash
# NFS 根文件系统 bootargs:
root=/dev/nfs nfsroot=192.168.1.100:/nfs/rootfs,v3,tcp rw
ip=192.168.1.200:192.168.1.100:192.168.1.1:255.255.255.0::eth0:off

# ip= 格式:
# ip=<client>:<server>:<gateway>:<netmask>::<device>:<autoconf>

# 需要内核编译选项:
# CONFIG_NFS_FS=y, CONFIG_ROOT_NFS=y, CONFIG_IP_PNP=y
```

---

## 9. 实用调试技巧

### 9.1 在各阶段插入 shell

```bash
# 方法 1: 替换 init 进入 shell
init=/bin/sh                        # 直接进 shell, rootfs 已挂载

# 方法 2: 在 initramfs 中 break
# 某些 initramfs 支持:
break=premount                      # 挂载 rootfs 前进 shell
break=bottom                        # 挂载 rootfs 后进 shell

# 方法 3: systemd rescue
systemd.unit=rescue.target          # 进入救援模式
systemd.unit=emergency.target       # 进入紧急模式
```

### 9.2 最小化启动验证

```bash
# 步骤: 逐步排除法
# 1. 内核 + 最小 initramfs (只含 busybox)
#    → 验证内核本身是否正常
# 2. 内核 + 完整 rootfs + init=/bin/sh
#    → 验证 rootfs 是否正常
# 3. 内核 + 完整 rootfs + 正常 init
#    → 验证 init 流程是否正常
# 4. 逐个启用服务
#    → 找出导致问题的服务
```

### 9.3 U-Boot 环境变量检查

```bash
# U-Boot 命令行:
printenv bootargs                  # 看 bootargs
setenv bootargs "console=ttyS2,1500000n8 root=/dev/mmcblk0p8 rootwait rw loglevel=7"
saveenv
# 手动启动: load mmc 0:6 $kernel_addr_r Image → booti $kernel_addr_r - $fdt_addr_r
```

---

## 10. 启动时间测量方法

### 10.1 各阶段时间测量

```bash
# 硬件计时:
# GPIO toggle + 示波器: 最精确, 测量从上电到特定节点的时间

# 软件计时:
# 1. U-Boot 阶段:
=> time boot                          # U-Boot 内置命令
# 2. Kernel 阶段:
dmesg | head -1                       # 第一条内核日志时间
dmesg | grep "Freeing unused"         # initcall 完成时间
# 3. Systemd 阶段:
systemd-analyze                       # 内核+用户空间总时间

# 4. 应用层:
# 在启动完成的应用中记录时间戳
```

### 10.2 printk 时间戳精度

```bash
# bootargs 中:
printk.time=1                         # 启用 printk 时间戳 (默认已开)
# 注意: printk 时间戳是从内核启动开始算的相对时间
# 不包含 bootloader 阶段时间
```

---

## 参考资料索引

| 文件 | 内容 | 加载时机 |
|------|------|---------|
| `references/boot_flow_analysis.md` | 完整启动流程深度分析、各阶段时间拆解、bootloader 到内核的参数传递、initrd/initramfs 机制、设备树的角色 | 用户需要理解完整启动流程 |
| `references/boot_optimization.md` | 开机速度优化全攻略、Bootloader 优化 (Falcon mode / bootdelay)、内核裁剪与 initcall 优化、systemd 优化配置、文件系统选型与优化、应用层启动优化、Thunder Boot 方案 | 用户需要优化开机速度 |
| `references/boot_failure_diagnosis.md` | 启动失败完整诊断手册、kernel panic 分类与解读、rootfs/init/DTB 失败的深度排查、串口日志分析模板、NFS/网络启动调试、Recovery 模式 | 用户遇到启动失败问题 |

# 启动流程深度分析

## Bootloader 阶段详解

### BootROM
- 片内固化代码，不可修改
- 读取 boot pin / eFuse 选择启动介质
- 加载并校验第一级引导程序 (SPL/TPL)
- 常见介质优先级：SPI NOR > SPI NAND > eMMC > SD > USB

### SPL/TPL (Secondary/Tertiary Program Loader)
- 初始化时钟树 (PLL 配置)
- 初始化 DRAM 控制器和 DDR 训练
- 加载 U-Boot proper 到 DRAM
- 若使用 Falcon mode，可跳过 U-Boot 直接加载 Kernel

### U-Boot
- 初始化更多外设 (网络、USB、显示)
- 加载 kernel Image、DTB、ramdisk 到指定地址
- 设置 bootargs (kernel command line)
- 启动内核：`booti`/`bootz`/`bootm`

### 参数传递机制
```
U-Boot → Kernel 的信息传递:
1. DTB (Device Tree Blob): 硬件描述
2. bootargs: 通过 DTB 的 chosen 节点或直接传参
3. initrd/ramdisk: 初始文件系统 (可选)
4. 加载地址: kernel_addr_r, fdt_addr_r, ramdisk_addr_r
```

## Kernel 启动阶段详解

### 解压与入口
```
1. 压缩内核自解压 (zImage) 或直接跳入 (Image)
2. 入口函数: head.S → start_kernel() (init/main.c)
3. start_kernel() 执行顺序:
   - setup_arch()         # 架构初始化、解析 DTB
   - mm_init()            # 内存管理初始化
   - sched_init()         # 调度器初始化
   - init_IRQ()           # 中断控制器初始化
   - time_init()          # 定时器初始化
   - console_init()       # 控制台初始化 (earlycon 之后的正式 console)
   - rest_init()          # 创建 init 线程和 kthreadd
```

### initcall 执行
```
rest_init() → kernel_init() → kernel_init_freeable()
→ do_basic_setup() → do_initcalls()
→ 按级别 0-7 顺序执行所有 initcall
→ 同级别内按链接顺序执行 (Makefile 中的编译顺序)
→ 所有 initcall 完成后 → free_initmem()
→ 打印 "Freeing unused kernel memory"
→ 尝试执行 init 程序
```

### init 进程搜索顺序
```
1. bootargs 中 init= 指定的路径
2. /sbin/init
3. /etc/init
4. /bin/init
5. /bin/sh
如果都不存在 → panic "No working init found"
```

## initrd / initramfs 机制

### initramfs (推荐)
```
- cpio 格式的归档，编译进内核或外部加载
- 作为 rootfs 的初始内容
- 可包含早期用户空间工具 (udev, modprobe 等)
- 执行 /init 脚本完成:
  1. 加载必要的内核模块 (存储驱动等)
  2. 等待真正的 root 设备就绪
  3. mount 真正的 rootfs
  4. switch_root 切换到真正的根
```

### initrd (传统方式)
```
- 加载到内存的 ramdisk
- 内核将其 mount 为临时根
- 执行 /linuxrc
- pivot_root 到真正的根
- 已逐渐被 initramfs 取代
```

## 设备树在启动中的角色

```
DTB 在启动过程中的关键作用:
1. chosen 节点: 传递 bootargs、stdout-path (控制台)
2. memory 节点: 描述可用物理内存
3. 各设备节点: 驱动 probe 的依据
4. reserved-memory: 预留内存区域 (CMA/DMA)
5. 时钟/中断/GPIO 等资源描述

DTB 加载失败的影响:
- 内存信息丢失 → 无法建立页表 → 早期崩溃
- 中断控制器未初始化 → 无法处理中断 → 系统卡死
- 存储控制器驱动无法 probe → rootfs 挂不上
```

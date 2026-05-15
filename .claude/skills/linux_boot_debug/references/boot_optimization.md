# 开机速度优化全攻略

## 1. 优化总体方法论

```
Step 1: 测量 — 精确测量各阶段耗时
Step 2: 分析 — 找到瓶颈 (80/20 法则: 20% 的模块占 80% 的时间)
Step 3: 优化 — 针对瓶颈优化
Step 4: 验证 — 重新测量确认效果
Step 5: 迭代 — 重复以上过程
```

## 2. Bootloader 阶段优化

### 2.1 减少 U-Boot 延迟
```bash
# 设置 bootdelay=0 (跳过 autoboot 倒计时)
setenv bootdelay 0
saveenv
# 注意: 设置为 0 后无法通过串口中断进入 U-Boot
# 可以用 bootdelay=-2 完全禁用 (无法通过按键中断)

# 如果仍需要进入 U-Boot 的紧急方式:
# - 某些平台支持特殊 GPIO 组合进入 Loader 模式
# - Maskrom 模式总是可用的
```

### 2.2 Falcon Mode (SPL 直引内核)
```
原理: SPL 跳过 U-Boot, 直接加载 kernel + DTB
效果: 节省 1-2 秒 (U-Boot 初始化时间)
代价: 失去 U-Boot 的灵活性 (不能改 bootargs, 不能用 rescue)

配置步骤:
1. CONFIG_SPL_OS_BOOT=y
2. 将 kernel 和 DTB 放在 SPL 可直接读取的位置
3. SPL 加载 kernel + DTB 后直接 boot
4. 保留回退: 某个 GPIO 按下 → 正常走 U-Boot
```

### 2.3 U-Boot 裁剪
```
- 去掉 splash screen / logo 显示
- 去掉 USB 初始化 (如果不需要 USB 启动)
- 去掉网络初始化 (如果不需要 TFTP/NFS 启动)
- 去掉 console banner 字符串
- 简化 bootcmd (去掉多余的检查逻辑)
```

## 3. Kernel 阶段优化

### 3.1 内核压缩方式选择
| 压缩方式 | 压缩比 | 解压速度 | 推荐场景 |
|---------|--------|---------|---------|
| LZ4 | 低 | **最快** | 快速启动优先 |
| LZO | 中 | 快 | 平衡方案 |
| GZIP | 高 | 中 | 存储空间不足 |
| LZMA/XZ | 最高 | 慢 | 存储极度不足 |
| 不压缩 (Image) | 无 | **最快** | 存储不是问题 |

```
CONFIG_KERNEL_LZ4=y     # 推荐用于快速启动
```

### 3.2 裁剪内核驱动
```bash
# 原则: 不需要的驱动不编译, 非启动关键的驱动编为模块
# 分析当前使用的模块:
lsmod | wc -l            # 当前加载的模块数
cat /proc/modules         # 详细模块列表

# 裁剪方法:
# 1. make localmodconfig  # 基于当前加载的模块生成最小配置
# 2. 手动 review 每个子系统的 CONFIG
# 3. 常见可裁剪项:
#    - 不用的文件系统 (NTFS, BTRFS, XFS 等)
#    - 不用的网络协议 (IPv6, NFC, CAN 等)
#    - 不用的设备驱动 (不存在的硬件)
#    - 调试功能 (生产环境关闭 KASAN, LOCKDEP 等)
```

### 3.3 initcall 优化
```bash
# 找出最慢的 initcall:
dmesg | grep "initcall" | sed 's/.*after //' | sed 's/ usecs//' | sort -nr | head -20

# 将慢的 initcall 对应的驱动:
# 1. 改为模块, 启动后异步加载
# 2. 或用 deferred_probe 机制延迟
# 3. 或修改驱动本身的初始化逻辑 (减少阻塞等待)

# 异步 probe (kernel 5.x+):
# 某些驱动支持异步 probe, 可以并行初始化
# 在 DTS 中或驱动中标记 PROBE_PREFER_ASYNCHRONOUS
```

### 3.4 console 输出优化
```bash
# console 串口输出是同步阻塞的, 大量输出会显著拖慢启动
# 优化方法:
quiet                    # bootargs: 减少内核输出
loglevel=0               # bootargs: 几乎不输出
# 或:
console=                 # 不指定 console (= 不输出)
# 注意: 调试阶段不建议加 quiet
```

## 4. Systemd/Init 阶段优化

### 4.1 分析工具
```bash
# 总时间:
systemd-analyze
# Startup finished in 1.5s (kernel) + 8.2s (userspace) = 9.7s

# 各 unit 耗时排序:
systemd-analyze blame | head -20

# 关键路径:
systemd-analyze critical-chain

# 生成时间轴 SVG:
systemd-analyze plot > boot-timeline.svg

# 检查 unit 间依赖导致的等待:
systemd-analyze dot --order | dot -Tsvg > boot-deps.svg
```

### 4.2 禁用不必要的服务
```bash
# 常见可考虑禁用的服务:
systemctl disable NetworkManager-wait-online.service  # 等网络就绪 (通常很慢)
systemctl disable apt-daily.service                   # 自动更新
systemctl disable apt-daily-upgrade.service
systemctl disable ModemManager.service                # 调制解调器
systemctl disable bluetooth.service                   # 蓝牙 (如不需要)
systemctl disable fwupd.service                       # 固件更新

# 禁用 Plymouth splash:
systemctl disable plymouth-start.service
```

### 4.3 Socket/Bus 激活
```
systemd 高级特性: 不在启动时启动服务, 而是:
- Socket activation: 有连接请求时才启动
- D-Bus activation: 有 D-Bus 请求时才启动
- Path activation: 文件变化时才启动
- Timer activation: 定时启动 (延迟到启动后)

适合于: 非启动关键、低频使用的服务
```

## 5. 文件系统优化

### 5.1 选择合适的文件系统
```
快速启动推荐:
- squashfs (只读, 压缩, 挂载极快) + overlayfs (可写层)
- erofs (比 squashfs 更快的只读 FS)
- ext4 with noatime,nodiratime

避免:
- btrfs (功能丰富但挂载较慢)
- 大分区 ext4 不带 ^has_journal (需要 fsck 很慢)
```

### 5.2 禁用 fsck 检查
```bash
# 对于嵌入式设备, 可以禁用定期 fsck:
tune2fs -c 0 -i 0 /dev/mmcblk0p8
# -c 0: 不按挂载次数检查
# -i 0: 不按时间间隔检查

# 也可在 fstab 中设置 passno 为 0
```

## 6. Thunder Boot / 极速启动方案

```
某些 SoC 厂商提供的极速启动方案 (如 Rockchip Thunder Boot):
原理:
1. 利用 BootROM 或 SPL 直接初始化关键外设 (如 Camera/Display)
2. 在内核加载完成前就开始采集/显示
3. 内核启动后接管 (seamless handover)

效果: 从上电到第一帧画面 < 500ms
限制:
- 需要 BootROM/SPL 级别的定制
- 只适用于特定的外设场景
- 灵活性很低
```

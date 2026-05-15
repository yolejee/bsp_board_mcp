# 启动失败完整诊断手册

## 1. Kernel Panic 分类与解读

### 1.1 早期 Panic (start_kernel → initcall 阶段)
```
特征: 在 "Freeing unused kernel memory" 之前崩溃
常见原因:
- DTB 解析错误 (memory 节点缺失/错误)
- 中断控制器初始化失败
- 时钟子系统初始化失败
- 页表/内存管理初始化异常
- 驱动 bug 导致的空指针/越界

调试方法:
1. earlycon 获取最早期日志
2. initcall_debug 定位卡在哪个 init 函数
3. 检查 DTB 是否完整 (dtc -I dtb -O dts 反编译并检查)
4. 检查内核 CONFIG 是否与硬件匹配
```

### 1.2 Rootfs 相关 Panic
```
错误信息及分析:

"VFS: Cannot open root device \"mmcblk0p8\" or unknown-block(0,0)"
→ root 设备不存在
→ 排查: 存储驱动是否编入内核 (不能是模块), 分区号是否对

"VFS: Unable to mount root fs on unknown-block(179,8)"
→ 找到了设备但无法挂载
→ 排查: rootfstype= 参数, 文件系统是否损坏

"RAMDISK: couldn't find valid RAM disk image starting at 0"
→ initrd 加载失败
→ 排查: initrd 地址和大小是否正确
```

### 1.3 Init 相关 Panic
```
"Kernel panic - not syncing: No working init found."
→ 所有 init 路径都不存在或不可执行
→ 排查步骤:
  1. init=/bin/sh 测试 rootfs 是否正常
  2. file /sbin/init 检查架构匹配
  3. ldd /sbin/init 检查动态库
  4. ls -la /sbin/init 检查权限

"Kernel panic - not syncing: Attempted to kill init!"
→ init 进程崩溃
→ 排查: init 程序自身的 bug, libc 兼容性, 段错误
```

## 2. 串口日志分析模板

### 2.1 日志分段分析
```
一份完整的串口启动日志可以分为以下阶段:

[BootROM]   "Boot..." 或厂商特定的输出
[SPL/TPL]   "U-Boot SPL" 或 DDR 初始化信息
[U-Boot]    "U-Boot 2017.09" 版本信息, 环境变量, 加载地址
[Kernel]    "Booting Linux on physical CPU 0x0" 开始
            "Calibrating delay loop" CPU 校准
            大量驱动 probe 信息
            "Freeing unused kernel memory" initcall 结束
[Init]      "Run /sbin/init as init process"
[Systemd]   "systemd[1]: Startup finished..."
```

### 2.2 关键 grep 模式
```bash
# 提取错误:
grep -in "error\|fail\|panic\|oops\|bug\|warn\|timeout" boot.log

# 提取时间相关:
grep -in "time\|delay\|usec\|msec\|second" boot.log

# 提取启动里程碑:
grep -in "Booting\|Freeing\|init\|systemd\|login" boot.log

# 提取设备状态:
grep -in "probe\|register\|ready\|mounted\|started" boot.log
```

## 3. NFS 根文件系统调试

### 3.1 NFS 启动配置
```bash
# 必需的内核 CONFIG:
CONFIG_NFS_FS=y
CONFIG_NFS_V3=y         # 推荐 v3
CONFIG_ROOT_NFS=y
CONFIG_IP_PNP=y         # 内核级网络配置
CONFIG_IP_PNP_DHCP=y    # 可选: 自动获取 IP

# bootargs 示例:
root=/dev/nfs nfsroot=192.168.1.100:/nfs/rootfs,v3,tcp rw
ip=192.168.1.200:192.168.1.100:192.168.1.1:255.255.255.0::eth0:off
```

### 3.2 NFS 启动失败排查
```bash
# 检查网络:
# 确保 U-Boot 中网络能 ping 通 NFS 服务器

# 服务器端检查:
exportfs -v              # 查看 NFS 导出
showmount -e localhost   # 查看可用共享
# 确保导出选项包含: (rw,sync,no_root_squash,no_subtree_check)

# 客户端 bootargs ip= 格式:
# ip=<client-ip>:<server-ip>:<gateway>:<netmask>::<device>:<autoconf>
# 最后的 autoconf 可以是 off/dhcp/bootp
```

## 4. Recovery 模式

### 4.1 进入 Recovery 的方法
```bash
# 方法 1: bootargs 加 init=/bin/sh
# 直接进入最小 shell, rootfs 已挂载

# 方法 2: systemd rescue 模式
# bootargs 加: systemd.unit=rescue.target
# 或在 GRUB/U-Boot 启动时选择 recovery 选项

# 方法 3: 使用独立 recovery 分区
# 某些嵌入式系统有独立的 recovery ramdisk
# U-Boot 检测按键 → 加载 recovery ramdisk

# 方法 4: initramfs 内置 shell
# 在 initramfs 的 /init 脚本中加入:
# if [ -f /break ]; then exec /bin/sh; fi
```

### 4.2 Recovery 后的修复操作
```bash
# 常见修复操作:
mount -o remount,rw /              # rootfs 改为读写
passwd root                         # 重置密码
fsck /dev/mmcblk0p8                 # 检查文件系统
dpkg --configure -a                 # 修复包管理器
systemctl enable xxx                # 恢复服务
```

# VOP2 架构与多屏显示详解

## 目录

1. [VOP2 架构](#1-vop2-架构)
2. [图层分配策略](#2-图层分配策略)
3. [多屏显示配置详解](#3-多屏显示配置详解)
4. [Baseparameter 配置](#4-baseparameter-配置)
5. [DRM 调试接口](#5-drm-调试接口)
6. [U-Boot 到 Kernel 显示过渡](#6-u-boot-到-kernel-显示过渡)

---

## 1. VOP2 架构

### 1.1 VOP2 组成 (以 RK3568 为例)

```
VOP2
├── Video Port 0 (VP0) ─→ HDMI / eDP / DSI0 (4K capable)
│   ├── Cluster0 (4K, AFBC, HDR)
│   ├── Esmart0 (多格式, 缩放)
│   └── Smart0 (基础)
├── Video Port 1 (VP1) ─→ HDMI / eDP / DSI0 / LVDS (2K)
│   ├── Cluster1 (AFBC)
│   ├── Esmart1 (多格式, 缩放)
│   └── Smart1 (基础)
└── Video Port 2 (VP2) ─→ LVDS / DSI1 (1080p)
    └── Esmart2 / Smart2 (固定)
```

### 1.2 图层类型

| 类型 | 支持 AFBC | 支持缩放 | 最大分辨率 | 数量 (RK3568) |
|------|---------|---------|----------|-------------|
| Cluster | ✅ | ✅ (4K) | 4096×2160 | 2 |
| Esmart | ❌ | ✅ | 4096×2160 | 2 |
| Smart | ❌ | ❌ | 4096×2160 | 2 |

### 1.3 RK3588 VOP2 扩展

```
RK3588 VOP2:
├── VP0 (8K@30 / 4K@120) → HDMI0 / eDP0 / DP0
│   ├── Cluster0 (4 layers)
│   └── Esmart0
├── VP1 (4K@60) → HDMI1 / eDP1 / DP1
│   ├── Cluster1 (4 layers)
│   └── Esmart1
├── VP2 (4K@60) → HDMI1 / eDP1 / DSI0 / DP1
│   ├── Cluster2
│   └── Esmart2
└── VP3 (2K) → DSI1 / DP1
    ├── Cluster3
    └── Esmart3

8 个 Cluster layer, 4 个 Esmart layer, 总计 12 layers
每个 Cluster 支持 4 个 sub-layer (layer split)
```

---

## 2. 图层分配策略

### 2.1 默认分配

```
默认: 每个 VP 关联固定的图层
VP0 → Cluster0 + Esmart0 + Smart0
VP1 → Cluster1 + Esmart1 + Smart1

图层可以在不同 VP 间迁移 (Plane Migration)
当某个 VP 的图层不够用时, 从其他 VP 借用
```

### 2.2 DTS 自定义分配

```dts
// 指定某个图层归属特定 VP
&vp0 {
    // 指定 Cluster0 为鼠标层 (硬件光标)
    cursor-win-id = <ROCKCHIP_VOP2_CLUSTER0>;
};

// 禁止图层迁移 (避免多屏间闪烁)
&vop {
    rockchip,plane-mask = <(1<<CLUSTER0 | 1<<ESMART0)>,  // VP0
                          <(1<<CLUSTER1 | 1<<ESMART1)>,  // VP1
                          <(1<<SMART0)>;                  // VP2
};
```

### 2.3 VOP2 Plane Assign 文档参考

```
Rockchip_VOP2_Plane_Assign.pdf 描述了:
- 各平台图层分配的默认规则
- 动态迁移的触发条件
- 多屏场景下的图层分配策略
- 降分辨率/降刷新率时的图层释放策略
```

---

## 3. 多屏显示配置详解

### 3.1 双屏异显

```dts
// VP0 → HDMI (4K@60), VP1 → DSI (1080p)
&route_hdmi {
    status = "okay";
    connect = <&vp0_out_hdmi>;    // VP0 驱动 HDMI
};

&route_dsi0 {
    status = "okay";
    connect = <&vp1_out_dsi0>;    // VP1 驱动 DSI
};

// endpoint 配置
&hdmi_in_vp0 { status = "okay"; };
&dsi0_in_vp1 { status = "okay"; };
```

### 3.2 三屏/四屏 (RK3588)

```dts
// VP0 → HDMI0, VP1 → HDMI1, VP2 → DSI0, VP3 → DSI1
&route_hdmi0 { status = "okay"; connect = <&vp0_out_hdmi0>; };
&route_hdmi1 { status = "okay"; connect = <&vp1_out_hdmi1>; };
&route_dsi0  { status = "okay"; connect = <&vp2_out_dsi0>;  };
&route_dsi1  { status = "okay"; connect = <&vp3_out_dsi1>;  };
```

### 3.3 多屏注意事项

```
1. 带宽限制:
   - 每个 VP 的最大处理能力不同
   - 同时运行多个 4K 输出需要足够的 DDR 带宽
   - RK3568 最多 3 个显示输出, RK3588 最多 4 个

2. VP 能力限制:
   - VP0 通常最强 (4K/8K capable)
   - VP2/VP3 较弱 (1080p~2K)
   - 4K@60 以上的输出放在 VP0

3. 图层不够:
   - 双屏各需要至少 1 个图层
   - 带 overlay 的应用需要更多图层
   - 可通过 plane-mask 固定分配
```

---

## 4. Baseparameter 配置

### 4.1 概念

```
baseparameter 是存储在 eMMC/SD 的一个数据分区
包含各显示接口的默认参数:
- 分辨率
- 刷新率
- 颜色格式/色深
- 过扫描 (overscan)
- 亮度/对比度/饱和度

U-Boot 和 Kernel 都会读取 baseparameter
确保开机到桌面的显示一致性
```

### 4.2 使用

```bash
# 写入工具: resource_tool (RK 提供)
# 或在用户空间通过 ioctl 设置

# 在 kernel cmdline 中指定:
# androidboot.baseparameter=/dev/block/by-name/baseparameter

# 结构体参考:
# struct base_parameter {
#     uint32_t tag;           // "BASP"
#     uint32_t version;
#     struct screen_info screen[8];
# };
```

---

## 5. DRM 调试接口

### 5.1 debugfs

```bash
# DRM 信息总览
cat /sys/kernel/debug/dri/0/summary
# 输出: Video Port 状态, Connector, CRTC, Plane 信息

# 完整 DRM state dump
cat /sys/kernel/debug/dri/0/state
# 输出: 所有 CRTC/Encoder/Connector/Plane 的属性

# VOP 寄存器 dump
cat /sys/kernel/debug/dri/0/regs
```

### 5.2 modetest 工具

```bash
# 列出所有 DRM 资源
modetest -M rockchip

# 关键信息:
# Connectors: id, type, status, modes
# CRTCs: id, fb, position, size
# Planes: id, crtc, type, formats

# 测试显示 (画彩条)
modetest -M rockchip -s <conn>@<crtc>:<WxH>[@<refresh>]
# 例: modetest -M rockchip -s 175@67:1920x1080@60

# 带图层测试
modetest -M rockchip -P <plane>@<crtc>:<WxH>[+<x>+<y>]

# 设置属性
modetest -M rockchip -w <conn>:<property>:<value>
```

### 5.3 DRM 日志控制

```bash
# 开启 DRM debug 日志
echo 0x1f > /sys/module/drm/parameters/debug

# 日志分类:
# 0x01 = DRM_UT_CORE       核心
# 0x02 = DRM_UT_DRIVER     驱动
# 0x04 = DRM_UT_KMS        模式设置
# 0x08 = DRM_UT_PRIME      prime/dma-buf
# 0x10 = DRM_UT_ATOMIC     atomic commit
# 0x1f = 全部

# 关闭
echo 0 > /sys/module/drm/parameters/debug
```

---

## 6. U-Boot 到 Kernel 显示过渡

### 6.1 无缝过渡条件

```
U-Boot logo → Kernel logo 无闪屏需要:
1. U-Boot 和 Kernel 使用相同的 VP 通路
2. 相同的分辨率和 timing
3. Kernel 驱动不重新初始化 VOP (fastboot display)
4. baseparameter 参数一致
```

### 6.2 闪屏排查

```
出现闪屏:
1. U-Boot 显示通路和 Kernel 不一致 → 统一 route 配置
2. U-Boot 分辨率和 Kernel 不同 → 统一 baseparameter
3. VOP 驱动 probe 时重新初始化 → 检查 fastboot display 支持
4. Panel init-sequence 执行导致闪烁 → 调整时序
```

### 6.3 U-Boot Logo 显示流程

```
1. logo.bmp + logo_kernel.bmp 放在 Linux kernel 根目录
2. 编译时打包 → resource.img → Boot.img
3. U-Boot 启动时加载两个文件到内存:
   - U-Boot Logo: 在 U-Boot 阶段显示
   - Kernel Logo: 内存地址传给 Linux, 在 DRM 驱动 init 阶段显示
4. U-Boot 显示驱动目录: drivers/video/drm/
```

---

## 7. DRM Component Framework

### 7.1 为什么需要 Component

```
DRM 驱动是 backlight + panel + DSI/HDMI/DP/eDP/LVDS + VOP 等模块的组合
这些模块相互依赖, 必须全部加载后 DRM 系统才能正常工作

问题:
- 模块加载顺序不确定 (多线程编译影响 initcall 顺序)
- 子设备没加载好, 主设备就加载了, 导致设备无法工作
- 子设备之间可能有时序依赖

解决: Component Framework (drivers/base/component.c)
- display_subsystem 作为 master, ports 中关联的节点作为 component
- 等所有 component 都加载完毕后, 统一执行 bind
```

### 7.2 Deferred Probe

```
当某个依赖资源未就绪时, 驱动返回 -EPROBE_DEFER 退出:
  dw-mipi-dsi: 找不到 panel 或 bridge → 返回 -EPROBE_DEFER
  → 内核稍后重试 probe
  → 直到 panel 驱动加载完, DSI bind 成功
  → 最终整个 DRM 驱动完成加载

Deferred probe log 示例:
  dw-mipi-dsi ff...: failed to find panel or bridge: -517
  # -517 = -EPROBE_DEFER, 这是正常行为, 不是错误
```

### 7.3 关闭 VOP IOMMU

```bash
# 关闭 VOP IOMMU 后 DRM 内存从 CMA 分配
# 系统默认 CMA 大小 16M, 需要根据场景调大, 否则分配内存失败
# DTS 修改:
&vop_mmu {
    status = "disabled";
};
# 同时调整 CMA: 在 cmdline 中 cma=128M
```

# 以太网 PHY/MAC 深度调试

## 1. PHY 基础知识

### 1.1 PHY 接口类型
```
接口类型         速率        信号线数    时钟       典型场景
─────────────────────────────────────────────────────────────
MII             10/100M     16 线      25MHz      旧百兆设计
RMII            10/100M     8 线       50MHz      百兆嵌入式 (省 IO)
GMII            10/100/1000 24 线      125MHz     千兆 (少用, 太多线)
RGMII           10/100/1000 12 线      125MHz     千兆嵌入式 ★ 最常用
SGMII           10/100/1000 差分对     625MHz     SerDes 千兆 (省 IO)
QSGMII          10/100/1000 差分对     -          4 端口复用
2.5G SGMII      2.5G        差分对     -          2.5G 网口
USXGMII         1-10G       差分对     -          多速率 SerDes

嵌入式最常用: RGMII (千兆), RMII (百兆)
```

### 1.2 RGMII 时序 (delay 配置)
```
RGMII 标准要求: 数据相对时钟有 1.5~2ns 的延迟

延迟实现方式 (三选一, 不要重复!):
1. PHY 芯片内部加 delay (最常用)
   → DTS: phy-mode = "rgmii"
   → PHY 驱动设置 TX/RX delay

2. MAC 侧加 delay
   → DTS: phy-mode = "rgmii-id" (TX+RX 都由 MAC 加)
   → 或 "rgmii-txid" / "rgmii-rxid" (仅加 TX / 仅加 RX)

3. PCB 走线加 delay (绕线)
   → 不推荐, 不好控制

常见错误:
- PHY 和 MAC 都加了 delay → 延迟过大 → link 不稳
- 谁都没加 delay → 数据采样错误 → CRC 错误 / 不通
- DTS phy-mode 写错 → 驱动不设 delay → 通信异常

排查步骤:
1. 确认 PHY 芯片 datasheet 的 delay 默认值
2. 确认 DTS phy-mode 设置
3. 确认 PHY 驱动是否会设置 delay 寄存器
4. 保证 TX 方向和 RX 方向各只有一处加 delay
```

## 2. 常见 PHY 芯片问题

### 2.1 Realtek RTL8211F / RTL8211E
```
RTL8211F:
- PHY ID: 0x001cc916
- 默认 TX delay: ON (寄存器 0x11 page 0xd08, bit 8)
- 默认 RX delay: ON (寄存器 0x15 page 0xd08, bit 3)
- DTS 推荐: phy-mode = "rgmii" (PHY 自己加 delay)

RTL8211E:
- PHY ID: 0x001cc915
- TX delay 和 RX delay 由外部 strap pin 控制
- 如果 strap 配置了 delay → phy-mode = "rgmii"
- 如果 strap 未配 delay → phy-mode = "rgmii-id"

常见问题:
- RTL8211F 千兆 OK, 百兆不通
  → 可能是 RGMII 延迟在百兆下不匹配, 检查是否双方都加了 delay
- Link 频繁 up/down
  → 检查 PHY 供电 (3.3V/1.8V), Reset GPIO 时序, MDC/MDIO 信号质量
```

### 2.2 Motorcomm YT8511 / YT8521
```
YT8511:
- PHY ID: 0x0000010a
- 支持 RGMII, 内部可配 TX/RX delay
- 需要 YT8511 PHY 驱动 (drivers/net/phy/motorcomm.c)
- DTS 推荐: phy-mode = "rgmii"

YT8521:
- PHY ID: 0x0000011a
- 支持 RGMII/SGMII, UTP/Fiber
- 内部可配 delay

常见问题:
- 驱动未编入内核 → PHY 无法识别 → fallback 到 genphy 驱动 → delay 可能不对
  → 确认 CONFIG_MOTORCOMM_PHY=y
```

### 2.3 Micrel/Microchip KSZ9031 / KSZ9131
```
KSZ9031:
- PHY ID: 0x00221620
- RGMII delay 通过 MMD 寄存器配置
- DTS 中可用 rxc-skew-ps / txc-skew-ps 属性配置精确延迟 (单位 ps)

KSZ9131:
- PHY ID: 0x00221640
- rxc-skew-psec / txc-skew-psec 属性
```

## 3. MDIO 总线调试

```bash
# 检查 MDIO 通信:
# 如果无法读取 PHY ID (寄存器 2/3) → MDIO 总线有问题

# 内核日志:
dmesg | grep -i "mdio\|phy\|stmmac\|ethernet"

# 常见 MDIO 问题:
# 1. PHY 未检测到:
#    "Cannot initialize PHY" / "No PHY found"
#    → 检查 MDIO 引脚配置 (pinctrl)
#    → 检查 PHY 地址 (DTS 中 reg = <N>)
#    → 检查 PHY 供电和 Reset 时序

# 2. 读的全是 0xffff:
#    → MDIO 时钟未使能
#    → PHY 处于 Reset 状态
#    → MDIO 引脚被其他功能复用

# 3. PHY ID 读到但与预期不符:
#    → PHY 地址可能与 DTS 不匹配
#    → 尝试扫描: for i in $(seq 0 31); do echo "PHY $i:"; done
```

## 4. MAC 驱动调试

```bash
# 查看 MAC 驱动:
ethtool -i eth0
# driver: stmmac       → Synopsys DesignWare MAC (大多数嵌入式 SoC 使用)
# driver: macb         → Cadence GEM MAC
# driver: fec          → NXP i.MX FEC

# stmmac 调试:
# 开启 debug:
echo "file stmmac_main.c +p" > /sys/kernel/debug/dynamic_debug/control
echo "file stmmac_platform.c +p" > /sys/kernel/debug/dynamic_debug/control

# 查看 DMA 描述符状态:
cat /sys/kernel/debug/stmmaceth/eth0/dma_cap
cat /sys/kernel/debug/stmmaceth/eth0/descriptors_status

# 性能优化:
# - 调整 TX/RX ring buffer 大小:
ethtool -G eth0 rx 4096 tx 4096
# - 开启中断合并 (降低 CPU 负载):
ethtool -C eth0 rx-usecs 64 rx-frames 32
```

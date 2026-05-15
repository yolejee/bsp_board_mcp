# 设备树问题排查案例集

## 案例 1: MIPI 屏幕不亮

### 症状
上电后 MIPI DSI 屏幕无显示，无背光。

### 排查步骤

**Step 1: 确认设备树已正确选择**
```bash
cat /proc/device-tree/model
# 应显示正确的板卡名称
```

**Step 2: 检查 DSI 控制器状态**
```bash
# 方法1: 通过 procfs
xxd /proc/device-tree/soc/dsi@fe060000/status
# 应显示 "okay"

# 方法2: 反编译整个 DTB 搜索
dtc -I fs -O dts /proc/device-tree/ 2>/dev/null | grep -A5 "dsi@"
```

**Step 3: 检查 VP 通路**
```bash
# 确认只有一个 VP 连接了 DSI
dtc -I fs -O dts /proc/device-tree/ 2>/dev/null | grep -B2 -A2 "dsi0_in"
```

**Step 4: 检查背光**
```bash
ls /sys/class/backlight/
cat /sys/class/backlight/*/brightness
cat /sys/class/backlight/*/max_brightness
# 如果 brightness=0，尝试:
echo 200 > /sys/class/backlight/backlight/brightness
```

**Step 5: 检查 kernel log**
```bash
dmesg | grep -i "dsi\|panel\|mipi\|backlight\|pwm\|drm"
```

### 常见原因
1. `&video_phy0` 没有设为 `okay`
2. VP0/VP1 选择错误（双屏配置时冲突）
3. `reset-gpios` 引脚号写错
4. `panel-init-sequence` 与屏幕不匹配
5. 背光 PWM 节点 status 不是 `okay`
6. 电源 regulator 没有使能

---

## 案例 2: I2C 设备不识别

### 症状
`i2cdetect` 扫描不到设备，或驱动 probe 失败。

### 排查步骤

**Step 1: 确认 I2C 控制器已启用**
```bash
ls /dev/i2c-*
# 应列出 i2c-0, i2c-1, ... 等
```

**Step 2: 扫描总线**
```bash
i2cdetect -y -r 0  # 扫描 i2c-0
i2cdetect -y -r 1  # 扫描 i2c-1
# 注意：有些设备在被驱动占用时显示 UU
```

**Step 3: 检查 DT 中的配置**
```bash
# 确认 I2C 节点 status
xxd /proc/device-tree/soc/i2c@fe*/status

# 确认子设备存在
ls /proc/device-tree/soc/i2c@*/
```

**Step 4: 检查 pinctrl**
```bash
cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins | grep i2c
# 确认 I2C 引脚已正确分配
```

### 常见原因
1. I2C 控制器 status 是 `disabled`
2. pinctrl mux 组选错 (m0 vs m1)
3. I2C 地址写错 (7位 vs 8位，需要用7位)
4. 电源 regulator 没到位
5. 引脚被其他外设复用

---

## 案例 3: 以太网不通

### 症状
`ifconfig` 看不到 eth0，或能看到但无法获取 IP。

### 排查步骤

**Step 1: 检查 GMAC 节点**
```bash
xxd /proc/device-tree/soc/ethernet@*/status
# 应返回 "okay"
```

**Step 2: 检查 PHY**
```bash
dmesg | grep -i "mdio\|phy\|ethernet\|gmac\|stmmac"
# 看是否识别到 PHY
```

**Step 3: 检查 link 状态**
```bash
ethtool eth0
# 看 Link detected: yes/no
ip link show eth0
# 看 state UP/DOWN
```

**Step 4: TX/RX delay 调试**
```bash
# 如果能 link up 但丢包严重，可能是 delay 不对
# 修改 DTS 中的 tx_delay 和 rx_delay，范围通常 0x00~0x7f
# 建议从默认值开始，逐步调整
```

### 常见原因
1. PHY 复位 GPIO 或 delay 参数不对
2. TX/RX delay 不匹配
3. pinctrl mux 组选错 (gmac1m0 vs gmac1m1)
4. PHY 地址不匹配 (`reg = <0x0>` vs 实际)
5. 时钟配置错误
6. drive strength 不对 (level2 vs level3)

---

## 案例 4: USB 不工作

### 症状
USB 设备插入无反应，`lsusb` 看不到设备。

### 排查步骤

**Step 1: 检查 USB 相关节点**
```bash
# USB2 PHY
xxd /proc/device-tree/soc/usb2-phy@*/status

# EHCI/OHCI
xxd /proc/device-tree/soc/usb@*/status
```

**Step 2: 检查 kernel log**
```bash
dmesg | grep -i "usb\|ehci\|ohci\|xhci\|dwc\|phy"
```

**Step 3: 检查 VBUS 电源**
```bash
cat /sys/kernel/debug/regulator/regulator_summary | grep usb
# USB 口需要 5V VBUS 供电
```

### 常见原因
1. USB PHY 子节点没全部使能 (host + otg)
2. VBUS 供电 regulator GPIO 配置错误
3. Combo PHY 被配置为 SATA/PCIe (与 USB3 互斥)
4. OTG 模式 `dr_mode` 设置错误

---

## 案例 5: 摄像头不出图

### 症状
`v4l2-ctl --list-devices` 看不到 camera，或打开后无数据。

### 排查步骤

**Step 1: 检查 I2C 通信**
```bash
i2cdetect -y -r 1  # 摄像头通常在 i2c1
# 应看到 0x36 (OV5648/OV5647)
```

**Step 2: 检查 camera 驱动**
```bash
dmesg | grep -i "ov5648\|ov5647\|camera\|isp\|csi\|dphy"
```

**Step 3: 检查 media 拓扑**
```bash
media-ctl -p
# 应看到完整的 ISP pipeline
```

**Step 4: 检查电源**
```bash
cat /sys/kernel/debug/regulator/regulator_summary | grep cam
# dovdd(1.8V), avdd(2.8V), dvdd(1.2V) 都应该 on
```

### 常见原因
1. 摄像头供电 regulator 没使能
2. MCLK 时钟频率不对 (24MHz vs 25MHz vs 37.125MHz)
3. CSI data-lanes 配置错 (2-lane vs 4-lane)
4. endpoint remote-endpoint 连接错误
5. DPHY 没有使能

---

## 案例 6: PCIe 设备不识别

### 症状
`lspci` 看不到任何设备。

### 排查步骤

**Step 1: 检查 Combo PHY 和 PCIe 节点**
```bash
xxd /proc/device-tree/soc/pcie@*/status
```

**Step 2: 检查 kernel log**
```bash
dmesg | grep -i "pcie\|pci"
# 看是否有 link up 信息
```

**Step 3: 检查 reset GPIO**
```bash
cat /sys/kernel/debug/gpio | grep pcie
```

### 常见原因
1. `combphy2_psq` 被配为 SATA (互斥)
2. reset-gpios 引脚错误
3. 3.3V 供电 regulator 未使能
4. PCIe 设备需要更长的 power-on delay

---

## 案例 7: Overlay 不生效

### 症状
加载 DTBO 后功能没变化。

### 排查步骤

**Step 1: 检查 overlay 编译**
```bash
dtc -@ -I dts -O dtb -o test.dtbo overlay.dts
# -@ 是必须的，生成 __symbols__ 段
```

**Step 2: 确认 base DTB 有 __symbols__**
```bash
ls /proc/device-tree/__symbols__/
# 如果为空，base DTB 编译时需要加 -@
```

**Step 3: 检查 fragment target**
```bash
# overlay 中的 target 必须匹配 base DTB 中的节点
# target = <&uart3>; 要求 base DTB 中有 uart3 label
```

### 常见原因
1. DTBO 编译缺少 `-@` 参数
2. Base DTB 编译缺少 `-@` 参数
3. fragment target 指向不存在的节点
4. Overlay 中 compatible 不匹配
5. `/plugin/;` 标记缺失

---

## 案例 8: 串口无输出

### 症状
板子上电后串口没有任何输出。

### 排查步骤

**Step 1: 确认串口接线**
- TX/RX 是否交叉连接
- 波特率是否正确 (115200 或 1500000)
- 地线是否连接

**Step 2: 检查 debug 串口配置**
```dts
// fiq-debugger 通常使用 UART2
fiq-debugger {
    compatible = "rockchip,fiq-debugger";
    rockchip,serial-id = <2>;        // UART 编号
    rockchip,baudrate = <1500000>;   // 波特率
    pinctrl-0 = <&uart2m0_xfer>;     // mux 组
    status = "okay";
};
```

**Step 3: 检查 chosen/bootargs**
```dts
chosen {
    bootargs = "earlycon=uart8250,mmio32,0xfe660000 console=ttyFIQ0";
    // 0xfe660000 是 UART2 的寄存器基地址
};
```

### 常见原因
1. 波特率不匹配 (Rockchip 默认用 1500000)
2. pinctrl mux 组选错
3. UART 被其他节点占用
4. 串口芯片/转接板不支持 1.5M 波特率

---

## 通用排查技巧

### 方法 1: A/B 对比法
1. 找一份已知可工作的 DTS (如 EVB 开发板)
2. 将问题节点与工作版本逐属性对比
3. 缩小差异范围

### 方法 2: 最小化测试
1. 只保留问题相关的最少节点
2. 先用最基本的配置验证
3. 逐步添加功能，定位引入问题的修改

### 方法 3: 反编译验证
```bash
# 编译 DTS
dtc -I dts -O dtb -o test.dtb board.dts

# 立即反编译
dtc -I dtb -O dts -o verify.dts test.dtb

# 对比原始 DTS 和反编译结果
diff board.dts verify.dts
# 注意：反编译格式会不同，主要看节点和属性是否正确
```

### 方法 4: 运行时实时查看
```bash
# 持续监视 kernel log
dmesg -w | grep -i "error\|fail\|warn\|probe"

# 查看设备 probe 状态
ls /sys/bus/platform/drivers_autoprobe
cat /sys/bus/platform/devices/*/driver_override
```

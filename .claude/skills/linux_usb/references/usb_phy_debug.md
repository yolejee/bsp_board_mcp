# USB PHY 调试

## 1. USB PHY 类型

```
PHY 类型        接口标准       速率            说明
──────────────────────────────────────────────────────────
USB 2.0 PHY    UTMI/UTMI+     480 Mbps        大多数 SoC 内置
                ULPI           480 Mbps        外置 PHY (减少引脚)
USB 3.0 PHY    PIPE           5 Gbps          通常 SerDes 实现
               SSIC           5 Gbps          芯片内部互连
Combo PHY      PIPE+UTMI      USB2+USB3       复用物理接口
                                              (可能与 PCIe/SATA 共享)
```

## 2. PHY 驱动调试

### 2.1 PHY 初始化检查
```bash
# 查看 PHY 驱动:
dmesg | grep -i "phy\|usb.*init"

# 常见 PHY 初始化日志:
# "phy phy-xxx.0: phy init"       → PHY 初始化
# "phy phy-xxx.0: phy power on"   → PHY 上电

# PHY 初始化失败:
# "phy phy-xxx.0: phy init failed" → 检查时钟/供电/DTS
# "usb phy not found" → DTS 中 PHY phandle 配置错误

# sysfs PHY 信息:
ls /sys/class/phy/
cat /sys/class/phy/phy-xxx.0/type     # PHY 类型
```

### 2.2 PHY 时钟配置
```
USB 2.0 PHY 典型时钟:
  - 参考时钟: 24MHz / 25MHz / 26MHz (晶振输入)
  - 内部 PLL 倍频到 480MHz
  - 输出: UTMI 48MHz/60MHz 时钟

USB 3.0 PHY 典型时钟:
  - 参考时钟: 24MHz / 25MHz / 100MHz
  - SerDes PLL
  - 输出: PIPE 125MHz/250MHz

时钟问题排查:
  - 确认 DTS 中 PHY 节点的 clock 引用正确
  - 确认晶振频率与 PHY 驱动期望一致
  - 某些 PHY 需要在 DTS 中指定参考时钟频率:
    assigned-clock-rates = <24000000>;
```

## 3. USB 信号质量

### 3.1 USB 2.0 信号要求
```
USB 2.0 High-Speed 信号特性:
  - 差分信号幅度: 360~440 mV
  - 共模电压: -50 ~ 500 mV
  - 阻抗: 90Ω ±15% (差分)
  - 上升/下降时间: 500ps (典型)

信号质量问题表现:
  - CRC 错误 → ethtool -S (如果是 USB 网卡) 或 usbmon 中看到 -EILSEQ
  - 设备枚举不稳定 → 有时能识别有时不能
  - 仅低速才能工作, 高速失败

排查:
  1. 换 USB 线缆 (排除线缆问题)
  2. 直连 (排除 hub/延长线)
  3. 示波器测差分信号 (需要差分探头)
  4. 检查 PCB 走线 (差分阻抗, 等长)
```

### 3.2 USB 3.0 信号要求
```
USB 3.0 SuperSpeed 信号特性:
  - 差分信号: 800~1200 mV (峰峰值)
  - 数据率: 5 Gbps
  - 编码: 8b/10b
  - 阻抗: 90Ω ±7% (差分)

USB 3.0 链路训练失败:
  - 设备以 USB 2.0 速率运行 → speed 显示 480 而非 5000
  - dmesg: "usb 2-1: device descriptor read, error -110"

排查:
  1. 确认使用 USB 3.0 线缆 (有额外的 SuperSpeed 线对)
  2. 确认 USB 3.0 PHY 初始化成功
  3. 检查 DTS 中是否使能了 USB 3.0
  4. 缩短线缆长度 (USB 3.0 对线长更敏感)
```

### 3.3 眼图分析
```
眼图 (Eye Diagram):
  - 评估 USB 信号质量的标准方法
  - 将大量 UI (Unit Interval) 叠加显示
  - 眼睛越大越好 (信号裕量越大)

眼图屏蔽区 (Mask):
  - USB 规范定义了眼图必须通过的屏蔽区
  - 信号不能进入屏蔽区内
  - 不同速率有不同的 mask 要求

嵌入式 PHY 调优:
  很多 SoC 的 USB PHY 提供以下可调参数:
  - TX 驱动强度 (impedance tuning)
  - TX 预加重 (pre-emphasis)
  - TX 幅度 (amplitude)
  - RX 均衡 (equalization)
  - 这些参数通常在 DTS 或 PHY 驱动中配置
```

## 4. 常见 PHY 芯片配置

### 4.1 Innosilicon USB2 PHY (Rockchip 常用)
```dts
&u2phy0 {
    status = "okay";
    u2phy0_host: host-port {
        phy-supply = <&vcc5v0_usb>;
        status = "okay";
    };
    u2phy0_otg: otg-port {
        status = "okay";
    };
};
```

### 4.2 Generic USB PHY (通用)
```dts
/* 通用 USB PHY 绑定 */
usb_phy: usb-phy@xxx {
    compatible = "vendor,usb-phy";
    reg = <0x0 0xxx 0x0 0x100>;
    clocks = <&cru CLK_USB_PHY>;
    clock-names = "phyclk";
    #phy-cells = <0>;
    resets = <&cru SRST_USB_PHY>;
    reset-names = "phy";
};

/* USB 控制器引用 PHY */
&usb_host {
    phys = <&usb_phy>;
    phy-names = "usb2-phy";
    status = "okay";
};
```

## 5. USB 电源域

```
USB 典型电源域:
  VBUS:   5V (主机提供给设备的供电)
  VDD33:  3.3V (PHY I/O 电源)
  VDD18:  1.8V (PHY 内核电源)
  VDD09:  0.9V (某些 USB 3.0 PHY 内核)

电源问题排查:
  - VBUS 电压不足 → 设备枚举失败
  - PHY 供电异常 → PHY 初始化失败
  - 电源纹波大 → 信号质量差

测量建议:
  - 万用表测 VBUS: 应为 4.75~5.25V
  - 示波器测 VDD 纹波: 应 < 50mV
  - 负载测试: 接重负载设备时 VBUS 是否跌落
```

# RK3588 多摄方案与 DPHY/DCPHY 链路配置

## 1. RK3588 Camera 硬件架构

### 1.1 接口资源总览

```
                    ┌─ csi2_dcphy0 (DPHY/CPHY 4L) ─→ mipi0_csi2
                    ├─ csi2_dcphy1 (DPHY/CPHY 4L) ─→ mipi1_csi2
                    ├─ csi2_dphy0  (dphy0_hw full 4L) ─→ mipi2_csi2
MIPI Sensors ──→    ├─ csi2_dphy1  (dphy0_hw split L0/1) ─→ mipi2_csi2
                    ├─ csi2_dphy2  (dphy0_hw split L2/3) ─→ mipi2_csi2
                    ├─ csi2_dphy3  (dphy1_hw full 4L) ─→ mipi4_csi2
                    ├─ csi2_dphy4  (dphy1_hw split L0/1) ─→ mipi4_csi2
DVP Sensor ──→      └─ csi2_dphy5  (dphy1_hw split L2/3) ─→ mipi4_csi2
                                                     ↓
                                                  VICAP (rkcif)
                                                     ↓ (sditf)
                                              rkisp0 / rkisp1
                                              (各4路虚拟设备)
```

### 1.2 最大支持 7 路 Sensor

6 MIPI + 1 DVP = 7 路，具体分配：
- 2 × DCPHY (dcphy0/dcphy1) = 2 路 4Lane
- dphy0_hw split = 2 路 2Lane
- dphy1_hw split = 2 路 2Lane
- 1 × DVP

### 1.3 DPHY 物理节点与逻辑节点对应

| 物理 HW | 工作模式 | 逻辑节点 | CSI Host | VICAP 逻辑节点 |
|---------|---------|---------|----------|---------------|
| csi2_dcphy0_hw | — | csi2_dcphy0 | mipi0_csi2 | rkcif_mipi_lvds |
| csi2_dcphy1_hw | — | csi2_dcphy1 | mipi1_csi2 | rkcif_mipi_lvds1 |
| csi2_dphy0_hw | Full | csi2_dphy0 | mipi2_csi2 | rkcif_mipi_lvds2 |
| csi2_dphy0_hw | Split | csi2_dphy1 (L0/1) | mipi2_csi2 | rkcif_mipi_lvds2 |
| csi2_dphy0_hw | Split | csi2_dphy2 (L2/3) | mipi2_csi2 | rkcif_mipi_lvds3 |
| csi2_dphy1_hw | Full | csi2_dphy3 | mipi4_csi2 | rkcif_mipi_lvds4 |
| csi2_dphy1_hw | Split | csi2_dphy4 (L0/1) | mipi4_csi2 | rkcif_mipi_lvds4 |
| csi2_dphy1_hw | Split | csi2_dphy5 (L2/3) | mipi4_csi2 | rkcif_mipi_lvds5 |
| — | DVP | — | — | rkcif_dvp |

### 1.4 Full Mode 配置特殊规则

当 dphy_hw 使用 Full Mode 时，**链路需按 Split Mode 第一条路来配置**，但节点名改为 Full Mode 名：
- dphy0_hw Full Mode: 使用 csi2_dphy1 的链路配置，但节点名用 csi2_dphy0
- dphy1_hw Full Mode: 使用 csi2_dphy4 的链路配置，但节点名用 csi2_dphy3

> 驱动通过 PHY 序号（dt 注册顺序）来区分 Full 和 Split 模式。

## 2. 多摄方案配置示例

### 2.1 双摄 (DCPHY0 + DPHY1_HW)

```dts
/* Sensor 0: IMX415 → dcphy0 → mipi0_csi2 → vicap → isp0 */
/* Sensor 1: OV5695 → dphy3(dphy1_hw full) → mipi4_csi2 → vicap → isp1 */

/* === Sensor 0 链路 === */
&csi2_dcphy0_hw { status = "okay"; };
&csi2_dcphy0 {
    status = "okay";
    ports {
        port@0 { dcphy0_in: endpoint { remote-endpoint = <&imx415_out>; data-lanes = <1 2 3 4>; }; };
        port@1 { dcphy0_out: endpoint { remote-endpoint = <&mipi0_csi2_input>; }; };
    };
};
&mipi0_csi2 {
    status = "okay";
    ports {
        port@0 { mipi0_csi2_input: endpoint { remote-endpoint = <&dcphy0_out>; }; };
        port@1 { mipi0_csi2_output: endpoint { remote-endpoint = <&cif_mipi_in0>; }; };
    };
};
&rkcif { status = "okay"; };
&rkcif_mmu { status = "okay"; };
&rkcif_mipi_lvds {
    status = "okay";
    port { cif_mipi_in0: endpoint { remote-endpoint = <&mipi0_csi2_output>; }; };
};
&rkcif_mipi_lvds_sditf {
    status = "okay";
    port { mipi_lvds_sditf: endpoint { remote-endpoint = <&isp0_vir0>; }; };
};
&rkisp0 { status = "okay"; };
&isp0_mmu { status = "okay"; };
&rkisp0_vir0 {
    status = "okay";
    port { isp0_vir0: endpoint@0 { reg = <0>; remote-endpoint = <&mipi_lvds_sditf>; }; };
};

/* === Sensor 1 链路 === */
&csi2_dphy1_hw { status = "okay"; };
&csi2_dphy3 {
    status = "okay";
    ports {
        port@0 { dphy3_in: endpoint { remote-endpoint = <&ov5695_out>; data-lanes = <1 2>; }; };
        port@1 { dphy3_out: endpoint { remote-endpoint = <&mipi4_csi2_input>; }; };
    };
};
&mipi4_csi2 {
    status = "okay";
    ports {
        port@0 { mipi4_csi2_input: endpoint { remote-endpoint = <&dphy3_out>; }; };
        port@1 { mipi4_csi2_output: endpoint { remote-endpoint = <&cif_mipi_in4>; }; };
    };
};
&rkcif_mipi_lvds4 {
    status = "okay";
    port { cif_mipi_in4: endpoint { remote-endpoint = <&mipi4_csi2_output>; }; };
};
&rkcif_mipi_lvds4_sditf {
    status = "okay";
    port { mipi4_lvds_sditf: endpoint { remote-endpoint = <&isp1_vir0>; }; };
};
&rkisp1 { status = "okay"; };
&isp1_mmu { status = "okay"; };
&rkisp1_vir0 {
    status = "okay";
    port { isp1_vir0: endpoint@0 { reg = <0>; remote-endpoint = <&mipi4_lvds_sditf>; }; };
};
```

### 2.2 四摄 (dphy0_hw split + dphy1_hw split)

```dts
/* 每个 dphy_hw 拆分为 2×2Lane，共接 4 个 2Lane sensor */
/* Sensor 0 → csi2_dphy1 (dphy0_hw L0/1) → mipi2_csi2 → rkcif_mipi_lvds2 → isp0_vir0 */
/* Sensor 1 → csi2_dphy2 (dphy0_hw L2/3) → mipi2_csi2 → rkcif_mipi_lvds3 → isp0_vir1 */
/* Sensor 2 → csi2_dphy4 (dphy1_hw L0/1) → mipi4_csi2 → rkcif_mipi_lvds4 → isp1_vir0 */
/* Sensor 3 → csi2_dphy5 (dphy1_hw L2/3) → mipi4_csi2 → rkcif_mipi_lvds5 → isp1_vir1 */

&csi2_dphy0_hw { status = "okay"; };
&csi2_dphy1 {
    status = "okay";
    ports {
        port@0 { dphy1_in: endpoint { remote-endpoint = <&sensor0_out>; data-lanes = <1 2>; }; };
        port@1 { dphy1_out: endpoint { remote-endpoint = <&mipi2_csi2_input>; }; };
    };
};
&csi2_dphy2 {
    status = "okay";
    ports {
        port@0 { dphy2_in: endpoint { remote-endpoint = <&sensor1_out>; data-lanes = <1 2>; }; };
        port@1 { dphy2_out: endpoint { remote-endpoint = <&mipi2_csi2_input2>; }; };
    };
};
/* mipi2_csi2 和后续 VICAP/ISP 链路类似，为每个 sensor 配置独立的 sditf 和 rkisp_vir 节点 */
```

### 2.3 ISP 虚拟设备复用限制

| 复用路数 | 单路最大分辨率 | 说明 |
|---------|-------------|------|
| 1 路 | 4672×3504 | 单 ISP 全能力 |
| 2 路 | 3840×2160 | 分时复用 |
| 3-4 路 | 2560×1536 | 分时复用 |

需要在 ISP 节点配置 `max-input` 告知复用时的最大分辨率：
```dts
&rkisp0 {
    status = "okay";
    /* 多摄 sensor 分辨率不一时须配置 */
    max-input = <2688 1520 30>;
};
```

## 3. 8K 双 ISP 合成

### 3.1 使用场景

当 Sensor 分辨率超过单 ISP 极限（>16M = 4672×3504）时，需要双 ISP 合成：
- 仅支持单摄
- VICAP 采集 8K 数据，左右分图送 2 个 ISP 处理，再合成输出

### 3.2 DTS 配置

```dts
/* 关闭独立 ISP */
&rkisp0 { status = "disabled"; };
&isp0_mmu { status = "disabled"; };
&rkisp1 { status = "disabled"; };
&isp1_mmu { status = "disabled"; };

/* 使能合成 ISP */
&rkisp_unite { status = "okay"; };
&rkisp_unite_mmu { status = "okay"; };

/* 虚拟设备引用 unite 节点 */
&rkisp0_vir0 {
    status = "okay";
    rockchip,hw = <&rkisp_unite>;
    port {
        isp0_vir0: endpoint@0 {
            reg = <0>;
            remote-endpoint = <&mipi_lvds_sditf>;
        };
    };
};
```

## 4. DCPHY 特性说明

### 4.1 DPHY vs CPHY

| 特性 | DPHY | CPHY |
|-----|------|------|
| 信号 | 差分对 (D+/D-) | 三线 (A/B/C) |
| 每 Lane 速率 | 2.5 Gbps | 2.5 Gsps (约 5.7 Gbps 等效) |
| RK3588 支持 | 4Lane DPHY | 3Lane CPHY |

### 4.2 DCPHY RX/TX 约束

- 同一 DCPHY 的 TX 和 RX 只能**同时使用 DPHY** 或**同时使用 CPHY**
- TX 用于 DSI 显示，RX 用于 CSI Camera
- 如果 TX 用 DPHY 输出 DSI，则该 DCPHY 的 RX 也只能用 DPHY 协议接 Camera

## 5. 多摄电源设计要点

### 5.1 电源独立性

```
建议方案:
- avdd (2.8V): 可共用，注意电流能力
- dovdd (1.8V): 可共用
- dvdd (1.2/1.5V): 建议独立供电
  └─ 原因: dvdd 是 sensor 核心数字电源，功率较大
           多 sensor 同时工作时瞬态电流可能导致电压塌陷
           影响图像质量，甚至不出图
```

### 5.2 GPIO 控制的 LDO 配置

```dts
/ {
    vcc_mipicsi0: vcc-mipicsi0-regulator {
        compatible = "regulator-fixed";
        gpio = <&gpio4 RK_PA6 GPIO_ACTIVE_HIGH>;
        pinctrl-names = "default";
        pinctrl-0 = <&mipicsi0_pwr>;
        regulator-name = "vcc_mipicsi0";
        enable-active-high;
    };
};

/* Sensor 中引用 */
&sensor {
    avdd-supply = <&vcc_mipicsi0>;
};
```

## 6. RK3588 Camera DTS 配置 Checklist

| # | 检查项 |
|---|-------|
| 1 | 物理 DPHY HW 节点使能 (csi2_dphy0_hw / csi2_dphy1_hw / csi2_dcphy0_hw) |
| 2 | 逻辑 DPHY 节点使能 (data-lanes 正确) |
| 3 | CSI Host 节点使能 (mipiX_csi2) 并正确链接 |
| 4 | VICAP 物理节点 (rkcif) 和 IOMMU (rkcif_mmu) 使能 |
| 5 | VICAP 逻辑节点 (rkcif_mipi_lvdsX) 正确链接 CSI Host |
| 6 | sditf 桥接节点正确链接 ISP 虚拟设备 |
| 7 | ISP 物理节点 (rkisp0/1) 和 IOMMU (ispX_mmu) 使能 |
| 8 | ISP 虚拟设备 (rkispX_virY) 正确链接 sditf |
| 9 | Full Mode 时使用 Split 链路配但改节点名 |
| 10 | Split Mode 时 Full Mode 节点 disabled |
| 11 | 多摄 sensor 的 module-index 不重复 |
| 12 | dvdd 电源独立供电 |

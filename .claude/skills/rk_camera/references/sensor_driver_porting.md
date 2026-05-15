# Sensor 驱动移植详解

## 1. 驱动文件结构

标准 Sensor 驱动文件位于 `drivers/media/i2c/`，以 ov5695.c 为参考模板。

### 1.1 必须包含的头文件

```c
#include <linux/clk.h>
#include <linux/device.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <linux/delay.h>
#include <media/media-entity.h>
#include <media/v4l2-async.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-subdev.h>
#include <linux/rk-camera-module.h>  /* Rockchip 特有 */
```

### 1.2 核心数据结构

```c
struct sensor_priv {
    struct i2c_client *client;
    struct clk *xvclk;
    struct gpio_desc *reset_gpio;
    struct gpio_desc *pwdn_gpio;
    struct regulator_bulk_data supplies[3];  /* avdd, dovdd, dvdd */
    
    struct v4l2_subdev subdev;
    struct media_pad pad;
    struct v4l2_ctrl_handler ctrl_handler;
    struct v4l2_ctrl *exposure;
    struct v4l2_ctrl *anal_gain;
    struct v4l2_ctrl *hblank;
    struct v4l2_ctrl *vblank;
    struct v4l2_ctrl *pixel_rate;
    struct v4l2_ctrl *link_freq;
    struct v4l2_ctrl *test_pattern;
    
    struct mutex mutex;
    bool streaming;
    const struct sensor_mode *cur_mode;
    struct v4l2_mbus_framefmt format;
    
    /* Rockchip 模组信息 */
    u32 module_index;
    const char *module_facing;
    const char *module_name;
    const char *len_name;
};
```

## 2. Probe 函数实现

### 2.1 完整 Probe 流程

```c
static int sensor_probe(struct i2c_client *client)
{
    struct sensor_priv *priv;
    struct v4l2_subdev *sd;
    int ret;
    
    /* 1. 分配私有数据 */
    priv = devm_kzalloc(&client->dev, sizeof(*priv), GFP_KERNEL);
    
    /* 2. 获取 DTS 资源 */
    priv->xvclk = devm_clk_get(&client->dev, "xvclk");
    priv->reset_gpio = devm_gpiod_get_optional(&client->dev, "reset", GPIOD_OUT_LOW);
    priv->pwdn_gpio = devm_gpiod_get_optional(&client->dev, "pwdn", GPIOD_OUT_LOW);
    
    /* 3. 获取 regulator */
    priv->supplies[0].supply = "avdd";   /* 模拟 2.8V */
    priv->supplies[1].supply = "dovdd";  /* IO 1.8V */
    priv->supplies[2].supply = "dvdd";   /* 核心 1.2/1.5V */
    devm_regulator_bulk_get(&client->dev, 3, priv->supplies);
    
    /* 4. 获取 Rockchip 模组信息 */
    of_property_read_u32(client->dev.of_node,
        "rockchip,camera-module-index", &priv->module_index);
    of_property_read_string(client->dev.of_node,
        "rockchip,camera-module-facing", &priv->module_facing);
    of_property_read_string(client->dev.of_node,
        "rockchip,camera-module-name", &priv->module_name);
    of_property_read_string(client->dev.of_node,
        "rockchip,camera-module-lens-name", &priv->len_name);
    
    /* 5. 上电并检查 chip ID */
    __sensor_power_on(priv);
    sensor_check_id(priv);
    __sensor_power_off(priv);
    
    /* 6. 初始化 V4L2 controls */
    sensor_init_controls(priv);
    
    /* 7. 注册 V4L2 subdev */
    sd = &priv->subdev;
    v4l2_i2c_subdev_init(sd, client, &sensor_subdev_ops);
    sd->flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
    priv->pad.flags = MEDIA_PAD_FL_SOURCE;
    media_entity_pads_init(&sd->entity, 1, &priv->pad);
    
    /* 8. 异步注册 (必须) */
    v4l2_async_register_subdev_sensor_common(sd);
    
    /* 9. PM Runtime */
    pm_runtime_set_active(&client->dev);
    pm_runtime_enable(&client->dev);
    pm_runtime_idle(&client->dev);
    
    return 0;
}
```

### 2.2 V4L2 Controls 初始化

```c
static int sensor_init_controls(struct sensor_priv *priv)
{
    struct v4l2_ctrl_handler *handler = &priv->ctrl_handler;
    const struct sensor_mode *mode = priv->cur_mode;
    
    v4l2_ctrl_handler_init(handler, 8);
    
    /* link freq (只读, 可枚举多个值) */
    priv->link_freq = v4l2_ctrl_new_int_menu(handler, NULL,
        V4L2_CID_LINK_FREQ, ARRAY_SIZE(link_freq_items) - 1,
        0, link_freq_items);
    if (priv->link_freq) priv->link_freq->flags |= V4L2_CTRL_FLAG_READ_ONLY;
    
    /* pixel rate (只读) */
    priv->pixel_rate = v4l2_ctrl_new_std(handler, NULL,
        V4L2_CID_PIXEL_RATE, 0, pixel_rate, 1, pixel_rate);
    if (priv->pixel_rate) priv->pixel_rate->flags |= V4L2_CTRL_FLAG_READ_ONLY;
    
    /* exposure */
    priv->exposure = v4l2_ctrl_new_std(handler, &sensor_ctrl_ops,
        V4L2_CID_EXPOSURE, 1, mode->vts_def - 4, 1, mode->exp_def);
    
    /* analogue gain */
    priv->anal_gain = v4l2_ctrl_new_std(handler, &sensor_ctrl_ops,
        V4L2_CID_ANALOGUE_GAIN, 0x10, 0xf8, 1, 0x10);
    
    /* vblank */
    priv->vblank = v4l2_ctrl_new_std(handler, &sensor_ctrl_ops,
        V4L2_CID_VBLANK, mode->vts_def - mode->height,
        0x7fff - mode->height, 1, mode->vts_def - mode->height);
    
    /* hblank (只读) */
    priv->hblank = v4l2_ctrl_new_std(handler, NULL,
        V4L2_CID_HBLANK, mode->hts_def - mode->width,
        mode->hts_def - mode->width, 1, mode->hts_def - mode->width);
    if (priv->hblank) priv->hblank->flags |= V4L2_CTRL_FLAG_READ_ONLY;
    
    /* test pattern */
    priv->test_pattern = v4l2_ctrl_new_std_menu_items(handler,
        &sensor_ctrl_ops, V4L2_CID_TEST_PATTERN,
        ARRAY_SIZE(test_pattern_menu) - 1, 0, 0, test_pattern_menu);
    
    priv->subdev.ctrl_handler = handler;
    return handler->error;
}
```

## 3. DTS 完整示例

### 3.1 RV1126 双摄 (MIPI 4Lane + MIPI 4Lane)

```dts
/* Sensor 0: OS04A10 → csi_dphy0 → ISP(VP0) */
&i2c1 {
    os04a10: os04a10@36 {
        compatible = "ovti,os04a10";
        reg = <0x36>;
        clocks = <&cru CLK_MIPICSI_OUT>;
        clock-names = "xvclk";
        avdd-supply = <&vcc_avdd>;
        dovdd-supply = <&vcc1v8_dvp>;
        dvdd-supply = <&vdd_dvdd0>;  /* dvdd 独立供电 */
        reset-gpios = <&gpio1 RK_PD5 GPIO_ACTIVE_HIGH>;
        pwdn-gpios = <&gpio1 RK_PD4 GPIO_ACTIVE_HIGH>;
        rockchip,camera-module-index = <0>;
        rockchip,camera-module-facing = "back";
        rockchip,camera-module-name = "CMK-OT1607-FV1";
        rockchip,camera-module-lens-name = "M12-4IR-4MP-F16";
        ir-cut = <&cam_ircut0>;
        port {
            ucam_out0: endpoint {
                remote-endpoint = <&mipi_in_ucam0>;
                data-lanes = <1 2 3 4>;
            };
        };
    };
};

/* Sensor 1: OS04A10 → csi_dphy1 → ISP(VP1) */
&i2c3 {
    os04a10_1: os04a10@36 {
        compatible = "ovti,os04a10";
        reg = <0x36>;
        clocks = <&cru CLK_MIPICSI_OUT>;
        clock-names = "xvclk";
        avdd-supply = <&vcc_avdd>;
        dovdd-supply = <&vcc1v8_dvp>;
        dvdd-supply = <&vdd_dvdd1>;  /* dvdd 独立供电! */
        reset-gpios = <&gpio3 RK_PA6 GPIO_ACTIVE_HIGH>;
        rockchip,camera-module-index = <1>;
        rockchip,camera-module-facing = "front";
        rockchip,camera-module-name = "CMK-OT1607-FV1";
        rockchip,camera-module-lens-name = "M12-4IR-4MP-F16";
        ir-cut = <&cam_ircut1>;
        port {
            ucam_out1: endpoint {
                remote-endpoint = <&mipi_in_ucam1>;
                data-lanes = <1 2 3 4>;
            };
        };
    };
};

&csi_dphy0 {
    status = "okay";
    ports {
        port@0 { mipi_in_ucam0: endpoint@1 { reg = <1>; remote-endpoint = <&ucam_out0>; data-lanes = <1 2 3 4>; }; };
        port@1 { csidphy0_out: endpoint@0 { reg = <0>; remote-endpoint = <&isp_in>; }; };
    };
};

&csi_dphy1 {
    status = "okay";
    ports {
        port@0 { mipi_in_ucam1: endpoint@1 { reg = <1>; remote-endpoint = <&ucam_out1>; data-lanes = <1 2 3 4>; }; };
        port@1 { csidphy1_out: endpoint@0 { reg = <0>; remote-endpoint = <&mipi_lvds_sditf>; }; };
    };
};
```

### 3.2 RK3568 三摄 (1×4Lane + Split 2×2Lane)

```dts
/* Sensor 0: GC8034 → csi2_dphy0 (Full Mode 4L) → ISP */
&csi2_dphy_hw { status = "okay"; };
&csi2_dphy0 {
    status = "okay";
    /* csi2_dphy0 = Full Mode, 与 dphy1/dphy2 互斥 */
    ports {
        port@0 { dphy0_in: endpoint { remote-endpoint = <&gc8034_out>; data-lanes = <1 2 3 4>; }; };
        port@1 { dphy0_out: endpoint { remote-endpoint = <&isp0_in>; }; };
    };
};

/* Sensor 1: OV5695 → csi2_dphy1 (Split Mode, lane0/1) */
/* Sensor 2: OV2685 → csi2_dphy2 (Split Mode, lane2/3) */
/* Split Mode 时 csi2_dphy0 必须 disabled */
```

### 3.3 RK3588 DCPHY 使用示例

```dts
/* DCPHY 同时支持 DPHY 和 CPHY 协议 */
/* 同一 DCPHY 的 TX/RX 必须同时使用 DPHY 或同时使用 CPHY */
&csi2_dcphy0_hw { status = "okay"; };
&csi2_dcphy0 {
    status = "okay";
    ports {
        port@0 { dcphy0_in: endpoint { remote-endpoint = <&sensor_out>; data-lanes = <1 2 3 4>; }; };
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
/* 后续链路: rkcif_mipi_lvds0 → sditf → rkisp0_vir0 (同标准RK3588链路) */
```

## 4. Sensor 驱动移植 Checklist

| # | 检查项 | 确认方法 |
|---|-------|---------|
| 1 | compatible 字符串匹配 | grep compatible driver.c, dts |
| 2 | I2C 地址 7-bit | reg = <addr/2> |
| 3 | xvclk 频率正确 | clk_get_rate() 打印 |
| 4 | 上电顺序符合 datasheet | 示波器抓时序 |
| 5 | chip ID 读取正确 | dmesg 日志 |
| 6 | link_freq 配置正确 | 公式计算或原厂确认 |
| 7 | data-lanes 数量一致 | sensor DTS 和 dphy DTS 都要配 |
| 8 | mbus_code 格式正确 | RGGB/BGGR/GBRG/GRBG 对应 |
| 9 | 寄存器列表完整 | REG_NULL 结束标志 |
| 10 | v4l2_subdev_ops 回调完整 | 至少 6 个回调 |
| 11 | module-index 不重复 | 多 sensor 时检查 |
| 12 | DT binding 文档 | Documentation/devicetree/bindings/media/i2c/ |

## 5. HDR Sensor 驱动移植要点

### 5.1 多 Pad 配置

HDR Sensor 需要通过多个 Virtual Channel 输出不同曝光帧，驱动需要：

```c
/* 定义多个 pad */
#define PAD_SINK    0
#define PAD_SRC0    1  /* VC0 - 短曝光 */
#define PAD_SRC1    2  /* VC1 - 长曝光 (或中曝光) */
#define PAD_SRC2    3  /* VC2 - 长曝光 */

/* get_fmt 需要为每个 pad 返回正确的分辨率和格式 */
static int sensor_get_fmt(struct v4l2_subdev *sd,
    struct v4l2_subdev_pad_config *cfg,
    struct v4l2_subdev_format *fmt)
{
    if (fmt->pad == PAD_SRC0)
        /* 短帧格式 */;
    else if (fmt->pad == PAD_SRC1)
        /* 中帧/长帧格式 */;
    /* ... */
}
```

### 5.2 rkmodule_hdr_cfg

```c
static int sensor_ioctl(struct v4l2_subdev *sd, unsigned int cmd, void *arg)
{
    switch (cmd) {
    case RKMODULE_GET_HDR_CFG:
        /* 返回 HDR 模式: NO_HDR / HDR_X2 / HDR_X3 */
        break;
    case RKMODULE_SET_HDR_CFG:
        /* 切换 HDR 模式 */
        break;
    case PREISP_CMD_SET_HDRAE_EXP:
        /* 设置 HDR 曝光参数 */
        break;
    }
}
```

---
name: rk_isp
description: "Rockchip 瑞芯微平台 ISP 图像信号处理与调优技能。覆盖 ISP20/ISP21/ISP30/ISP32-lite 全系列 ISP 的图像质量调优 (IQ Tuning)、3A 算法 (AE/AWB/AF)、IQ XML 文件配置、RkAiq 软件框架与 API、ISP 各处理模块参数调试、色彩优化、降噪、HDR 图像处理。触发关键词包括但不限于：ISP、ISP20、ISP21、ISP30、ISP32、RKISP、RkAiq、rkaiq、3A、AE、AEC、AWB、AF、自动曝光、自动白平衡、自动聚焦、IQ 文件、IQ XML、iqfiles、图像调优、tuning、Tuner 工具、image quality、画质、降噪、NR、去噪、BNR、YNR、UVNR、CNR、3DNR、TNR、SHP、锐化、sharpen、BLC、黑电平、LSC、镜头阴影校正、lens shading、CCM、色彩校正矩阵、Gamma、DRC、动态范围压缩、DEHAZE、去雾、DPC、坏点校正、GIC、LDCH、畸变校正、FEC、WDR、HDR 合成、曝光融合、色偏、偏色、偏绿、偏红、偏蓝、噪点多、过曝、欠曝、暗角、色彩还原、白平衡不准、3A server、rkisp_3A_server、camera_engine_rkaiq、标定、calibration、OTP。当用户提到 Rockchip 平台的 ISP 图像处理、画质调优、3A 参数调试、IQ 文件相关问题时触发本技能。Camera 采集和 sensor 驱动请使用 rk_camera 技能。"
---

# Rockchip ISP 图像处理与调优技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| 画质调优从何开始 | §3 调优总体流程 |
| AE 曝光问题 (过曝/欠曝/闪烁) | §4.1 |
| AWB 色偏问题 (偏绿/偏红/偏蓝) | §4.2 |
| 降噪参数调整 | §4.4 |
| IQ XML 文件配置 | §5 |
| RkAiq API 使用 | §6 |
| 自定义 3A 算法开发 | §6.3 |
| ISP Tuner 工具使用 | §5.2 |
| HDR 调优 | §3.2 |
| 常见画质问题诊断 | §7 |

---

## 1. ISP 系统架构

### 1.1 ISP 版本与平台对应

| ISP 版本 | 适用芯片 | 特有功能 |
|---------|---------|---------|
| ISP20 (ISP+ISPP) | RV1126/RV1109 | ISPP 后处理 (TNR/NR/SHP/FEC) |
| ISP21 | RK3568 | 集成 2帧 HDR |
| ISP21 Lite | RK3566 | 无 HDR |
| ISP30 | RK3588 | 3帧 HDR, 双 ISP 合成 8K |
| ISP32-Lite | RV1106 | 轻量级, 2帧 HDR |

### 1.2 ISP 功能框图 (ISP30)

```
RAW Data ─→ BLC ─→ DPC ─→ LSC ─→ AWB Gain ─→ BNR ─→ CCM ─→ Gamma ─→ DRC
                                                              ↓
            ← LDCH/FEC ← SHP ← YNR/CNR ← CSM ← 3DLUT ← DEHAZE ← A3DLUT
                                                              ↓
                                                          YUV Output
```

### 1.3 关键模块说明

| 模块 | 功能 | 调优场景 |
|------|------|---------|
| BLC | 黑电平校正 | 暗部偏色/暗场噪声 |
| DPC | 坏点校正 | 亮/暗固定坏点 |
| LSC | 镜头阴影校正 | 四角暗角/偏色 |
| AWB | 自动白平衡 | 色温适应/色偏 |
| BNR | Bayer 域降噪 | Raw 域噪声 |
| CCM | 色彩校正矩阵 | 色彩还原准确度 |
| Gamma | 伽马校正 | 亮度映射/对比度 |
| DRC | 动态范围压缩 | HDR/逆光场景 |
| DEHAZE | 去雾 | 雾天/低对比度 |
| 3DLUT | 三维查找表 | 精细色彩调整 |
| YNR | 亮度域降噪 | Y 通道噪声 |
| CNR | 色度域降噪 | 彩色噪声 |
| SHP | 锐化 | 边缘增强 |
| LDCH/FEC | 畸变校正 | 镜头畸变 |

### 1.4 软件架构

```
┌─────────────────────────────────────────┐
│            应用层 (Application)           │
│  RkAiq API (rk_aiq_uapi2_xxx)           │
├─────────────────────────────────────────┤
│         camera_engine_rkaiq              │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ AEC  │ │ AWB  │ │  AF  │ │ ANR  │...│
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘   │
│     └────────┴────────┴────────┘         │
│              AIQ Core                    │
├─────────────────────────────────────────┤
│           Kernel ISP Driver              │
│  isp_params ←→ isp_stats                │
│  (参数下发)     (统计上报)                │
├─────────────────────────────────────────┤
│          ISP Hardware                    │
└─────────────────────────────────────────┘
```

---

## 2. RkAiq 工作流程

### 2.1 初始化流程

```
rk_aiq_uapi2_sysctl_preInit()    ← 预初始化 (可选, 设置 HDR 模式等)
        ↓
rk_aiq_uapi2_sysctl_init()       ← 初始化 (绑定 sensor, 加载 IQ 文件)
        ↓
rk_aiq_uapi2_sysctl_prepare()    ← 准备 (配置分辨率等)
        ↓
rk_aiq_uapi2_sysctl_start()      ← 启动 3A 处理
        ↓
    ... 运行中 (Stats → Algo → Params 循环) ...
        ↓
rk_aiq_uapi2_sysctl_stop()       ← 停止
        ↓
rk_aiq_uapi2_sysctl_deinit()     ← 反初始化
```

### 2.2 工作模式

```c
typedef enum {
    RK_AIQ_WORKING_MODE_NORMAL   = 0,  /* 线性模式 */
    RK_AIQ_WORKING_MODE_ISP_HDR2 = 0x10, /* 2帧HDR */
    RK_AIQ_WORKING_MODE_ISP_HDR3 = 0x20, /* 3帧HDR */
} rk_aiq_working_mode_t;
```

### 2.3 rkisp_3A_server 启动与 IQ 文件

```bash
# 自动启动 (SDK 默认)
# 系统服务启动 rkisp_3A_server

# 手动启动
rkisp_3A_server --mmedia=/dev/media0 &

# IQ 文件自动匹配路径
# /etc/iqfiles/{sensor}_{module-name}_{lens-name}.xml
# 例: /etc/iqfiles/os04a10_CMK-OT1607-FV1_M12-4IR-4MP-F16.xml

# 开启 3A log
export persist_camera_engine_log=0xff
rkisp_3A_server --mmedia=/dev/media0 &
```

---

## 3. 图像调优总体流程

### 3.1 线性模式调优步骤

```
1. BLC 标定     ← 暗场拍摄, 消除黑电平偏移
2. LSC 标定     ← 均匀光源拍摄, 消除暗角和色偏
3. AWB 标定     ← 多色温标准光源拍摄, 建立色温模型
4. CCM 标定     ← ColorChecker 24色卡拍摄, 建立色彩校正矩阵
5. Gamma 调整   ← 根据应用场景选择曲线
6. AE 参数调整   ← 曝光策略/收敛速度/防闪烁
7. NR 标定      ← 不同 ISO/增益下拍噪声图, 建立降噪强度曲线
8. SHP 调整     ← 锐度与噪声平衡
9. DRC/DEHAZE   ← 逆光/雾天场景优化
10. FEC/LDCH    ← 畸变校正 (需标定板)
```

### 3.2 HDR 模式额外调优

在线性调优基础上增加：
- **ExpRatioCtrl** — 长短帧曝光比控制
- **MergeV30** — HDR 合成参数 (短帧/长帧融合权重)
- **DRC** — 动态范围压缩参数 (HDR tone mapping)
- **TMO** — Tone Mapping 参数

---

## 4. 核心模块调优参数

### 4.1 AEC (自动曝光控制)

**关键参数：**

| 参数 | 作用 | 典型值 |
|------|------|-------|
| AecOpType | Auto/Manual 模式选择 | 0=Auto |
| AecSpeed | 曝光收敛速度 | 中速适合大多数场景 |
| AecDelayFrmNum | 曝光生效延迟帧数 | 与 sensor 相关 |
| AecAntiFlicker | 防闪烁 (50Hz/60Hz) | 按地区选择 |
| AecFrameRateMode | 帧率模式 | Auto=自动降帧 |
| HistStatsMode | 直方图统计模式 | — |
| RawStatsMode | Raw 统计模式 | — |

**线性模式特有参数：**

| 参数 | 作用 |
|------|------|
| ToleranceIn/Out | 曝光收敛容忍度 |
| EvBias | 曝光偏移 (整体偏亮/偏暗) |
| StrategyMode | 曝光策略 (低照/高光) |
| Route | 曝光路由表 (gain/time 分配) |
| DySetpoint | 动态目标亮度 |
| BackLightCtrl | 逆光补偿 |
| OverExpCtrl | 过曝控制 |

**HDR 模式特有参数：**

| 参数 | 作用 |
|------|------|
| ExpRatioCtrl | 长短帧曝光比 |
| LongFrmMode | 长帧模式 |
| LframeCtrl/MframeCtrl/SframeCtrl | 各帧独立控制 |

### 4.2 AWB (自动白平衡)

**核心调优要点：**

1. **标定**: 使用标准光源 (D65/D50/TL84/A/H/CWF) 拍摄 Raw 图
2. **白点检测流程**: RGB2XY → XY Domain → UV Domain → RGB2RYUV → RYUV Domain
3. **分区策略**: 通过光源权重和亮度权重计算最终 WBGain
4. **色适应调整**: 不同色温下的增益微调
5. **WBGain 范围限制**: 防止极端场景下白平衡跑飞

**常用 API：**
```c
/* 手动设置白平衡增益 */
rk_aiq_wb_gain_t gain = {1.0, 1.0, 1.0, 1.0}; /* R/GR/GB/B */
rk_aiq_uapi2_setWBMode(ctx, OP_MANUAL);
rk_aiq_uapi2_setMWBGain(ctx, &gain);

/* 自动白平衡 */
rk_aiq_uapi2_setWBMode(ctx, OP_AUTO);
```

**AWB 问题排查：**
```bash
# 抓取 AWB log
export persist_camera_engine_log=0x40  # AWB bit
# AWB log 显示: curWBGain, curCT (色温), 白点统计
```

### 4.3 CCM (色彩校正矩阵)

**标定流程：**
1. 使用 ColorChecker 24 色卡
2. 在多个色温下拍摄 Raw 图
3. 在 Tuner 工具中执行 CCM 标定
4. 生成多组 CCM 矩阵 (对应不同色温)
5. ISP 运行时根据 AWB 色温插值选择 CCM

### 4.4 降噪 (NR)

**降噪模块层次：**

| 层级 | 模块 | 域 | 说明 |
|-----|------|---|------|
| 1 | BNR (Bayer NR) | Raw | 在 demosaic 前降噪 |
| 2 | YNR | Y (亮度) | 亮度通道空域降噪 |
| 3 | CNR / UVNR | UV (色度) | 色度通道降噪 |
| 4 | TNR (3DNR) | 时域 | 帧间时域降噪 (仅 ISPP) |

**典型参数范围与调优建议 (ISP30)：**

| 模块 | 关键参数 | 低增益(≤4×) | 中增益(4-16×) | 高增益(≥16×) | 注意 |
|------|---------|-------------|-------------|-------------|------|
| BNR | filtPara.iso[].filtStr | 0.1~0.3 | 0.3~0.6 | 0.6~1.0 | 过强导致 demosaic 伪彩 |
| BNR | filtPara.iso[].lumaWeight | 0.5~0.8 | 0.8~1.0 | 1.0 | 亮度加权降噪 |
| YNR | ynr_global_gain_alpha | 0.0~0.3 | 0.3~0.6 | 0.6~1.0 | 全局降噪强度比例 |
| YNR | ynr_nlm_strong[0-4] | 1~10 | 10~30 | 30~63 | 各频段 NLM 强度，[0]=低频 |
| CNR | cnr_gain | 0.0~0.2 | 0.2~0.5 | 0.5~1.0 | 色度降噪整体强度 |
| CNR | cnr_uvgain | 1.0~2.0 | 2.0~4.0 | 4.0~8.0 | UV 通道增益 |
| SHP | sharpStrength | 0.5~1.5 | 0.3~1.0 | 0.1~0.5 | 高增益需降低锐化避免噪声放大 |

> 参数名因 ISP 版本有差异 (ISP20/21/30)，以 IQ XML 中实际标签为准。

**标定环境要求：**
- **灰卡**：18% 灰度标准灰卡，覆盖画面 60%+
- **光源**：D65 标准光源箱 (亮度可调)
- **增益遍历**：以 1 stop (2×) 为步长，从 1× 到最大 analog gain
- **评估方法**：PSNR / SSIM 定量评估 + 主观评价双重确认
- **平衡原则**：降噪强度以"不出现明显涂抹"为上限

**标定方法：**
1. 在不同 ISO/gain 下拍摄灰卡
2. Tuner 工具中进行 NR 标定
3. 建立 gain → 降噪强度的映射曲线
4. 平衡降噪强度与细节保留

### 4.5 其他关键模块

| 模块 | 调优要点 |
|------|---------|
| Gamma | sRGB/BT709/自定义曲线, 影响整体亮度和对比度 |
| DRC | compressMode, Range, Scale; HDR 场景核心参数 |
| DEHAZE | 去雾强度/范围; 雾天/低对比度场景 |
| LSC | 需标定; 多色温暗角补偿; 补偿过度会引入边缘噪声 |
| SHP | sharpen 强度/半径; 过锐化产生伪影 |
| LDCH/FEC | 需标定板拍摄; 畸变校正系数 |
| 3DLUT | 精细色彩微调, 通常在 CCM 之后 |
| DPC | 静态坏点表 + 动态坏点检测 |

---

## 5. IQ 文件与 Tuner 工具

### 5.1 IQ XML 文件结构

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CamCalibDbV2 xmlns="http://www.rkisp.com/CamCalibDbV2">
    <header>
        <sensor_name>os04a10</sensor_name>
        <module_name>CMK-OT1607-FV1</module_name>
        <lens_name>M12-4IR-4MP-F16</lens_name>
    </header>
    <AEC> ... </AEC>           <!-- 自动曝光参数 -->
    <AWB> ... </AWB>           <!-- 自动白平衡参数 -->
    <CCM> ... </CCM>           <!-- 色彩校正矩阵 -->
    <BLC> ... </BLC>           <!-- 黑电平校正 -->
    <LSC> ... </LSC>           <!-- 镜头阴影校正 -->
    <NR> ... </NR>             <!-- 降噪参数 -->
    <Sharp> ... </Sharp>       <!-- 锐化参数 -->
    <Gamma> ... </Gamma>       <!-- 伽马曲线 -->
    <DRC> ... </DRC>           <!-- 动态范围压缩 -->
    <Dehaze> ... </Dehaze>     <!-- 去雾参数 -->
    <LDCH> ... </LDCH>         <!-- 畸变校正 -->
    <!-- ... 更多模块 ... -->
</CamCalibDbV2>
```

### 5.2 ISP Tuner 工具使用

**环境准备：**
1. PC 端安装 RKISP Tuner 工具
2. 板端与 PC 通过网络连接
3. 板端启动 rkaiq 服务

**典型工作流：**
```
1. 选择平台 → 配置网络地址 → 连接板端
2. 新建/加载 IQ 文件
3. 配置 Sensor Information
4. 使用 Capture Tool 抓 Raw 图
5. 执行各模块标定 (BLC → LSC → AWB → CCM → NR)
6. 在线调试 → 实时预览效果
7. 保存 IQ 文件 → 部署到板端
```

### 5.3 IQ 文件匹配规则

```
# 文件名格式:
{sensor_name}_{module_name}_{lens_name}.xml

# DTS 中的属性:
rockchip,camera-module-name = "CMK-OT1607-FV1";       → module_name
rockchip,camera-module-lens-name = "M12-4IR-4MP-F16"; → lens_name
sensor compatible = "ovti,os04a10";                    → sensor_name

# 搜索路径:
/etc/iqfiles/
/usr/share/iqfiles/

# 匹配优先级:
1. sensor + module + lens 完全匹配
2. sensor 匹配 (module/lens 用默认)
```

---

## 6. RkAiq API 参考

### 6.1 系统控制 API

```c
#include "rk_aiq_uapi2_sysctl.h"

/* 初始化 */
rk_aiq_sys_ctx_t *ctx;
rk_aiq_uapi2_sysctl_init(sns_ent_name, iq_file_dir, NULL, NULL, &ctx);
rk_aiq_uapi2_sysctl_prepare(ctx, width, height, working_mode);
rk_aiq_uapi2_sysctl_start(ctx);

/* 运行时动态更新 IQ */
rk_aiq_uapi2_sysctl_updateIq(ctx, iq_file_path);

/* 查询绑定的 sensor */
rk_aiq_uapi2_sysctl_getBindedSnsEntNmByVd(video_node);

/* 获取静态能力信息 */
rk_aiq_static_info_t info;
rk_aiq_uapi2_sysctl_getStaticMetas(sns_ent_name, &info);
```

### 6.2 常用模块 API

```c
/* AE */
#include "rk_aiq_uapi2_ae.h"
rk_aiq_uapi2_setExpMode(ctx, mode);       /* Auto/Manual */
rk_aiq_uapi2_setExpGainRange(ctx, &range);
rk_aiq_uapi2_setExpTimeRange(ctx, &range);

/* AWB */
#include "rk_aiq_uapi2_awb.h"
rk_aiq_uapi2_setWBMode(ctx, mode);
rk_aiq_uapi2_setMWBGain(ctx, &gain);
rk_aiq_uapi2_setMWBCT(ctx, ct);           /* 手动设置色温 */

/* NR */
rk_aiq_uapi2_setStrength(ctx, algo_type, level);  /* 降噪强度 0-100 */

/* Gamma */
rk_aiq_uapi2_setGammaCoef(ctx, &gamma_attr);

/* 补光灯控制 */
rk_aiq_uapi2_sysctl_setCpsLtCfg(ctx, &cpsl_cfg);
```

### 6.3 自定义 3A 算法开发

**开发模式：** 注册自定义算法替换内置 3A

```c
/* 自定义 AE 算法 */
rk_aiq_uapi2_customAE_register(ctx, &custom_ae_cbs);
rk_aiq_uapi2_customAE_enable(ctx, true);

/* 回调函数 */
typedef struct {
    int (*pfn_ae_init)(void *ctx);
    int (*pfn_ae_run)(void *ctx, const ae_stats_t *stats, ae_result_t *result);
    int (*pfn_ae_ctrl)(void *ctx, uint32_t cmd, void *param);
    int (*pfn_ae_exit)(void *ctx);
} custom_ae_cbs_t;

/* 自定义 AWB 算法 - 类似 */
rk_aiq_uapi_customAWB_register(ctx, &custom_awb_cbs);
rk_aiq_uapi_customAWB_enable(ctx, true);

/* 自定义 AF 算法 */
/* AF 统计模块: Focus Filter → Gamma → Luma/Highlight → Fv Calc */
/* 需配置 AF 统计窗口和 Filter 参数 */
```

### 6.4 离线帧处理

```c
/* 读取 RK-RAW 格式文件, 送入 ISP 处理 */
/* 用于: PC 端调试 / 工厂校准 / 算法验证 */
/* 支持格式: 8/10/12/16-bit RAW, CompactRAW */
```

---

## 7. 常见画质问题诊断

### 7.1 诊断决策树

```
画质问题
├── 整体偏暗/过曝
│   ├── 检查 AEC 参数 (EvBias, DySetpoint, Route)
│   ├── 检查 Gamma 曲线
│   └── 检查 sensor exposure/gain 范围
│
├── 偏色 (偏绿/偏红/偏蓝)
│   ├── AWB 标定是否覆盖当前色温
│   ├── CCM 矩阵是否正确
│   ├── BLC 是否标定 (暗部偏色)
│   └── LSC 标定 (边缘偏色)
│
├── 噪点多
│   ├── 检查 NR 参数 vs gain 映射
│   ├── 高增益下 BNR/YNR/CNR 强度
│   ├── TNR 是否启用 (ISPP 平台)
│   └── BLC 不准导致暗部噪声放大
│
├── 画面模糊/不清晰
│   ├── AF 是否聚焦
│   ├── SHP 锐化参数
│   ├── NR 降噪过强导致细节丢失
│   └── LSC 过补偿导致边缘模糊
│
├── 暗角 / 四角偏色
│   ├── LSC 未标定或标定不准
│   └── 镜头品质问题
│
├── 色彩不准 / 色彩饱和度异常
│   ├── CCM 标定
│   ├── 3DLUT 配置
│   └── Gamma 曲线影响
│
├── HDR 画面异常 (鬼影/色阶断裂)
│   ├── MergeV30 融合参数
│   ├── DRC 参数
│   ├── ExpRatioCtrl 曝光比
│   └── 运动场景鬼影抑制
│
└── 闪烁 / flicker
    ├── AecAntiFlicker 配置 (50Hz/60Hz)
    └── 光源频率与帧率匹配
```

### 7.2 快速排查命令

```bash
# 确认 3A 是否运行
ps aux | grep rkisp_3A_server
ps aux | grep rkaiq

# 确认 IQ 文件是否正确加载
ls /etc/iqfiles/
# 检查 sensor 名称与 IQ 文件是否匹配

# 查看 ISP params/stats 是否正常
cat /proc/interrupts | grep isp
# params 中断和 stats 中断应持续增长

# 手动曝光测试 (排除 AE 问题)
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl exposure=2000
v4l2-ctl -d /dev/v4l-subdev2 --set-ctrl analogue_gain=100

# ISP debug
echo 0xff > /sys/module/video_rkisp/parameters/debug

# camera_engine_rkaiq log
export persist_camera_engine_log=0xff
# log 位置: /tmp/rkaiq_log/
```

---

## 8. 深入参考

| 主题 | 参考文件 |
|------|---------|
| ISP 模块详细参数与标定方法 | → [isp_module_tuning.md](references/isp_module_tuning.md) |
| RkAiq API 完整参考与代码示例 | → [rkaiq_api_reference.md](references/rkaiq_api_reference.md) |

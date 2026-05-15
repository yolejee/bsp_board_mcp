# ISP 模块详细参数与标定方法

## 1. BLC (Black Level Correction) 黑电平校正

### 1.1 原理
Sensor 输出的 RAW 数据在完全遮光时不为 0，存在黑电平偏移。BLC 模块减去此偏移值。

### 1.2 标定方法
1. 遮挡镜头 (完全暗场)
2. 拍摄 RAW 图
3. 计算 R/Gr/Gb/B 四通道的平均值
4. 填入 IQ 文件的 BLC 参数

### 1.3 注意事项
- BLC 不准会导致暗部偏色和噪声放大
- 不同 sensor gain 下 BLC 值可能不同
- 温度变化也会影响 BLC

```xml
<BLC>
    <BLC_Data>
        <ISO>50</ISO>
        <R>64</R>
        <Gr>64</Gr>
        <Gb>64</Gb>
        <B>64</B>
    </BLC_Data>
</BLC>
```

## 2. LSC (Lens Shading Correction) 镜头阴影校正

### 2.1 原理
镜头的光学特性导致图像边缘比中心暗(暗角),不同色温下暗角的颜色偏移也不同。

### 2.2 标定方法
1. 准备均匀光源 (积分球/灯箱)
2. 在多个色温下 (D65/TL84/A) 拍摄 RAW 图
3. 在 Tuner 工具中执行 LSC 标定
4. 工具自动计算各色温下的补偿增益表

### 2.3 标定要求
- 光源均匀度要求高 (中心与边缘亮度差 <5%)
- 必须覆盖常用色温
- 过度补偿会放大边缘噪声

### 2.4 IQ 参数结构
```xml
<LSC>
    <!-- 多组色温下的增益表 -->
    <LscTbl>
        <IlluminantName>D65</IlluminantName>
        <R_Gain>1.00 1.01 1.03 ... 1.25</R_Gain>   <!-- 17×17 网格 -->
        <Gr_Gain>...</Gr_Gain>
        <Gb_Gain>...</Gb_Gain>
        <B_Gain>...</B_Gain>
    </LscTbl>
</LSC>
```

## 3. AWB (Auto White Balance) 详细参数

### 3.1 标定流程
1. **准备标准光源**: D65 (6500K), D50 (5000K), TL84 (4000K), A (2856K), H (2300K), CWF (4150K)
2. **拍摄 RAW 图**: 每种光源下拍摄
3. **标定工具操作**:
   - 导入 RAW 图
   - 设置光源色温
   - 选取灰卡区域
   - 工具自动计算 RGB2XY 参数
4. **验证**: 在不同色温下检查白平衡效果

### 3.2 白点检测流程详解

```
原始像素 → RGB2XY 变换 → XY 域白点检测 (xy_region)
                       → UV 域白点检测 (uv_region)
         → RGB2RYUV 变换 → RYUV 域白点检测 (3dyuv_region)
                          → 非白点排除 (excRangeV201)
                          → 亮度加权 (lumaValueMatrix)
                          → 分块权重 (blkWeight)
                                    ↓
                              白点统计信息
                                    ↓
                          光源权重计算 → 分区策略 → WBGain
                                    ↓
                          色适应调整 → 范围限制 → 色调调整 → 平滑输出
```

### 3.3 常用参数调整

| 场景 | 参数 | 调整方向 |
|------|------|---------|
| 日光下偏蓝 | limitRange 中 D65 的 maxR/minR | 增大 R gain 范围 |
| 钨丝灯下偏黄 | limitRange 中 A 的 maxB/minB | 增大 B gain 范围 |
| 白平衡收敛慢 | tolerance | 增大容忍度 |
| 混合光源不稳 | 光源权重 weight | 调整各光源权重 |
| 绿色物体干扰 | excRangeV201 | 添加绿色排除区间 |

### 3.4 AWB Log 解读

```
AWB log 关键字段:
- curWBGain: 当前白平衡增益 (R/GR/GB/B)
- curCT: 当前估算色温 (K)
- wpNo: 各域检测到的白点数量
- lightSrc: 当前判定的光源类型
- converged: 白平衡是否收敛
```

## 4. CCM (Color Correction Matrix) 详细参数

### 4.1 标定流程
1. 使用 X-Rite ColorChecker Classic 24 色卡
2. 在 3 个以上色温下拍摄 (推荐 D65/TL84/A)
3. AWB 标定必须在 CCM 之前完成
4. Tuner 工具中选择色卡区域, 自动计算 3×3 矩阵

### 4.2 CCM 矩阵说明

```
┌─        ─┐   ┌─              ─┐   ┌─        ─┐
│ R_corrected │   │ C00  C01  C02 │   │ R_awb    │
│ G_corrected │ = │ C10  C11  C12 │ × │ G_awb    │
│ B_corrected │   │ C20  C21  C22 │   │ B_awb    │
└─        ─┘   └─              ─┘   └─        ─┘

约束: 每行之和应接近 1.0 (C00+C01+C02 ≈ 1.0)
对角线元素 > 1.0 (增强本通道)
非对角线元素 < 0 (减少串扰)
```

### 4.3 多色温 CCM 插值

ISP 运行时根据 AWB 估算的色温, 在多组 CCM 之间线性插值:

```
色温 2856K → CCM_A
色温 4000K → CCM_TL84
色温 5000K → CCM_D50
色温 6500K → CCM_D65

当前色温 4500K → 在 CCM_TL84 和 CCM_D50 之间插值
```

## 5. NR (Noise Reduction) 详细参数

### 5.1 标定方法
1. 在不同 ISO/gain 级别下拍摄灰卡 (18% gray)
2. 建议拍摄: gain=1x, 2x, 4x, 8x, 16x, 32x, 64x
3. 每个 gain 下拍摄 10 帧取平均
4. Tuner 工具自动计算各 gain 下的噪声水平

### 5.2 模块参数

**BNR (Bayer域降噪):**
```xml
<BNR>
    <Mode>0</Mode>  <!-- 0=Auto 1=Manual -->
    <ISO_list>50 100 200 400 800 1600 3200</ISO_list>
    <Strength>1.0 1.0 1.2 1.5 2.0 3.0 4.0</Strength>
    <EdgeSoftness>...</EdgeSoftness>
</BNR>
```

**YNR (亮度域降噪):**
- 低频降噪: 大面积平坦区域噪声
- 高频降噪: 细节区域噪声
- 需要平衡降噪强度与细节保留

**CNR (色度域降噪):**
- 去除彩色噪声 (紫边/绿边)
- 对色度通道滤波, 不影响亮度细节

**TNR (时域降噪, 仅 ISPP):**
- 利用帧间相关性降噪
- 运动检测 + 静态区域时域滤波
- 运动区域退化为空域降噪

### 5.3 降噪强度与细节的平衡

```
降噪不足                    降噪过强
   |                           |
噪点多 ←────────────────────→ 涂抹感
      最佳平衡点 (根据应用调整)

IPC监控: 偏向降噪 (画面干净)
手机拍照: 偏向细节 (纹理清晰)
```

## 6. Gamma / DRC / DEHAZE

### 6.1 Gamma
```
预设曲线:
- sRGB: 标准显示器
- BT709: 视频标准
- Linear: 线性
- 自定义: 256 点 LUT

调整方向:
- 暗部提升 → 暗处细节增加, 但噪声也增加
- 亮部压缩 → 高光细节保留
- 整体平移 → 调整画面整体亮度
```

### 6.2 DRC (Dynamic Range Compression)
```
用于 HDR 场景, 将高动态范围压缩到显示范围:
- compressMode: 压缩模式
- Range: 压缩范围
- Scale: 压缩比例

HDR 调优关键:
1. 先调 ExpRatioCtrl (长短帧比)
2. 再调 MergeV30 (融合参数)
3. 最后调 DRC (tone mapping)
```

### 6.3 DEHAZE (去雾)
```
参数:
- dehaze_en: 使能/禁用
- strength: 去雾强度 (0-100)
- air_light: 大气光估计
- trans_range: 透射率范围

适用场景:
- 雾天/霾天
- 低对比度环境
- 远距离监控
```

## 7. FEC/LDCH (畸变校正)

### 7.1 标定方法
1. 打印标定板 (棋盘格)
2. 拍摄标定板图像 (需覆盖画面 80% 以上)
3. Tuner 工具中选择标定功能
4. 自动检测角点, 计算畸变系数
5. 生成畸变校正映射表

### 7.2 FEC vs LDCH

| 特性 | LDCH | FEC |
|-----|------|-----|
| 位置 | ISP 内部 | ISPP 后处理 |
| 校正精度 | 中等 | 高 |
| 性能开销 | 小 | 大 (需要读写 DDR) |
| 适用平台 | 所有 ISP | ISPP 平台 (RV1126) |

## 8. OTP 标定数据

### 8.1 概述
OTP (One-Time Programmable) 存储在 sensor 内部, 出厂时写入:
- AWB 标定数据 (Golden sample 的 WB gain)
- LSC 标定数据 (补偿系数)
- AF 标定数据 (无穷远/微距位置)

### 8.2 驱动读取
```c
/* Sensor 驱动通过 ioctl 上报 OTP 数据 */
case RKMODULE_GET_MODULE_INFO:
    /* 返回 rkmodule_inf 结构, 含 AWB/LSC/AF OTP */
    break;
```

### 8.3 应用
- RkAiq 自动读取 OTP 数据
- 用 OTP AWB 校准个体差异
- OTP LSC 可替代/辅助 LSC 标定

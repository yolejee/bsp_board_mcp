# rk_mpp  Rockchip MPP 多媒体处理技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_mpp` 是一个面向 Rockchip 瑞芯微 SoC 平台的多媒体处理 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip 平台的 MPP（Media Process Platform）视频硬件编解码、RGA 2D 图像加速、GStreamer/Rockit/RKADK/FFmpeg 多媒体集成方案等问题时，AI 会自动加载本技能，提供 MPP API 编程指导、RGA IM2D 接口、GStreamer pipeline 构建等深度知识。

## 覆盖芯片

| 芯片 | 架构 | 编解码能力 |
|------|------|-----------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | 8K H.265 解码, 8K H.264 编码, RGA3 |
| **RK3568** | 4A55, Mali-G52 | 4K H.265/H.264 编解码, RGA2 |
| **RK3566** | 4A55, Mali-G52 | 4K H.265/H.264 编解码, RGA2 |
| **RK3399 / RK3399Pro** | 2A72 + 4A53, Mali-T860 | 4K H.265 解码, 1080p H.264 编码, RGA2 |
| **RK3288** | 4A17, Mali-T764 | 4K H.265 解码, 1080p H.264 编码, RGA2 |
| **PX30 / RK3326** | 4A35, Mali-G31 | 1080p H.264 编解码, RGA2 |

## 功能说明

### 功能 1：MPP C API 编解码开发

使用 MPP MPI 接口进行视频硬件编码和解码的应用开发。

**你可以这样提问：**
- "帮我写一个 MPP 硬件解码 H.265 视频文件的 C 代码"
- "MPP 编码器怎么设置 CBR 码率控制？"
- "decode_get_frame 返回 info_change 是什么意思？"
- "MPP 解码输出的 stride 和宽度不一样怎么处理？"
- "怎么用 MPP 做多路并行解码？"

**AI 会返回：**
- 完整的 MPP 编解码 C 代码骨架（init → put_packet → get_frame → deinit）
- MppEncCfg 编码参数设置（codec type、rc mode、GOP、QP、bitrate）
- info_change 机制详解和处理代码
- stride/hor_stride 对齐规则和数据拷贝方法

### 功能 2：RGA 2D 图像加速

使用 RGA IM2D API 进行图像缩放、旋转、格式转换、合成等 2D 加速操作。

**你可以这样提问：**
- "怎么用 RGA 把 NV12 转成 RGB888？"
- "RGA 缩放最大支持多少倍？"
- "imcopy/imresize/imcvtcolor 的用法和区别？"
- "RGA2 和 RGA3 性能差多少？"
- "RGA 和 GPU 做图像处理哪个效率高？"

**AI 会返回：**
- IM2D API 调用示例（wrapbuffer → imresize/imcvtcolor/imblend 等）
- RGA2 vs RGA3 能力和性能对比表
- 各芯片 RGA 硬件规格（最大分辨率、支持格式、缩放倍率）
- 常见错误码和排查方法

### 功能 3：GStreamer / FFmpeg 多媒体集成

使用 GStreamer、Rockit、RKADK、FFmpeg 构建多媒体应用 pipeline。

**你可以这样提问：**
- "RK3568 GStreamer 硬件解码播放4K视频的命令？"
- "gst-launch 怎么写 RTSP 拉流 + 硬解 + 显示的 pipeline？"
- "Rockit 和 MPP 直接调用相比有什么优势？"
- "FFmpeg 怎么启用 RK MPP 硬件编解码？"
- "RKADK 适合什么场景？怎么用？"

**AI 会返回：**
- GStreamer pipeline 命令（mppvideodec/mpph264enc + waylandsink/kmssink）
- 各种场景的 GStreamer 实战命令（本地播放、RTSP、录像、转码）
- Rockit / RKADK 框架介绍和适用场景
- FFmpeg rkmpp 编解码器启用方法

### 功能 4：编解码问题排查

花屏、绿屏、卡顿、掉帧、编码质量差等多媒体问题的诊断。

**你可以这样提问：**
- "MPP 解码输出画面花屏/绿屏"
- "4K 60fps 视频播放掉帧"
- "编码输出文件其他播放器播放不了"
- "多路解码时内存占用过高"

**AI 会返回：**
- 花屏/绿屏原因分析（stride 不对齐、info_change 未处理、AFBC 格式不匹配）
- 性能瓶颈定位（VPU 能力上限、DDR 带宽、CPU 拷贝瓶颈）
- 编码参数优化建议
- 零拷贝方案（DMA buffer 共享、MPP + RGA + DRM 零拷贝链路）

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **MPP / MPI / MppCtx / MppApi / mpi_dec_test / mpi_enc_test** 等 MPP 概念
- 提到 **RGA / librga / im2d / imcopy / imresize / imcvtcolor** 等 RGA 关键词
- 提到 **GStreamer / gst-launch / mppvideodec / mpph264enc** 等 GStreamer 元素
- 提到 **硬解 / 硬编 / 硬件编码 / 硬件解码 / H.264 / H.265 / HEVC / VP9** 等编解码
- 提到 **Rockit / RKADK / FFmpeg rkmpp** 等多媒体框架
- 描述多媒体症状：**解码花屏 / 绿屏 / 掉帧 / 卡顿 / 编码质量差**

## 文件结构

```
rk_mpp/
├── SKILL.md                                 # 主技能文件 (AI 自动加载, ~600 行)
├── README.md                                # 本说明文档 (供人阅读)
└── references/                              # 深入参考资料 (AI 按需加载)
    ├── mpp_codec_detail.md                  # MPP 详细编解码参考 (格式/Info Change/Demo/Stride)
    └── gstreamer_rga_recipes.md             # GStreamer 进阶/RGA 完整 API/Rockit/RKADK/FFmpeg
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 MPP/RGA 核心知识（API 流程、编解码能力表、GStreamer 基础 pipeline）
- **references/**：AI 根据问题按需加载。例如：
  - 用户需要 MPP 编解码细节 → 加载 `mpp_codec_detail.md`
  - 用户需要 GStreamer/RGA/Rockit/FFmpeg → 加载 `gstreamer_rga_recipes.md`

## 使用示例

### 示例 1：MPP 硬解码开发

**用户提问：**
> 帮我写一个 RK3588 上用 MPP 解码 H.265 视频文件的 C 程序

**AI 行为：**
1. 自动触发 `rk_mpp` 技能
2. 生成完整的 MPP 解码 C 代码（mpp_create → mpp_init → packet/frame 循环 → destroy）
3. 包含 info_change 处理和 stride 对齐处理
4. 加载 `references/mpp_codec_detail.md` 提供各参数详细说明

### 示例 2：GStreamer RTSP 播放

**用户提问：**
> RK3568 上用 GStreamer 拉 RTSP 流并且硬解显示到屏幕

**AI 行为：**
1. 给出完整的 gst-launch 命令（rtspsrc → rtph264depay → mppvideodec → waylandsink）
2. 说明低延迟参数调优（latency、sync=false）
3. 提供 kmssink vs waylandsink 的选择建议

### 示例 3：RGA 图像格式转换

**用户提问：**
> 怎么用 RGA 把 MPP 解码输出的 NV12 转成 RGB 然后送给 NPU 推理？

**AI 行为：**
1. 给出 IM2D API 调用代码（wrapbuffer_fd → imcvtcolor）
2. 说明 MPP 输出的 DMA buffer 可以零拷贝传给 RGA
3. 提供 NPU 输入格式要求和 RGA 输出格式匹配

## 知识来源

| 文档 | 说明 |
|------|------|
| Rockchip_Developer_Guide_MPP_CN | MPP 开发参考 (38 页) |
| Rockchip_User_Guide_Linux_Gstreamer_CN | GStreamer 用户指南 (16 页) |
| Rockchip_User_Guide_Linux_Rockit_CN | Rockit 用户指南 (18 页) |
| Rockchip_Developer_Guide_Linux_RKADK_CN | RKADK 开发指南 (129 页) |
| Rockchip_Developer_Guide_RGA_CN | RGA IM2D API 开发指南 (65 页) |

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

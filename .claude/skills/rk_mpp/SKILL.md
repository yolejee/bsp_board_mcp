---
name: rk_mpp
description: "Rockchip 瑞芯微平台多媒体处理技能，覆盖 MPP (Media Process Platform) 视频编解码框架、RGA 2D 硬件加速、GStreamer/FFmpeg 多媒体集成。适用于 RK3588/RK3568/RK3566/RK3399/RV1126 等全系列芯片的视频硬件编解码（VPU/RKVDEC/RKVENC）、RGA 图像处理、多媒体 pipeline 搭建与性能调优。触发关键词：MPP、MPI、mpp_create、MppBuffer、MppFrame、MppPacket、mpi_dec_test、mpi_enc_test、H.264、H.265、HEVC、VP9、MJPEG、硬解、硬编、码率控制、CBR、VBR、GOP、QP、RGA、librga、im2d、imresize、imcvtcolor、GStreamer、gst-launch、mppvideodec、mpph264enc、kmssink、AFBC、ffmpeg、解码花屏、解码卡顿、4K 60fps、多路解码。当用户在 Rockchip 平台上遇到视频编解码、图像处理、多媒体 pipeline 问题时触发。"
---

# Rockchip MPP 多媒体处理技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| MPP 解码基本流程 | §2.1 |
| MPP 编码基本流程 | §2.2 |
| 编码器参数配置 | §2.3 |
| 解码器内存模式 | §2.4 |
| RGA 图像处理 | §3 |
| GStreamer 命令与插件 | §4 |
| 多媒体方案选型 | §5 |
| 性能调优 | §6 |
| 常见故障排查 | §7 |

---

## 1. MPP 系统架构

### 1.1 架构层次

```
应用层 (App / OpenMax / FFmpeg / GStreamer)
   ↕ MPI 接口
MPP 层 (MPI + OSAL + HAL + Video Decoder/Encoder/Process)
   ↕ ioctl
内核驱动层 (vcodec_service / mpp_service + IOMMU + CLK + PM)
   ↕
硬件层 (VPU / RKVDEC / RKVENC / VEPU)
```

### 1.2 平台硬件编解码能力

| 平台 | 解码 | 编码 | 说明 |
|------|------|------|------|
| RK3588 | H.265/H.264 8K@60fps, VP9 8K@30fps | H.265/H.264 8K@30fps | RKVDEC×3 + RKVENC×3 |
| RK3568/RK3566 | H.265/H.264 4K@60fps, VP9 4K | H.264 1080p@60fps | RKVDEC + VEPU |
| RV1126/RV1109 | H.264/H.265 4K | H.264/H.265 3840×2160@30fps | RKVDEC + RKVENC |
| RK3399 | H.265/H.264/VP9 4K@60fps | H.264 1080p@30fps | RKVDEC + VEPU |
| RK3288 | H.265/H.264 4K@30fps | H.264 1080p@30fps | VPU + VEPU |

### 1.3 核心数据结构

```
MppCtx ─────→ MPP 实例上下文 (通过 mpp_create 获取)
MppApi ─────→ MPI 接口函数指针集 (decode/encode/control/reset)
MppBuffer ──→ 硬件 DMA 内存封装 (fd/ptr/size, 支持 ion/drm)
MppPacket ──→ 一维码流封装 (data/pos/length/pts/dts/eos)
MppFrame ───→ 二维图像封装 (width/height/hor_stride/ver_stride/fmt)
MppTask ────→ 高级组合任务 (key-value 扩展接口)
MppBufferGroup → 内存池管理 (internal/external 模式)
```

---

## 2. MPP 编解码 API

### 2.1 解码器流程

```c
/* 1. 创建&初始化 */
MppCtx ctx; MppApi *mpi;
mpp_create(&ctx, &mpi);
/* 开启内部分帧 (按长度输入时需要) */
RK_U32 need_split = 1;
mpi->control(ctx, MPP_DEC_SET_PARSER_SPLIT_MODE, &need_split);
mpp_init(ctx, MPP_CTX_DEC, MPP_VIDEO_CodingAVC);  /* H.264 */

/* 2. 输入码流 */
MppPacket pkt;
mpp_packet_init(&pkt, buf, size);
mpp_packet_set_pts(pkt, pts);
ret = mpi->decode_put_packet(ctx, pkt);  /* 非阻塞, 返回非0需重试 */
mpp_packet_deinit(&pkt);

/* 3. 获取输出 */
MppFrame frame = NULL;
ret = mpi->decode_get_frame(ctx, &frame);
if (frame) {
    if (mpp_frame_get_info_change(frame)) {
        /* Info Change: 宽高/格式变化, 需更新 BufferGroup */
        RK_U32 buf_size = mpp_frame_get_buf_size(frame);
        /* 模式一: 纯内部分配 - 直接通知 ready */
        mpi->control(ctx, MPP_DEC_SET_INFO_CHANGE_READY, NULL);
        /* 模式二: 半内部分配 - 创建 bufer group */
        /* mpp_buffer_group_get_external(&grp, MPP_BUFFER_TYPE_ION);
           mpp_buffer_group_limit_config(grp, buf_size, 24);
           mpi->control(ctx, MPP_DEC_SET_EXT_BUF_GROUP, grp);
           mpi->control(ctx, MPP_DEC_SET_INFO_CHANGE_READY, NULL); */
    } else if (mpp_frame_get_errinfo(frame)) {
        /* 解码错误帧, 可丢弃 */
    } else {
        /* 正常帧: 获取像素数据地址 */
        MppBuffer mbuf = mpp_frame_get_buffer(frame);
        void *ptr = mpp_buffer_get_ptr(mbuf);
        int fd = mpp_buffer_get_fd(mbuf);
        /* ... 使用数据: 显示/RGA处理/编码 ... */
    }
    mpp_frame_deinit(&frame);
}

/* 4. 发送 EOS */
mpp_packet_init(&pkt, NULL, 0);
mpp_packet_set_eos(pkt);
mpi->decode_put_packet(ctx, pkt);

/* 5. 销毁 */
mpp_destroy(ctx);
```

**关键注意事项:**
- `decode_put_packet` 非阻塞, 最多缓存 4 包, 满时返回错误需延时重试
- `decode_get_frame` 返回 0 不代表有帧, 需判断 frame 非空
- 分帧模式 (默认): 每包一帧, 效率高; 非分帧模式: 开启 `SPLIT_MODE`, 按任意长度输入
- 变宽高 `info_change`: 必须响应, 否则解码阻塞

### 2.2 编码器流程

```c
/* 1. 创建&初始化 */
mpp_create(&ctx, &mpi);
mpp_init(ctx, MPP_CTX_ENC, MPP_VIDEO_CodingAVC);  /* H.264 编码 */

/* 2. 配置编码参数 (通过 MppEncCfg) */
MppEncCfg cfg;
mpp_enc_cfg_init(&cfg);
mpi->control(ctx, MPP_ENC_GET_CFG, cfg);  /* 获取当前配置 */

/* 码率控制 */
mpp_enc_cfg_set_s32(cfg, "rc:mode",     MPP_ENC_RC_MODE_CBR);
mpp_enc_cfg_set_s32(cfg, "rc:bps_target", 4000000);   /* 4Mbps */
mpp_enc_cfg_set_s32(cfg, "rc:bps_max",    4500000);
mpp_enc_cfg_set_s32(cfg, "rc:bps_min",    3500000);
mpp_enc_cfg_set_s32(cfg, "rc:fps_in_num",  30);
mpp_enc_cfg_set_s32(cfg, "rc:fps_in_denorm", 1);
mpp_enc_cfg_set_s32(cfg, "rc:fps_out_num", 30);
mpp_enc_cfg_set_s32(cfg, "rc:fps_out_denorm", 1);
mpp_enc_cfg_set_s32(cfg, "rc:gop",        30);        /* 1秒一个I帧 */

/* 输入图像参数 */
mpp_enc_cfg_set_s32(cfg, "prep:width",      1920);
mpp_enc_cfg_set_s32(cfg, "prep:height",     1080);
mpp_enc_cfg_set_s32(cfg, "prep:hor_stride", 1920);
mpp_enc_cfg_set_s32(cfg, "prep:ver_stride", 1080);
mpp_enc_cfg_set_s32(cfg, "prep:format", MPP_FMT_YUV420SP); /* NV12 */

/* H.264 协议参数 */
mpp_enc_cfg_set_s32(cfg, "h264:profile", 100);  /* High */
mpp_enc_cfg_set_s32(cfg, "h264:level",   41);   /* 4.1 */
mpp_enc_cfg_set_s32(cfg, "h264:cabac_en", 1);
mpp_enc_cfg_set_s32(cfg, "h264:trans8x8", 1);

mpi->control(ctx, MPP_ENC_SET_CFG, cfg);

/* 3. 获取 SPS/PPS 头信息 */
MppPacket hdr_pkt;
mpp_packet_init(&hdr_pkt, hdr_buf, HDR_BUF_SIZE);
mpi->control(ctx, MPP_ENC_GET_HDR_SYNC, hdr_pkt);
/* hdr_pkt 包含 00 00 00 01 SPS + 00 00 00 01 PPS */

/* 4. 编码循环 */
MppFrame frame;
mpp_frame_init(&frame);
mpp_frame_set_width(frame, 1920);
mpp_frame_set_height(frame, 1080);
mpp_frame_set_hor_stride(frame, 1920);
mpp_frame_set_ver_stride(frame, 1080);
mpp_frame_set_fmt(frame, MPP_FMT_YUV420SP);
mpp_frame_set_buffer(frame, input_mbuf);  /* dmabuf/ion 输入, 零拷贝 */

mpi->encode_put_frame(ctx, frame);  /* 阻塞, 等待编码完成 */
MppPacket out_pkt = NULL;
mpi->encode_get_packet(ctx, &out_pkt);  /* 获取编码码流 */
if (out_pkt) {
    void *data = mpp_packet_get_pos(out_pkt);
    size_t len = mpp_packet_get_length(out_pkt);
    /* 保存/发送码流 */
    mpp_packet_deinit(&out_pkt);
}

/* 5. 请求 IDR 帧 (运行时) */
mpi->control(ctx, MPP_ENC_SET_IDR_FRAME, NULL);

/* 6. 清理 */
mpp_enc_cfg_deinit(cfg);
mpp_destroy(ctx);
```

### 2.3 编码器参数速查

| 参数字串 | 类型 | 说明 |
|----------|------|------|
| `rc:mode` | S32 | CBR/VBR/FIX_QP |
| `rc:bps_target` | S32 | CBR 目标码率 (bps) |
| `rc:bps_max/min` | S32 | VBR 最高/最低码率 |
| `rc:fps_in_num/denorm` | S32 | 输入帧率 (分数) |
| `rc:fps_out_num/denorm` | S32 | 输出帧率 (分数) |
| `rc:gop` | S32 | I帧间隔 (0=仅首帧I, 1=全I) |
| `prep:width/height` | S32 | 输入图像像素宽高 |
| `prep:hor_stride` | S32 | 水平步长 (字节) |
| `prep:ver_stride` | S32 | 垂直步长 (行) |
| `prep:format` | S32 | MppFrameFormat (NV12/NV16/...) |
| `prep:rotation` | S32 | 旋转 (0/90/180/270) |
| `h264:profile` | S32 | 66=Baseline, 77=Main, 100=High |
| `h264:level` | S32 | 41=4.1 (1080p@30fps), 51=5.1 (4K) |
| `h264:cabac_en` | S32 | 0=CAVLC, 1=CABAC |
| `h264:qp_init/max/min` | S32 | QP 控制 (一般不配置) |
| `h265:profile` | S32 | 固定 1 (Main) |
| `jpeg:quant` | S32 | 量化等级 0~10 (质量从差到好) |
| `split:mode` | U32 | 0=不切分, 1=BY_BYTE, 2=BY_CTU |
| `split:arg` | U32 | slice 大小/CTU 个数 |

### 2.4 解码器内存交互模式

| 模式 | 说明 | 使用场景 |
|------|------|---------|
| 纯内部分配 | 解码器内部分配, `info_change` 时直接 `SET_INFO_CHANGE_READY` | 快速 demo 评估 |
| 半内部分配 | 用户创建 `MppBufferGroup`, 通过 `SET_EXT_BUF_GROUP` 配置, 可 `limit_config` 限制内存 | mpi_dec_test 默认模式 |
| 纯外部分配 | 用户 commit 外部 dmabuf 到 external MppBufferGroup | 零拷贝显示 (Android/DRM) |

**纯外部分配注意事项:**
- H.264/H.265 需 20+ buffer 块, 其他编码格式需 10+
- 内存大小: `hor_stride × ver_stride × 3/2` (YUV420) + `hor_stride × ver_stride / 2` (额外信息)
- info_change 时需 reset BufferGroup 并 commit 新 buffer

### 2.5 常用 control 命令

| 命令 | 参数 | 说明 |
|------|------|------|
| `MPP_DEC_SET_PARSER_SPLIT_MODE` | RK_U32* | 使能内部分帧 (mpp_init 前) |
| `MPP_DEC_SET_PARSER_FAST_MODE` | RK_U32* | 快速帧解析, 提升并行度 |
| `MPP_DEC_SET_EXT_BUF_GROUP` | MppBufferGroup | 配置外部内存池 |
| `MPP_DEC_SET_INFO_CHANGE_READY` | NULL | 通知 info change 处理完成 |
| `MPP_DEC_SET_DISABLE_ERROR` | RK_U32* | 关闭错误处理, 输出全部帧 |
| `MPP_DEC_SET_IMMEDIATE_OUT` | RK_U32* | H.264 立即输出 (忽略帧序) |
| `MPP_ENC_SET_CFG` | MppEncCfg | 提交编码器配置 |
| `MPP_ENC_GET_CFG` | MppEncCfg | 获取当前编码器配置 |
| `MPP_ENC_GET_HDR_SYNC` | MppPacket | 获取 SPS/PPS 头数据 (线程安全) |
| `MPP_ENC_SET_IDR_FRAME` | NULL | 请求下一帧编码为 IDR |
| `MPP_ENC_SET_REF_CFG` | - | 高级参考帧模式 |

---

## 3. RGA 图像处理

### 3.1 RGA 版本与平台

| 版本 | 芯片 | 最大输入 | 最大输出 | 特性 |
|------|------|---------|---------|------|
| RGA2-Enhance | RK3399/RV1126/RK3568/RK3566 | 8192×8192 | 4096×4096 | 1/16~16x缩放, Alpha blend, ROP, IOMMU(32bit) |
| RGA3 | RK3588 | 8176×8176 | 8128×8128 | FBC 支持, IOMMU(40bit), 3px/cycle |
| RGA2+RGA3 | RK3588 | — | — | RK3588 同时有 RGA2-Enhance + RGA3 |

### 3.2 IM2D API 核心流程

```c
#include "im2d.h"
#include "rga.h"

/* 1. 导入 buffer */
rga_buffer_handle_t src_handle = importbuffer_fd(src_fd, src_w, src_h, RK_FORMAT_YCbCr_420_SP);
rga_buffer_handle_t dst_handle = importbuffer_fd(dst_fd, dst_w, dst_h, RK_FORMAT_YCbCr_420_SP);

/* 2. 封装 rga_buffer_t */
rga_buffer_t src = wrapbuffer_handle(src_handle, src_w, src_h, RK_FORMAT_YCbCr_420_SP);
rga_buffer_t dst = wrapbuffer_handle(dst_handle, dst_w, dst_h, RK_FORMAT_YCbCr_420_SP);

/* 3. 执行操作 */
imcopy(src, dst);                                    /* 拷贝 */
imresize(src, dst);                                  /* 缩放 (自动计算) */
imcvtcolor(src, dst, src.format, dst.format);        /* 格式转换 */
imrotate(src, dst, IM_HAL_TRANSFORM_ROT_90);         /* 旋转 90° */
imcrop(src, dst, (im_rect){x, y, w, h});             /* 裁剪 */
imblend(src, dst);                                   /* Alpha 混合 */
imfill(dst, (im_rect){x, y, w, h}, 0xFF0000FF);     /* 颜色填充 */

/* 4. 释放 handle */
releasebuffer_handle(src_handle);
releasebuffer_handle(dst_handle);
```

**Buffer 类型性能排序:** physical address > fd > virtual address (推荐 fd)

### 3.3 RGA 任务模式

```c
/* 多步操作绑定为单个任务提交 */
im_job_handle_t job = imbeginJob();
imcopyTask(job, src, dst);
imresizeTask(job, src2, dst2);
imendJob(job);  /* 统一提交执行 */
```

---

## 4. GStreamer 集成

### 4.1 Rockchip MPP 插件

| 插件 | 类型 | 说明 |
|------|------|------|
| `mppvideodec` | 解码 | H.264/H.265/VP8/VP9/MPEG, 支持 AFBC/Fast Mode |
| `mppjpegdec` | 解码 | JPEG |
| `mpph264enc` | 编码 | H.264 |
| `mpph265enc` | 编码 | H.265 |
| `mppvp8enc` | 编码 | VP8 |
| `mppjpegenc` | 编码 | JPEG |

**mppvideodec 属性:**
- `rotation`: 0/90/180/270
- `width/height`: 非0时进行缩放
- `crop-rectangle`: `<x,y,w,h>` (缩放后坐标)
- `arm-afbc`: 开启 AFBC 压缩, 降低 DDR 带宽
- `format`: 输出格式 (默认 auto)
- `fast-mode`: 部分流程并行 (默认开启)
- `ignore-error`: 忽略解码错误 (默认开启)

### 4.2 常用 GStreamer 命令

```bash
# === 播放 ===
gst-play-1.0 --flags=3 --videosink=waylandsink test.mp4
gst-play-1.0 --flags=3 --videosink="fpsdisplaysink video-sink=waylandsink \
  signal-fps-measurements=true text-overlay=false sync=false" test.mp4

# === 解码播放 ===
gst-launch-1.0 filesrc location=test.mp4 ! parsebin ! mppvideodec ! waylandsink

# === 多路播放 ===
gst-launch-1.0 filesrc location=test.mp4 ! parsebin ! mppvideodec ! \
  waylandsink render-rectangle='<0,0,400,400>' &
gst-launch-1.0 filesrc location=test.mp4 ! parsebin ! mppvideodec ! \
  waylandsink render-rectangle='<0,500,400,400>' &

# === 摄像头编码保存 + 预览 ===
gst-launch-1.0 v4l2src ! 'video/x-raw,format=NV12' ! tee name=tv \
  ! queue ! mpph264enc ! h264parse ! filesink location=out.h264 \
  tv. ! queue ! autovideosink

# === RTSP 播放 ===
gst-launch-1.0 rtspsrc location=rtsp://192.168.1.105:8554/ ! rtph264depay ! \
  h264parse ! mppvideodec ! waylandsink

# === 码流拆分 ===
gst-launch-1.0 filesrc location=test.mp4 ! qtdemux name=qt \
  qt.audio_0 ! queue ! filesink location=audio.bin \
  qt.video_0 ! queue ! filesink location=video.bin

# === 编码参数指定 ===
gst-launch-1.0 v4l2src ! 'video/x-raw,format=NV12,width=1920,height=1080' ! \
  mpph264enc bps=4000000 gop=30 rc-mode=cbr profile=high ! \
  h264parse ! mp4mux ! filesink location=out.mp4
```

### 4.3 显示插件选择

| 插件 | 接口 | 零拷贝 | 独占图层 | AFBC |
|------|------|--------|---------|------|
| `waylandsink` | Wayland | ✓ | ✗ | ✓ |
| `xvimagesink` | X11 | ✗ | ✗ | ✓ |
| `kmssink` | KMS/DRM | ✓ | ✓ | Cluster层支持 |
| `rkximagesink` | DRM | ✓ | ✓ | ✓ |

**图层指定:**
```bash
# 查看可用图层
cat /sys/kernel/debug/dri/0/state | grep "plane\["
# plane[57]: Smart1-win0  plane[101]: Cluster0-win0 ...
gst-play-1.0 --flags=3 test.mp4 --videosink="kmssink plane-id=101"
```

### 4.4 环境变量

```bash
export GST_MPP_VIDEODEC_DEFAULT_ARM_AFBC=1     # 全局开启 AFBC
export GST_MPP_VIDEODEC_DEFAULT_FORMAT=NV12     # 强制输出 NV12
export GST_MPP_DEC_DEFAULT_FAST_MODE=0          # 关闭 Fast Mode
export GST_MPP_DEC_DEFAULT_IGNORE_ERROR=0       # 不忽略解码错误
export GST_VIDEO_CONVERT_USE_RGA=1              # videoconvert 使用 RGA
export GST_VIDEO_FLIP_USE_RGA=1                 # videoflip 使用 RGA
export GST_V4L2_PREFERRED_FOURCC=NV12:YU12      # v4l2 输出格式优先级
```

### 4.5 GStreamer 日志

```bash
export GST_DEBUG=2                    # 全局 WARNING
export GST_DEBUG=2,fpsdisplaysink:7   # 特定模块 TRACE
export GST_DEBUG=*mpp*:4              # MPP 插件 INFO (查看 AFBC 状态等)
# 日志等级: ERROR(1) WARNING(2) FIXME(3) INFO(4) DEBUG(5) LOG(6) TRACE(7)
```

---

## 5. 多媒体方案选型

### 5.1 方案对比

| 方案 | 层次 | 适用场景 | 特点 |
|------|------|---------|------|
| **MPP 直接调用** | 底层 C API | 极致性能/自定义 pipeline | 灵活, 复杂度高 |
| **GStreamer** | 中间件 | Linux 桌面/多媒体应用 | 插件化, 快速原型 |
| **Rockit** | 中间件 | IPC/NVR 多模块绑定 | 类海思 API 风格 |
| **RKADK** | 应用层 | 行车记录仪/运动相机 | 录像/拍照/预览一体化 |
| **FFmpeg + RKMPP** | 中间件 | 服务端转码 | FFmpeg 生态兼容 |

### 5.2 Rockit 主要模块

| 模块 | 功能 | 说明 |
|------|------|------|
| VENC | 视频编码 | H.264/H.265 编码输出 |
| VDEC | 视频解码 | 解码视频流 |
| VPSS | 视频处理 | 缩放/裁剪/旋转 |
| VI | 视频输入 | 对接 Camera |
| VO | 视频输出 | 送显 |
| AI/AO | 音频输入/输出 | 采集/播放 |
| AENC/ADEC | 音频编解码 | 编码/解码音频 |
| RGN | 区域管理 | OSD 叠加 |
| VGS | 视频图形子系统 | 2D 操作 |

---

## 6. 性能调优

### 6.1 AFBC (ARM Frame Buffer Compression)

- **支持格式:** H.264/H.265/VP9 解码输出, NV12/NV12_10bit/NV16
- **作用:** 压缩帧缓存, 降低 DDR 带宽占用
- **开启方式:**
  ```bash
  # GStreamer
  export GST_MPP_VIDEODEC_DEFAULT_ARM_AFBC=1
  # 或
  gst-launch-1.0 ... mppvideodec arm-afbc=true ! waylandsink
  ```
- **注意:** Esmart 图层不支持 AFBC, 需使用 Cluster 图层; 竖屏横播时 AFBC 性能可能不如非 AFBC
- **不支持 AFBC 的平台:** RK3399

### 6.2 定频提升性能

```bash
# 锁定 CPU/GPU/DDR 频率到最高
echo performance | tee $(find /sys/ -name *governor)
```

### 6.3 Fast Mode

RK3588 等平台开启 Fast Mode 可使部分解码流程并行, 提升效率 (GStreamer 默认开启)。

### 6.4 多路解码带宽优化

- 开启 AFBC 降低 DDR 带宽
- 关闭 sync: `waylandsink sync=false`
- 关闭字幕: `--flags=3` (bit0=video, bit1=audio, 不含 bit2=subtitle)
- 如 4K60 卡顿, 确认已开启性能模式

---

## 7. 常见故障排查

### 7.1 解码花屏/绿屏

1. 确认输入码流完整性 (分帧 vs 非分帧模式是否匹配)
2. 检查 `hor_stride / ver_stride` 是否正确 (16 对齐)
3. 确认 `info_change` 已正确处理
4. 检查 `MppFrameFormat` 与显示端格式匹配

### 7.2 编码图像拉伸/色偏

1. 检查 `prep:hor_stride` / `prep:ver_stride` 是否与实际内存排布一致
2. ver_stride 不等于 height 时, 亮度与色度间可能有空行 (如 1080→1088)
3. 确认 `prep:format` 与实际输入格式一致

### 7.3 解码无输出

1. 检查 codec type (`-t` 参数/`MppCodingType`)
2. 确认 `info_change` 时调用了 `SET_INFO_CHANGE_READY`
3. 检查 `MPP_DEC_SET_PARSER_SPLIT_MODE` 设置
4. EOS 后需 `reset` 才能继续解码

### 7.4 4K 播放卡顿

1. 开启性能模式: `echo performance | tee $(find /sys/ -name *governor)`
2. 开启 AFBC: `export GST_MPP_VIDEODEC_DEFAULT_ARM_AFBC=1`
3. 关闭同步: `waylandsink sync=false`
4. 关闭字幕 `--flags=3`
5. 确认硬解在工作: `echo 0x100 > /sys/module/rk_vcodec/parameters/mpp_dev_debug`

### 7.5 MPP 运行异常诊断

```bash
# 1. 检查 MPP 版本
mpp_info_test

# 2. 检查内核设备
ls /dev/mpp_service   # 新接口
ls /dev/vpu_service   # 旧接口

# 3. 检查内存分配器
# MPP 日志会打印: "found ion allocator" 或 "found drm allocator"

# 4. 检查 IOMMU
dmesg | grep iommu
cat /proc/iomem | grep vdpu

# 5. 编解码调试日志
echo 0x100 > /sys/module/rk_vcodec/parameters/mpp_dev_debug
echo 0x400 > /sys/module/rk_vcodec/parameters/mpp_dev_debug  # dump 数据

# 6. MPP 工具
mpp_buffer_test      # 测试内存分配器
mpp_runtime_test     # 测试运行时环境
mpp_platform_test    # 测试平台信息
```

### 7.6 RGA 常见问题

- **格式不支持:** 用 `querystring(RGA_INPUT_FORMAT)` 查询
- **分辨率超限:** RGA2 最大输出 4096×4096, RGA3 最大输出 8128×8128
- **对齐要求:** YUV 格式宽高需偶数对齐, RGA3 最小 68×2
- **性能不够:** 优先使用 fd 而非虚拟地址; 用 RGA3 (RK3588) 处理大分辨率

### 7.7 RGA 性能优化要点

```
参考性能: RGA2-Enhance (RK3566) 处理 1920×1080 ≈ 3.3ms (约 630 MPixel/s)

优化建议:
1. 重用缓冲区 — 避免频繁 importbuffer/releasebuffer
2. 使用 fd 导入 — physical > fd > virtual (性能排序)
3. 避免不必要的格式转换 — 保持输入输出格式一致
4. 批量任务 — imbeginJob() 合并多步操作一次提交
5. 内存对齐 — posix_memalign 分配对齐内存
```

---

## 8. 深入参考

详细 API 参考和代码示例请查阅:
- `references/mpp_codec_detail.md` — MPP 详细编解码代码、demo 说明、info_change 完整处理
- `references/gstreamer_rga_recipes.md` — GStreamer 进阶用法、RGA IM2D 完整 API、Rockit/RKADK 使用

---

## 9. 编译与源码

### 9.1 MPP 源码

```bash
git clone https://github.com/rockchip-linux/mpp.git  # release 分支
cd mpp/build/linux/arm/
# 配置 arm.linux.cross.cmake 中的工具链
./make-Makefiles.bash
make -j16
```

### 9.3 FFmpeg + RKMPP 硬件编解码

FFmpeg 通过 `rkmpp` wrapper 调用 MPP 进行硬件编解码:

```bash
# 硬件解码 H.265 → NV12
ffmpeg -c:v hevc_rkmpp -i input.mp4 -f rawvideo -pix_fmt nv12 output.yuv

# 硬件编码 H.264 (需 rkmpp encoder 支持)
ffmpeg -i input.mp4 -c:v h264_rkmpp -b:v 4M -r 30 output.mp4

# 硬解 + 缩放 + 硬编 pipeline
ffmpeg -c:v hevc_rkmpp -i 4k_input.mp4 -vf scale_rkrga=1920:1080 \
       -c:v h264_rkmpp -b:v 4M output_1080p.mp4

# 查看可用硬件编解码器
ffmpeg -codecs 2>/dev/null | grep rkmpp
# 典型输出: hevc_rkmpp / h264_rkmpp / vp9_rkmpp (解码)
#           h264_rkmpp_encoder / hevc_rkmpp_encoder (编码, 需 SDK 支持)
```

> FFmpeg 需编译时启用 `--enable-rkmpp --enable-libdrm`。Buildroot: `BR2_PACKAGE_FFMPEG_RKMPP=y`

```
<SDK>/external/gstreamer-rockchip/gst/rockchipmpp/  # MPP 编解码插件
<SDK>/external/mpp/                                   # MPP 库
<SDK>/external/linux-rga/                              # RGA 库
```

Buildroot 配置:
```ini
BR2_PACKAGE_MPP=y
BR2_PACKAGE_MPP_ALLOCATOR_DRM=y
BR2_PACKAGE_GSTREAMER1_ROCKCHIP=y
BR2_PACKAGE_LINUX_RGA=y
```

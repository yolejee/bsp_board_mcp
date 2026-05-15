# GStreamer 进阶用法、RGA 完整 API 与应用集成

## 1. GStreamer 进阶

### 1.1 完整 pipeline 构建示例

```bash
# === 视频转码 (H.264 → H.265) ===
gst-launch-1.0 filesrc location=input.mp4 ! qtdemux ! h264parse ! \
  mppvideodec ! mpph265enc bps=4000000 ! h265parse ! \
  mp4mux ! filesink location=output_h265.mp4

# === 摄像头 RTSP 推流 ===
gst-launch-1.0 v4l2src ! 'video/x-raw,format=NV12,width=1920,height=1080' ! \
  mpph264enc bps=4000000 ! h264parse ! \
  rtph264pay ! udpsink host=192.168.1.100 port=5000

# === 多路摄像头拼接预览 ===
gst-launch-1.0 compositor name=comp \
  sink_0::xpos=0 sink_0::ypos=0 \
  sink_1::xpos=640 sink_1::ypos=0 \
  ! waylandsink \
  v4l2src device=/dev/video0 ! 'video/x-raw,width=640,height=480' ! comp.sink_0 \
  v4l2src device=/dev/video4 ! 'video/x-raw,width=640,height=480' ! comp.sink_1

# === JPEG 抓拍 ===
gst-launch-1.0 v4l2src num-buffers=1 ! 'video/x-raw,format=NV12' ! \
  mppjpegenc ! filesink location=snapshot.jpg

# === 视频截取片段 ===
gst-launch-1.0 filesrc location=input.mp4 ! qtdemux name=qt \
  qt.video_0 ! queue ! h264parse ! mp4mux ! filesink location=video_only.mp4

# === 音视频同步播放 ===
gst-play-1.0 --flags=3 \
  --videosink="waylandsink sync=true" \
  --audiosink="alsasink device=hw:0,0" \
  test.mp4
```

### 1.2 GStreamer 性能调试

```bash
# 测量帧率
GST_DEBUG=fpsdisplaysink:7 gst-launch-1.0 filesrc location=test.mp4 ! \
  parsebin ! mppvideodec ! fpsdisplaysink video-sink=fakesink \
  signal-fps-measurements=true text-overlay=false sync=false

# Pipeline 图导出 (需安装 graphviz)
export GST_DEBUG_DUMP_DOT_DIR=/tmp/dots/
gst-play-1.0 test.mp4
dot -Tpng /tmp/dots/*.dot -o pipeline.png

# 延迟分析
GST_DEBUG=GST_SCHEDULING:5 gst-launch-1.0 ...

# 查看插件详细信息
gst-inspect-1.0 mppvideodec
gst-inspect-1.0 mpph264enc
```

### 1.3 mpph264enc/mpph265enc 完整属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `bps` | int | 目标码率 (bps) |
| `bps-max` | int | 最高码率 |
| `bps-min` | int | 最低码率 |
| `rc-mode` | enum | vbr/cbr/fixqp |
| `gop` | int | I帧间隔 (-1=按帧率) |
| `profile` | enum | baseline/main/high |
| `level` | int | level_idc |
| `width` | int | 编码宽度 (0=跟随输入) |
| `height` | int | 编码高度 |
| `rotation` | enum | 0/90/180/270 |

### 1.4 AFBC Dump 解码数据

```bash
# 方法1: MPP 内部 dump (不支持 AFBC 开启时)
export mpp_debug=0x400
# 解码数据保存到 /data 目录

# 方法2: GStreamer filesink dump (支持 AFBC)
gst-launch-1.0 uridecodebin uri=file:///test.mp4 ! filesink location=dump.yuv

# 查看每帧大小
GST_DEBUG=filesink:6 gst-launch-1.0 uridecodebin uri=file:///test.mp4 ! \
  filesink location=dump.yuv

# 分帧 (每帧 1390080 bytes)
split -b 1390080 -a 5 -d dump.yuv dump_frame

# AFBC 解压缩
./afbcDec dump_frame00000 1920 1080 1 0
# 参数: filename w h format(0=RGBA,1=NV12,2=RGB888) afbcmode(0=afbc,1=afbc+YTR)
```

### 1.5 Buildroot 配置宏

```ini
# 核心
BR2_PACKAGE_MPP=y
BR2_PACKAGE_MPP_ALLOCATOR_DRM=y
BR2_PACKAGE_GSTREAMER1_ROCKCHIP=y
BR2_PACKAGE_LINUX_RGA=y

# GStreamer 基础
BR2_PACKAGE_GSTREAMER1=y
BR2_PACKAGE_GST1_PLUGINS_BASE=y
BR2_PACKAGE_GST1_PLUGINS_BASE_PLUGIN_ALSA=y
BR2_PACKAGE_GST1_PLUGINS_BASE_PLUGIN_VIDEOCONVERT=y

# 常用插件
BR2_PACKAGE_GST1_PLUGINS_GOOD=y
BR2_PACKAGE_GST1_PLUGINS_GOOD_PLUGIN_MATROSKA=y
BR2_PACKAGE_GST1_PLUGINS_GOOD_PLUGIN_AUDIOPARSERS=y
BR2_PACKAGE_GST1_PLUGINS_BAD=y
BR2_PACKAGE_GST1_PLUGINS_BAD_PLUGIN_VIDEOPARSERS=y
BR2_PACKAGE_GST1_PLUGINS_BAD_PLUGIN_KMS=y
BR2_PACKAGE_GST1_PLUGINS_UGLY=y
BR2_PACKAGE_GST1_PLUGINS_UGLY_PLUGIN_MPEG2DEC=y
```

## 2. RGA IM2D 完整 API 参考

### 2.1 Buffer 管理

```c
/* 导入不同类型的 buffer */
rga_buffer_handle_t h1 = importbuffer_fd(fd, width, height, format);
rga_buffer_handle_t h2 = importbuffer_virtualaddr(va, width, height, format);
rga_buffer_handle_t h3 = importbuffer_physicaladdr(pa, width, height, format);
/* Android 专用 */
rga_buffer_handle_t h4 = importbuffer_GraphicBuffer_handle(hnd);
rga_buffer_handle_t h5 = importbuffer_AHardwareBuffer(ahb);

/* 封装为 rga_buffer_t */
rga_buffer_t src = wrapbuffer_handle(handle, w, h, fmt);
/* 可选: 指定 wstride/hstride */
rga_buffer_t src2 = wrapbuffer_handle(handle, w, h, fmt, wstride, hstride);

/* 释放 */
releasebuffer_handle(handle);
```

### 2.2 图像操作 API

```c
/* 拷贝 */
IM_STATUS imcopy(src, dst, sync=1, release_fence_fd=NULL);

/* 缩放 */
IM_STATUS imresize(src, dst, fx=0, fy=0, interp=INTER_LINEAR, sync=1);
/* fx/fy 非0时使用缩放系数; 否则根据 src/dst 大小自动计算 */

/* 金字塔 (2x 或 1/2 缩放) */
IM_STATUS impyramid(src, dst, IM_UP_SCALE / IM_DOWN_SCALE);

/* 裁剪 */
IM_STATUS imcrop(src, dst, (im_rect){x, y, w, h}, sync=1);

/* 平移 */
IM_STATUS imtranslate(src, dst, x, y, sync=1);

/* 格式转换 */
IM_STATUS imcvtcolor(src, dst, src.format, dst.format, IM_COLOR_SPACE_DEFAULT, sync=1);
/* 支持: YUV↔RGB, BT.601/709/2020(RGA3), Dither */

/* 旋转 */
IM_STATUS imrotate(src, dst, IM_HAL_TRANSFORM_ROT_90/180/270, sync=1);

/* 翻转 */
IM_STATUS imflip(src, dst, IM_HAL_TRANSFORM_FLIP_H/V/HV, sync=1);

/* Alpha 混合 */
IM_STATUS imblend(srcA, dst, mode=IM_ALPHA_BLEND_SRC_OVER, sync=1);
IM_STATUS imcomposite(srcA, srcB, dst, mode, sync=1);  /* 三通道 */

/* 颜色键 */
IM_STATUS imcolorkey(src, dst, (im_colorkey_range){max, min}, mode, sync=1);

/* 颜色填充 */
IM_STATUS imfill(dst, (im_rect){x, y, w, h}, color_rgba, sync=1);
IM_STATUS imfillArray(dst, rect_array, count, color_rgba, sync=1);

/* OSD 叠加 (仅 RV1106/RV1103) */
IM_STATUS imosd(osd, dst, osd_rect, osd_config, sync=1);

/* NN 量化预处理 */
IM_STATUS imquantize(src, dst, nn_info, sync=1);
/* nn_info: 缩放系数和偏移, 用于 NPU 输入预处理 */

/* 光栅操作 ROP */
IM_STATUS imrop(src, dst, rop_code, sync=1);

/* 矩形边框绘制 */
IM_STATUS imrectangle(dst, rect, color, thickness, sync=1);

/* 马赛克 (仅部分平台) */
IM_STATUS immosaic(dst, rect, mosaic_mode, sync=1);

/* 复合操作 */
IM_STATUS improcess(src, dst, pat, src_rect, dst_rect, pat_rect, usage, ...);

/* 参数校验 */
IM_STATUS imcheck(src, dst, src_rect, dst_rect, usage);

/* 查询硬件信息 */
const char* querystring(RGA_ALL);  /* 返回全部 RGA 信息 */
```

### 2.3 RGA 格式常量

| 常量 | 说明 |
|------|------|
| `RK_FORMAT_YCbCr_420_SP` | NV12 |
| `RK_FORMAT_YCbCr_420_P` | I420/YU12 |
| `RK_FORMAT_YCbCr_422_SP` | NV16 |
| `RK_FORMAT_YUYV_422` | YUYV |
| `RK_FORMAT_RGBA_8888` | RGBA |
| `RK_FORMAT_BGRA_8888` | BGRA |
| `RK_FORMAT_RGB_888` | RGB24 |
| `RK_FORMAT_BGR_888` | BGR24 |
| `RK_FORMAT_RGB_565` | RGB16 |
| `RK_FORMAT_YCbCr_420_SP_10B` | NV12 10bit |

### 2.4 典型使用场景

```c
/* 场景1: Camera NV12 → 缩放到 NPU 输入尺寸 + 格式转换 */
rga_buffer_handle_t cam_h = importbuffer_fd(cam_fd, 1920, 1080, RK_FORMAT_YCbCr_420_SP);
rga_buffer_handle_t npu_h = importbuffer_fd(npu_fd, 640, 640, RK_FORMAT_RGB_888);
rga_buffer_t cam = wrapbuffer_handle(cam_h, 1920, 1080, RK_FORMAT_YCbCr_420_SP);
rga_buffer_t npu = wrapbuffer_handle(npu_h, 640, 640, RK_FORMAT_RGB_888);
/* 一步完成缩放+格式转换 */
imresize(cam, npu);  /* 自动进行 NV12→RGB + 1920x1080→640x640 */
releasebuffer_handle(cam_h);
releasebuffer_handle(npu_h);

/* 场景2: 解码帧 + OSD 时间戳叠加 + 编码 */
im_job_handle_t job = imbeginJob();
imcopyTask(job, decoded_buf, enc_input_buf);
imfillTask(job, enc_input_buf, osd_rect, bg_color);  /* OSD 背景 */
/* imblendTask for OSD text overlay if needed */
imendJob(job);
/* 然后将 enc_input_buf 送入 MPP 编码 */

/* 场景3: 视频帧 90° 旋转 (竖屏适配) */
imrotate(src, dst, IM_HAL_TRANSFORM_ROT_90);
```

## 3. Rockit 使用指南

### 3.1 编译

```bash
# Buildroot
BR2_PACKAGE_ROCKIT=y
# 源码路径: <SDK>/external/rockit/
```

### 3.2 常用测试命令

```bash
# VENC 编码测试
rockit_test venc -w 1920 -h 1080 -c h264 -b 4000000 -i input.yuv -o output.h264

# VDEC 解码测试
rockit_test vdec -c h264 -i input.h264 -o output.yuv

# VPSS 视频处理
rockit_test vpss -w 1920 -h 1080 -W 640 -H 480 -i input.yuv -o output.yuv

# VI 摄像头采集
rockit_test vi -w 1920 -h 1080 -o output.yuv

# VO 视频输出
rockit_test vo -w 1920 -h 1080 -i input.yuv
```

### 3.3 模块绑定 (IPC 典型方案)

```
VI ──→ VPSS ──→ VENC ──→ 推流/存储
           ├──→ VO ──→ 本地预览
           └──→ RGN ──→ OSD 叠加
AI ──→ AENC ──→ 音频编码
ADEC ──→ AO ──→ 音频播放
```

## 4. RKADK 应用 SDK

### 4.1 核心功能

| 功能 | API |
|------|-----|
| 录像 | `RKADK_RECORD_Create/Start/Stop/Destroy` |
| 拍照 | `RKADK_PHOTO_Init/TakePhoto/DeInit` |
| 预览 | `RKADK_STREAM_VideoInit/VencStart/VencStop` |
| 播放 | `RKADK_PLAYER_Create/Play/Stop/Destroy` |

### 4.2 录像示例

```c
RKADK_RECORD_ATTR_S attr;
memset(&attr, 0, sizeof(attr));
attr.enRecType = RKADK_REC_TYPE_NORMAL;
attr.s32CamId = 0;

RKADK_MW_PTR pRecorder = NULL;
RKADK_RECORD_Create(&attr, &pRecorder);
RKADK_RECORD_Start(pRecorder);
/* ... 录制中 ... */
RKADK_RECORD_Stop(pRecorder);
RKADK_RECORD_Destroy(pRecorder);
```

## 5. FFmpeg + RKMPP 集成

```bash
# FFmpeg 编译时启用 rkmpp
./configure --enable-rkmpp --enable-libdrm --enable-version3

# 硬件解码
ffmpeg -c:v h264_rkmpp -i input.mp4 -f rawvideo output.yuv

# 硬件编码
ffmpeg -i input.yuv -c:v h264_rkmpp -b:v 4M output.mp4

# 转码 (硬解+硬编)
ffmpeg -c:v h264_rkmpp -i input.mp4 -c:v h264_rkmpp -b:v 4M output.mp4

# 查看可用硬件编解码器
ffmpeg -codecs | grep rkmpp
```

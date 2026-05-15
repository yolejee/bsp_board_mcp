# MPP 详细编解码参考

## 1. MppCodingType 编解码类型

| 类型 | 值 | 说明 |
|------|-----|------|
| `MPP_VIDEO_CodingMPEG2` | 2 | MPEG-2 |
| `MPP_VIDEO_CodingH263` | 3 | H.263 |
| `MPP_VIDEO_CodingMPEG4` | 4 | MPEG-4 |
| `MPP_VIDEO_CodingAVC` | 7 | H.264/AVC |
| `MPP_VIDEO_CodingMJPEG` | 8 | MJPEG |
| `MPP_VIDEO_CodingVP8` | 9 | VP8 |
| `MPP_VIDEO_CodingVP9` | 10 | VP9 |
| `MPP_VIDEO_CodingHEVC` | 16777220 | H.265/HEVC (0x01000004) |

注: HEVC 和 AVS 的值与其他格式差距很大，需注意。

## 2. MppFrameFormat 图像格式

| 格式 | 说明 |
|------|------|
| `MPP_FMT_YUV420SP` | NV12 (YUV420 Semi-Planar) |
| `MPP_FMT_YUV420SP_10BIT` | NV12 10bit |
| `MPP_FMT_YUV420P` | I420/YU12 (YUV420 Planar) |
| `MPP_FMT_YUV422SP` | NV16 (YUV422 Semi-Planar) |
| `MPP_FMT_YUV422_YUYV` | YUYV |
| `MPP_FMT_YUV422_UYVY` | UYVY |
| `MPP_FMT_RGB888` | RGB 24bit |
| `MPP_FMT_BGR888` | BGR 24bit |
| `MPP_FMT_ARGB8888` | ARGB 32bit |
| `MPP_FMT_ABGR8888` | ABGR 32bit |

## 3. 解码器 Info Change 完整处理

### 3.1 模式一: 纯内部分配

```c
void decode_loop_mode1(MppCtx ctx, MppApi *mpi)
{
    /* 读取码流并 put_packet ... */
    MppFrame frame = NULL;
    mpi->decode_get_frame(ctx, &frame);
    if (!frame) return;

    if (mpp_frame_get_info_change(frame)) {
        RK_U32 w = mpp_frame_get_width(frame);
        RK_U32 h = mpp_frame_get_height(frame);
        RK_U32 hs = mpp_frame_get_hor_stride(frame);
        RK_U32 vs = mpp_frame_get_ver_stride(frame);
        RK_U32 buf_size = mpp_frame_get_buf_size(frame);
        MppFrameFormat fmt = mpp_frame_get_fmt(frame);
        printf("info change: %dx%d stride %dx%d fmt %d buf_size %d\n",
               w, h, hs, vs, fmt, buf_size);
        /* 纯内部分配: 只需通知 ready */
        mpi->control(ctx, MPP_DEC_SET_INFO_CHANGE_READY, NULL);
    } else {
        RK_U32 err = mpp_frame_get_errinfo(frame);
        RK_U32 discard = mpp_frame_get_discard(frame);
        if (err || discard) {
            /* 错误帧或丢弃帧 */
        } else {
            /* 正常帧处理 */
            MppBuffer buf = mpp_frame_get_buffer(frame);
            /* ... */
        }
    }
    mpp_frame_deinit(&frame);
}
```

### 3.2 模式二: 半内部分配

```c
MppBufferGroup frame_group = NULL;

void handle_info_change_mode2(MppCtx ctx, MppApi *mpi, MppFrame frame)
{
    RK_U32 buf_size = mpp_frame_get_buf_size(frame);

    if (frame_group) {
        /* 已有 group, 重置 */
        mpp_buffer_group_clear(frame_group);
    } else {
        /* 首次创建 */
        mpp_buffer_group_get_internal(&frame_group, MPP_BUFFER_TYPE_ION);
    }

    /* 限制内存使用: buf_size × 24 (H.264/H.265 参考帧数) */
    mpp_buffer_group_limit_config(frame_group, buf_size, 24);

    /* 配置给解码器 */
    mpi->control(ctx, MPP_DEC_SET_EXT_BUF_GROUP, frame_group);
    mpi->control(ctx, MPP_DEC_SET_INFO_CHANGE_READY, NULL);
}
```

### 3.3 模式三: 纯外部分配

```c
void handle_info_change_mode3(MppCtx ctx, MppApi *mpi, MppFrame frame,
                              int *fds, int fd_count)
{
    RK_U32 buf_size = mpp_frame_get_buf_size(frame);

    if (frame_group) {
        mpp_buffer_group_clear(frame_group);
    } else {
        /* 创建 external 类型的 group */
        mpp_buffer_group_get_external(&frame_group, MPP_BUFFER_TYPE_DRM);
    }

    /* 导入外部 dmabuf */
    for (int i = 0; i < fd_count; i++) {
        MppBufferInfo info;
        memset(&info, 0, sizeof(info));
        info.type = MPP_BUFFER_TYPE_DRM;
        info.size = buf_size;
        info.fd   = fds[i];
        mpp_buffer_commit(frame_group, &info);
    }

    mpi->control(ctx, MPP_DEC_SET_EXT_BUF_GROUP, frame_group);
    mpi->control(ctx, MPP_DEC_SET_INFO_CHANGE_READY, NULL);
}
```

## 4. 编码器高级用法

### 4.1 H.265 编码配置

```c
mpp_init(ctx, MPP_CTX_ENC, MPP_VIDEO_CodingHEVC);

mpp_enc_cfg_set_s32(cfg, "codec:type", MPP_VIDEO_CodingHEVC);
mpp_enc_cfg_set_s32(cfg, "h265:profile", 1);        /* Main */
mpp_enc_cfg_set_s32(cfg, "h265:level",   120);       /* Level 4.0 */
mpp_enc_cfg_set_s32(cfg, "h265:scaling_list", 0);    /* flat matrix */
mpp_enc_cfg_set_s32(cfg, "h265:cb_qp_offset", 0);
mpp_enc_cfg_set_s32(cfg, "h265:cr_qp_offset", 0);
mpp_enc_cfg_set_s32(cfg, "h265:dblk_disable", 0);   /* deblock 开启 */
```

### 4.2 JPEG 编码

```c
mpp_init(ctx, MPP_CTX_ENC, MPP_VIDEO_CodingMJPEG);

/* JPEG 量化等级 0~10, 10 为最高质量 */
mpp_enc_cfg_set_s32(cfg, "jpeg:quant", 8);

/* JPEG 输出格式 */
mpp_enc_cfg_set_s32(cfg, "prep:format", MPP_FMT_YUV420SP);
```

### 4.3 Slice 切分 (用于低延迟)

```c
/* 按字节大小切分 */
mpp_enc_cfg_set_u32(cfg, "split:mode", MPP_ENC_SPLIT_BY_BYTE);
mpp_enc_cfg_set_u32(cfg, "split:arg",  65536);  /* 每个 slice 最大 64KB */

/* 按 CTU/宏块数切分 */
mpp_enc_cfg_set_u32(cfg, "split:mode", MPP_ENC_SPLIT_BY_CTU);
mpp_enc_cfg_set_u32(cfg, "split:arg",  10);     /* 每个 slice 10 个 CTU */
```

### 4.4 码率控制策略

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| CBR | 固定码率, `bps_target` 为主 | 实时推流/视频会议 |
| VBR | 可变码率, `bps_max/min` 为主 | 存储录像 |
| FIX_QP | 固定 QP, 不控制码率 | 调试/性能评估 |

**码率建议:**
- 1080p@30fps H.264: CBR 4~8Mbps
- 4K@30fps H.265: CBR 10~20Mbps
- 全 I 帧 (gop=1): 码率需提升 3~5 倍

### 4.5 自定义码率控制插件

```c
/* MPP 支持注册自定义码控策略 */
RcImplApi my_rc = {
    .name = "my_custom_rc",
    .type = MPP_VIDEO_CodingAVC,
    .init = my_rc_init,
    .proc = my_rc_proc,     /* 每帧调用: 输入统计信息, 输出 QP 等参数 */
    .deinit = my_rc_deinit,
};
mpi->control(ctx, MPP_ENC_SET_RC_API_CFG, &my_rc);

/* 激活自定义码控 */
RcApiBrief brief = { .name = "my_custom_rc", .type = MPP_VIDEO_CodingAVC };
mpi->control(ctx, MPP_ENC_SET_RC_API_CURRENT, &brief);
```

## 5. Demo 命令参考

### 5.1 mpi_dec_test

```bash
# H.264 解码 (type=7)
mpi_dec_test -t 7 -i input.h264 -n 100
# H.265 解码 (type=16777220)
mpi_dec_test -t 16777220 -i input.h265
# VP9 解码 (type=10) + 输出保存
mpi_dec_test -t 10 -i input.vp9 -o output.yuv

# 参数说明:
# -i 输入文件 (必选)
# -t 码流类型 (必选, 见 MppCodingType)
# -o 输出文件
# -w 图像宽度
# -h 图像高度
# -n 解码帧数
```

### 5.2 mpi_enc_test

```bash
# H.264 编码
mpi_enc_test -w 1920 -h 1080 -t 7 -i input.yuv -o output.h264 -n 100
# 不指定输入: 编码器自动生成彩条

# 参数说明:
# -w 宽度 (必选)
# -h 高度 (必选)
# -t 编码类型 (必选)
# -i 输入 YUV 文件
# -o 输出码流文件
# -n 编码帧数
```

## 6. 编码器 stride 与内存排布

### 6.1 1920x1080 示例

**情况 A (ver_stride=1088, 有空行):**
```
Y 分量: 1920 × 1080
空行:   1920 × 8     (1088-1080=8 行)
UV 分量: 1920 × 540
总大小: 1920 × 1088 × 3/2 = 3,133,440 bytes
```

**情况 B (ver_stride=1080, 无空行):**
```
Y 分量: 1920 × 1080
UV 分量: 1920 × 540  (紧接 Y)
总大小: 1920 × 1080 × 3/2 = 3,110,400 bytes
注意: 需额外分配 1920×4 填充, 否则硬件 16 对齐读取越界
```

### 6.2 通用计算公式

```
buf_size = hor_stride × ver_stride × factor
  YUV420: factor = 3/2
  YUV422: factor = 2
  RGB888: factor = 3
  ARGB:   factor = 4

hor_stride ≥ width (通常等于 width, 或 16/32 对齐)
ver_stride ≥ height (通常 16 对齐, 如 1080→1088)
```

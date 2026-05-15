# RkAiq API 完整参考与代码示例

## 1. 系统控制 API

### 1.1 完整初始化流程

```c
#include "rk_aiq_uapi2_sysctl.h"

int camera_init(const char *sns_ent_name, const char *iq_dir)
{
    rk_aiq_sys_ctx_t *ctx = NULL;
    rk_aiq_working_mode_t mode = RK_AIQ_WORKING_MODE_NORMAL;
    
    /* 预初始化 (可选, 设置 HDR 模式) */
    rk_aiq_uapi2_sysctl_preInit(sns_ent_name, mode, NULL);
    
    /* 初始化: 绑定 sensor, 指定 IQ 文件目录 */
    int ret = rk_aiq_uapi2_sysctl_init(sns_ent_name, iq_dir,
        NULL,   /* error callback */
        NULL,   /* metas callback */
        &ctx);
    if (ret != XCAM_RETURN_NO_ERROR) {
        printf("aiq init failed: %d\n", ret);
        return -1;
    }
    
    /* 准备: 设置分辨率 (0,0 表示跟随 sensor) */
    rk_aiq_uapi2_sysctl_prepare(ctx, 0, 0, mode);
    
    /* 启动 3A */
    rk_aiq_uapi2_sysctl_start(ctx);
    
    return 0;
}

void camera_deinit(rk_aiq_sys_ctx_t *ctx)
{
    rk_aiq_uapi2_sysctl_stop(ctx, false);
    rk_aiq_uapi2_sysctl_deinit(ctx);
}
```

### 1.2 获取 Sensor 信息

```c
/* 通过 video 节点查找绑定的 sensor entity 名称 */
const char *sns_name = rk_aiq_uapi2_sysctl_getBindedSnsEntNmByVd("/dev/video0");
printf("Sensor: %s\n", sns_name);

/* 获取静态元信息 */
rk_aiq_static_info_t static_info;
rk_aiq_uapi2_sysctl_getStaticMetas(sns_name, &static_info);
printf("Sensor info: %s, has_lens=%d\n",
    static_info.sensor_info.sensor_name,
    static_info.has_lens_vcm);
```

### 1.3 场景切换

```c
/* 预初始化场景 (在 init 之前) */
rk_aiq_uapi2_sysctl_preInit_scene(sns_name, "normal", "day");

/* 运行时切换场景 */
rk_aiq_uapi2_sysctl_switch_scene(ctx, "normal", "night");
```

### 1.4 运行时更新 IQ 文件

```c
/* 动态更新 IQ 参数 (不需要重启) */
rk_aiq_uapi2_sysctl_updateIq(ctx, "/etc/iqfiles/new_iq.xml");
```

## 2. AE (自动曝光) API

### 2.1 曝光模式控制

```c
#include "rk_aiq_uapi2_ae.h"

/* 设置为自动曝光 */
rk_aiq_uapi2_setExpMode(ctx, OP_AUTO);

/* 设置为手动曝光 */
rk_aiq_uapi2_setExpMode(ctx, OP_MANUAL);

/* 手动设置曝光参数 */
Uapi_ExpSwAttrV2_t exp_attr;
rk_aiq_user_api2_ae_getExpSwAttr(ctx, &exp_attr);
exp_attr.stManual.LinearAE.ManualTimeEn = true;
exp_attr.stManual.LinearAE.ManualGainEn = true;
exp_attr.stManual.LinearAE.TimeValue = 0.01;     /* 10ms */
exp_attr.stManual.LinearAE.GainValue = 2.0;      /* 2x gain */
rk_aiq_user_api2_ae_setExpSwAttr(ctx, &exp_attr);
```

### 2.2 曝光范围限制

```c
/* 限制曝光时间范围 */
Uapi_ExpSwAttrV2_t attr;
rk_aiq_user_api2_ae_getExpSwAttr(ctx, &attr);
attr.stAuto.stLinAeRoute.TimeDev.stLinTimeDev.fCoeff = 1.0;
/* 设置 gain 范围 */
attr.stAuto.stLinAeRoute.GainDev.stLinGainDev.fCoeff = 1.0;
rk_aiq_user_api2_ae_setExpSwAttr(ctx, &attr);
```

### 2.3 获取当前曝光信息

```c
Uapi_ExpQueryInfo_t exp_info;
rk_aiq_user_api2_ae_queryExpResInfo(ctx, &exp_info);
printf("CurExpTime: %f, CurGain: %f, CurLuma: %d\n",
    exp_info.CurExpInfo.LinearExp.exp_real_params.analog_gain,
    exp_info.CurExpInfo.LinearExp.exp_real_params.integration_time,
    exp_info.MeanLuma);
```

## 3. AWB (自动白平衡) API

### 3.1 白平衡模式

```c
#include "rk_aiq_uapi2_awb.h"

/* 自动白平衡 */
rk_aiq_uapi2_setWBMode(ctx, OP_AUTO);

/* 手动白平衡 - 设置增益 */
rk_aiq_wb_gain_t wb_gain = {
    .rgain  = 1.8,   /* R 增益 */
    .grgain = 1.0,   /* Gr 增益 */
    .gbgain = 1.0,   /* Gb 增益 */
    .bgain  = 1.5,   /* B 增益 */
};
rk_aiq_uapi2_setWBMode(ctx, OP_MANUAL);
rk_aiq_uapi2_setMWBGain(ctx, &wb_gain);

/* 手动白平衡 - 设置色温 */
rk_aiq_uapi2_setMWBCT(ctx, 5000);  /* 5000K */
```

### 3.2 获取 AWB 信息

```c
rk_aiq_wb_querry_info_t wb_info;
rk_aiq_user_api2_awb_QueryWBInfo(ctx, &wb_info);
printf("gain: R=%.2f G=%.2f B=%.2f, CT=%dK\n",
    wb_info.gain.rgain, wb_info.gain.grgain,
    wb_info.gain.bgain, wb_info.cctGloabl);
```

## 4. AF (自动聚焦) API

```c
#include "rk_aiq_uapi2_af.h"

/* 设置 AF 模式 */
rk_aiq_uapi2_setFocusMode(ctx, OP_AUTO);     /* 自动聚焦 */
rk_aiq_uapi2_setFocusMode(ctx, OP_MANUAL);   /* 手动聚焦 */

/* 手动设置焦距 */
rk_aiq_uapi2_setOpZoomPosition(ctx, 100);     /* 变焦位置 */
rk_aiq_uapi2_setFixedModeCode(ctx, 64);       /* 对焦步进值 */

/* AF 搜索 */
rk_aiq_uapi2_setFocusMode(ctx, OP_SEMI_AUTO); /* 触发一次对焦 */
```

## 5. 图像增强 API

### 5.1 降噪强度

```c
/* 设置降噪总体强度 (0-100) */
rk_aiq_uapi2_setStrength(ctx, true,  50);  /* 空域降噪 */
rk_aiq_uapi2_setStrength(ctx, false, 50);  /* 时域降噪 (ISPP) */

/* 精细控制各 NR 模块 */
/* BNR, YNR, CNR 分别有独立 API */
```

### 5.2 Gamma

```c
#include "rk_aiq_uapi2_agamma.h"

rk_aiq_gamma_attr_t gamma_attr;
rk_aiq_user_api2_agamma_GetAttrib(ctx, &gamma_attr);

/* 使用预设曲线 */
gamma_attr.mode = RK_AIQ_GAMMA_MODE_FAST;
gamma_attr.stFast.GammaCoef = 2.2;  /* gamma 系数 */

/* 或自定义 LUT */
gamma_attr.mode = RK_AIQ_GAMMA_MODE_MANUAL;
gamma_attr.stManual.Gamma_curve[0] = 0;
gamma_attr.stManual.Gamma_curve[1] = 100;
/* ... 共 256 个点 ... */

rk_aiq_user_api2_agamma_SetAttrib(ctx, gamma_attr);
```

### 5.3 锐化

```c
/* 控制锐化强度 */
/* 通过 setStrength API 或者直接操作 sharp attr */
```

### 5.4 去雾

```c
#include "rk_aiq_uapi2_adehaze.h"

rk_aiq_dehaze_attr_t dehaze_attr;
rk_aiq_user_api2_adehaze_getSwAttrib(ctx, &dehaze_attr);

dehaze_attr.mode = RK_AIQ_DEHAZE_MODE_AUTO;
dehaze_attr.stAuto.DehazePara.dehaze_en = true;
dehaze_attr.stAuto.DehazePara.strength = 80;

rk_aiq_user_api2_adehaze_setSwAttrib(ctx, dehaze_attr);
```

## 6. 补光灯控制 API

```c
#include "rk_aiq_uapi2_sysctl.h"

/* 配置补光灯 */
rk_aiq_cpsl_cfg_t cpsl_cfg;
cpsl_cfg.mode = RK_AIQ_OP_MODE_AUTO;     /* 自动模式 */
cpsl_cfg.lght_src = RK_AIQ_CPSLS_LED;    /* LED 光源 */
cpsl_cfg.gray_on = false;
cpsl_cfg.u.a.sensitivity = 50;           /* 触发灵敏度 */
cpsl_cfg.u.a.sw_interval = 60;           /* 切换间隔 (秒) */
rk_aiq_uapi2_sysctl_setCpsLtCfg(ctx, &cpsl_cfg);

/* 查询补光灯状态 */
rk_aiq_cpsl_info_t cpsl_info;
rk_aiq_uapi2_sysctl_getCpsLtInfo(ctx, &cpsl_info);
printf("Light on: %d, strength: %f\n", cpsl_info.on, cpsl_info.strength_led);
```

## 7. 自定义 3A 算法开发

### 7.1 自定义 AE

```c
#include "rk_aiq_uapi2_customAe.h"

/* 定义回调函数 */
static int my_ae_init(void *ctx)
{
    /* 初始化自定义 AE 算法 */
    return 0;
}

static int my_ae_run(void *ctx, const rk_aiq_customAe_stats_t *stats,
                     rk_aiq_customAe_results_t *result)
{
    /* stats 包含:
     * - rawae_stat: RAW 域 AE 统计 (分块亮度)
     * - extra: 额外信息 (当前曝光参数等)
     */
    
    /* 根据统计信息计算新的曝光参数 */
    uint32_t mean_luma = 0;
    for (int i = 0; i < 225; i++) {  /* 15×15 网格 */
        mean_luma += stats->rawae_stat.channelr_xy[i];
    }
    mean_luma /= 225;
    
    /* 设置结果 */
    result->exp_result.new_ae_exp.LinearExp.exp_sensor_params.analog_gain_code_global = 16;
    result->exp_result.new_ae_exp.LinearExp.exp_sensor_params.coarse_integration_time = 200;
    
    return 0;
}

static int my_ae_ctrl(void *ctx, uint32_t cmd, void *param)
{
    return 0;
}

static int my_ae_exit(void *ctx)
{
    return 0;
}

/* 注册自定义 AE */
rk_aiq_customeAe_cbs_t ae_cbs = {
    .pfn_ae_init = my_ae_init,
    .pfn_ae_run  = my_ae_run,
    .pfn_ae_ctrl = my_ae_ctrl,
    .pfn_ae_exit = my_ae_exit,
};

rk_aiq_uapi2_customAE_register(ctx, &ae_cbs);
rk_aiq_uapi2_customAE_enable(ctx, true);

/* 禁用并注销 */
rk_aiq_uapi2_customAE_enable(ctx, false);
rk_aiq_uapi2_customAE_unRegister(ctx);
```

### 7.2 自定义 AWB

```c
#include "rk_aiq_uapi2_customAwb.h"

static int my_awb_run(void *ctx, const rk_aiq_customAwb_stats_t *stats,
                      rk_aiq_customeAwb_results_t *result)
{
    /* stats 包含:
     * - light: 各色温光源的白点统计
     * - wp_num: 白点数量
     */
    
    /* 计算 WB Gain */
    result->wbGainAlgo.rgain  = 1.8;
    result->wbGainAlgo.grgain = 1.0;
    result->wbGainAlgo.gbgain = 1.0;
    result->wbGainAlgo.bgain  = 1.5;
    
    return 0;
}

/* 注册和使能 */
rk_aiq_customeAwb_cbs_t awb_cbs = {
    .pfn_awb_init = my_awb_init,
    .pfn_awb_run  = my_awb_run,
    .pfn_awb_ctrl = my_awb_ctrl,
    .pfn_awb_exit = my_awb_exit,
};
rk_aiq_uapi_customAWB_register(ctx, &awb_cbs);
rk_aiq_uapi_customAWB_enable(ctx, true);
```

### 7.3 AF 统计配置

```c
/* AF 统计模块配置 */
/* 1. 配置 AF 统计窗口 */
/* 2. 配置 Focus Filter (高通滤波器) */
/* 3. Gamma 校正 (统计前) */
/* 4. Luma/Highlight 统计 */
/* 5. Luma Depend Gain (亮度依赖增益) */
/* 6. Fv threshold (焦点值阈值) */
/* 7. Fv Calc (焦点值计算) */

/* AF 统计结果可用于自定义 AF 算法 */
```

## 8. 编译与链接

### 8.1 头文件

```
camera_engine_rkaiq/
├── include/
│   ├── uAPI2/
│   │   ├── rk_aiq_uapi2_sysctl.h
│   │   ├── rk_aiq_uapi2_ae.h
│   │   ├── rk_aiq_uapi2_awb.h
│   │   ├── rk_aiq_uapi2_af.h
│   │   ├── rk_aiq_uapi2_agamma.h
│   │   ├── rk_aiq_uapi2_adehaze.h
│   │   ├── rk_aiq_uapi2_customAe.h
│   │   └── rk_aiq_uapi2_customAwb.h
│   └── common/
│       ├── rk_aiq_types.h
│       └── rk_aiq_comm.h
└── lib/
    └── librkaiq.so
```

### 8.2 CMake 示例

```cmake
find_package(PkgConfig)
pkg_check_modules(RKAIQ REQUIRED librkaiq)

target_include_directories(myapp PRIVATE ${RKAIQ_INCLUDE_DIRS})
target_link_libraries(myapp ${RKAIQ_LIBRARIES})
```

### 8.3 链接库

```
librkaiq.so          # RkAiq 核心库
librkisp_api.so      # V4L2 封装 API (简化接口)
```

## 9. 调试技巧

### 9.1 Log 级别控制

```bash
# 各模块独立控制
export persist_camera_engine_log=0xff    # 全部开启
export persist_camera_engine_log=0x01    # AE only
export persist_camera_engine_log=0x02    # AWB only
export persist_camera_engine_log=0x04    # AF only
export persist_camera_engine_log=0x08    # AHDR
export persist_camera_engine_log=0x10    # ANR
# 组合: 0x03 = AE + AWB

# Log 输出路径
# 默认: /tmp/rkaiq_log/
# 也可通过 stdout 查看
```

### 9.2 ISP 统计信息获取

```bash
# 通过 /dev/video 节点获取 statistics
# rkisp-statistics 节点提供 AE/AWB/AF 统计原始数据

# 通过 debugfs 查看 ISP 参数
cat /sys/kernel/debug/rkisp*/params_readable
```

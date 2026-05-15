---
name: rk_npu
description: "Rockchip 瑞芯微 NPU 神经网络推理技能，覆盖 RKNN SDK (RKNN-Toolkit2 + RKNPU2 Runtime) 全流程：模型转换、板端部署、C API 推理、零拷贝优化、多核调度、SRAM 加速、量化精度分析。适用于 RK3588/RK3568/RK3566/RV1103/RV1106 等全系列 NPU 芯片。触发关键词：NPU、RKNN、rknn_init、rknn_run、rknn_inputs_set、rknn_outputs_get、rknn_set_core_mask、rknn_create_mem、rknn_set_io_mem、librknnrt、rknn_server、RKNN-Toolkit2、rknn.config、rknn.build、rknn.export_rknn、rknn.load_onnx、rknn.eval_perf、rknn.accuracy_analysis、混合量化、模型转换、ONNX 转 RKNN、int8 量化、fp16 推理、零拷贝、zero-copy、NC1HWC2、多核、NPU_CORE_AUTO、SRAM、NPU 利用率、NPU 频率、逐层耗时、NPU 推理慢、量化精度低、模型部署、YOLOv5、目标检测。当用户在 Rockchip 平台上遇到 NPU 推理、模型转换、量化部署、性能调优等问题时触发。"
---

# Rockchip NPU / RKNN SDK 推理技能

## 快速导航

| 问题类型 | 跳转 |
|---------|------|
| NPU 硬件参数与算力 | §1 |
| RKNN SDK 开发流程 | §2 |
| RKNN-Toolkit2 模型转换 | §3 |
| C API 推理（通用 API） | §4 |
| 零拷贝 API | §5 |
| 多核调度 (RK3588) | §6 |
| SRAM 加速 (RK3588) | §7 |
| 量化策略与精度调优 | §8 |
| 调试方法 | §9 |
| 常见故障排查 | §10 |
---

## 1. NPU 硬件参数

### 1.1 芯片算力一览

| 芯片 | NPU 核心数 | 算力 (TOPS) | 最高频率 | 备注 |
|------|-----------|-------------|---------|------|
| RK3588 | 3 | 6 (3×2) | 1 GHz | 三核可独立/组合；含 SRAM 956KB |
| RK3568 | 1 | 1 | 1 GHz | 单核 |
| RK3566 | 1 | 0.8 | - | 单核 |
| RV1106 | 1 | 0.5 | - | 精简 API（无 rknn_inputs_set/rknn_outputs_get） |
| RV1103 | 1 | 0.5 | - | 同 RV1106 |

### 1.2 NPU 内部处理流程

```
输入数据 → [量化(int8)] → NPU 计算 → [反量化] → 输出数据

优化路径（int8 模型）：
  输入(int8) → 直送 NPU core → 输出(int8)  ← 零拷贝最优

通用路径：
  输入(uint8/float) → 内部转换+量化 → NPU core → 反量化 → 输出(float32)
```

### 1.3 支持的数据类型

| 类型 | 说明 |
|------|------|
| int8 asymmetric | 默认量化类型，性能最优 |
| float16 | 非量化模式，精度最高 |
| int16 asymmetric | 暂不支持 |

---

## 2. RKNN SDK 开发流程

### 2.1 整体架构

```
PC 端（模型转换 + 模拟器推理）           板端（部署推理）
┌─────────────────────────────┐    ┌──────────────────────────┐
│  RKNN-Toolkit2 (Python)     │    │  librknnrt.so (C API)    │
│  ├─ 模型加载 (ONNX/TF/PT)  │    │  ├─ rknn_init            │
│  ├─ config (均值/量化)      │    │  ├─ rknn_inputs_set      │
│  ├─ build (量化构建)        │    │  ├─ rknn_run             │
│  ├─ export_rknn            │───→│  ├─ rknn_outputs_get     │
│  ├─ accuracy_analysis      │    │  └─ rknn_destroy          │
│  └─ eval_perf / eval_memory│    │                          │
└─────────────────────────────┘    │  rknn_server (连板代理)   │
         │ USB 连板调试              └──────────────────────────┘
         └──────────────────────────────────┘
```

### 2.2 标准开发流程

```
1. PC: 训练模型 → 导出 ONNX/TF/PT/Caffe
2. PC: RKNN-Toolkit2 转换 → .rknn 模型
3. PC: 模拟器验证 or 连板推理验证
4. 板端: 交叉编译 C/C++ → 调用 librknnrt.so 推理
```

### 2.3 SDK 目录结构

```
rknpu2/
├── doc/
├── examples/
│   ├── rknn_api_demo/          # 零拷贝 API 示例
│   ├── rknn_mobilenet_demo/
│   ├── rknn_yolov5_demo/
│   └── rknn_ssd_demo/
└── runtime/
    ├── RK356X/{Android,Linux}/librknn_api/
    ├── RK3588/{Android,Linux}/librknn_api/
    └── RV1106/Linux/librknn_api/
```

---

## 3. RKNN-Toolkit2 模型转换

### 3.1 基本转换流程 (Python)

```python
from rknn.api import RKNN
rknn = RKNN(verbose=True)

# 1. 配置预处理参数
rknn.config(
    mean_values=[[123.675, 116.28, 103.53]],
    std_values=[[58.395, 57.12, 57.375]],
    target_platform='rk3588',            # 必须指定目标平台
    quantized_dtype='asymmetric_quantized-8',
    quantized_algorithm='normal',        # normal / mmse / kl_divergence
    quantized_method='channel',          # channel / layer
)

# 2. 加载模型
rknn.load_onnx(model='./yolov5s.onnx')
# 或: load_pytorch / load_tensorflow / load_tflite / load_caffe / load_darknet

# 3. 构建 RKNN 模型
rknn.build(do_quantization=True, dataset='./dataset.txt')
# dataset.txt: 每行一个图片路径，推荐 50~200 张

# 4. 导出
rknn.export_rknn('./yolov5s.rknn')
rknn.release()
```

### 3.2 config 关键参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| mean_values | 输入均值，与训练一致 | None |
| std_values | 输入归一化值 | None |
| target_platform | 目标芯片: rk3566/rk3568/rk3588/rv1103/rv1106 | 必填 |
| quantized_dtype | asymmetric_quantized-8 | -8 |
| quantized_algorithm | normal(快)/mmse(慢精高)/kl_divergence | normal |
| quantized_method | channel(精度高) / layer(兼容) | channel |
| quant_img_RGB2BGR | 量化图加载时 RGB→BGR（Caffe 模型常用） | False |
| optimization_level | 0~3，3=全开优化 | 3 |
| compress_weight | 压缩权重减小模型体积 | False |
| single_core_mode | 仅生成单核模型（减体积，仅 RK3588） | False |
| remove_weight | 去除权重生成从模型（用于共享权重） | False |
| custom_string | 自定义字符串嵌入模型 | None |

### 3.3 连板推理与评估

```python
# 连板推理
rknn.init_runtime(target='rk3588', device_id='xxx', perf_debug=True)
outputs = rknn.inference(inputs=[img])

# 性能评估
rknn.eval_perf()

# 内存评估
rknn.init_runtime(target='rk3588', eval_mem=True)
rknn.eval_memory()

# 量化精度分析 - 输出每层余弦距离
rknn.accuracy_analysis(inputs=['./test.jpg'], target='rk3588')
```

### 3.4 支持的模型框架

load_onnx(model=) / load_pytorch(model=, input_size_list=, torchscript .pt) /
load_tensorflow(tf_pb=, inputs=, outputs=, input_size_list=) / load_tflite(model=) /
load_caffe(model=, blobs=) / load_darknet(model=, weight=)

---

## 4. C API 推理（通用 API）

> **注意：RV1106/RV1103 不支持 rknn_inputs_set / rknn_outputs_get，必须使用零拷贝 API**

### 4.1 标准推理流程

```c
#include "rknn_api.h"

rknn_context ctx;

// 1. 初始化
rknn_init(&ctx, model_data, model_data_size, 0, NULL);

// 2. 查询输入输出信息
rknn_input_output_num io_num;
rknn_query(ctx, RKNN_QUERY_IN_OUT_NUM, &io_num, sizeof(io_num));

rknn_tensor_attr input_attrs[io_num.n_input];
memset(input_attrs, 0, sizeof(input_attrs));
for (int i = 0; i < io_num.n_input; i++) {
    input_attrs[i].index = i;
    rknn_query(ctx, RKNN_QUERY_INPUT_ATTR, &(input_attrs[i]),
               sizeof(rknn_tensor_attr));
}

// 3. 设置输入
rknn_input inputs[1];
memset(inputs, 0, sizeof(inputs));
inputs[0].index = 0;
inputs[0].type = RKNN_TENSOR_UINT8;
inputs[0].size = width * height * channels;
inputs[0].fmt = RKNN_TENSOR_NHWC;
inputs[0].buf = img_data;
inputs[0].pass_through = 0;  // 0=自动预处理, 1=直传
rknn_inputs_set(ctx, 1, inputs);

// 4. 执行推理
rknn_run(ctx, NULL);

// 5. 获取输出
rknn_output outputs[io_num.n_output];
memset(outputs, 0, sizeof(outputs));
for (int i = 0; i < io_num.n_output; i++) {
    outputs[i].index = i;
    outputs[i].want_float = 1;  // 1=输出 float32, 0=原始类型
    outputs[i].is_prealloc = 0; // 0=RKNN 分配内存
}
rknn_outputs_get(ctx, io_num.n_output, outputs, NULL);

// 6. 后处理...

// 7. 释放
rknn_outputs_release(ctx, io_num.n_output, outputs);
rknn_destroy(ctx);
```

### 4.2 rknn_init 标志位

| 标志 | 功能 | 用途 |
|------|------|------|
| 0 | 默认模式 | 常规使用 |
| RKNN_FLAG_COLLECT_PERF_MASK | 收集逐层耗时 | 性能分析 |
| RKNN_FLAG_MEM_ALLOC_OUTSIDE | 所有内存由用户分配 | 内存复用（RV1103/RV1106 内存紧张场景） |
| RKNN_FLAG_SHARE_WEIGHT_MEM | 共享权重内存 | 不定长输入（多分辨率模型共享权重） |

### 4.3 rknn_query 查询命令

| 命令 | 返回结构体 | 功能 |
|------|-----------|------|
| RKNN_QUERY_IN_OUT_NUM | rknn_input_output_num | 输入输出 tensor 个数 |
| RKNN_QUERY_INPUT_ATTR | rknn_tensor_attr | 输入 tensor 属性 |
| RKNN_QUERY_OUTPUT_ATTR | rknn_tensor_attr | 输出 tensor 属性 |
| RKNN_QUERY_PERF_DETAIL | rknn_perf_detail | 逐层耗时(需 PERF_MASK) |
| RKNN_QUERY_PERF_RUN | rknn_perf_run | 推理总耗时(us) |
| RKNN_QUERY_SDK_VERSION | rknn_sdk_version | SDK 版本信息 |
| RKNN_QUERY_MEM_SIZE | rknn_mem_size | 内存占用(权重/中间/DMA/SRAM) |
| RKNN_QUERY_CUSTOM_STRING | rknn_custom_string | 自定义字符串 |
| RKNN_QUERY_NATIVE_INPUT_ATTR | rknn_tensor_attr | 原生输入属性(零拷贝) |
| RKNN_QUERY_NATIVE_OUTPUT_ATTR | rknn_tensor_attr | 原生输出属性(零拷贝) |
| RKNN_QUERY_NATIVE_NHWC_INPUT_ATTR | rknn_tensor_attr | NHWC 输入属性(零拷贝) |
| RKNN_QUERY_NATIVE_NHWC_OUTPUT_ATTR | rknn_tensor_attr | NHWC 输出属性(零拷贝) |

### 4.4 错误码

0=成功, -1=失败, -2=超时, -3=NPU不可用, -4=内存分配失败, -5=参数无效, -6=模型无效, -7=ctx无效, -8=输入无效, -9=输出无效, -10=版本不匹配, -13=平台不兼容

---

## 5. 零拷贝 API

### 5.1 零拷贝优势

- 避免 rknn_inputs_set 的内存拷贝开销
- 直接操作 DMA buffer，可与 RGA/Camera/MPP 共享内存
- RV1106/RV1103 只支持零拷贝 API

### 5.2 零拷贝推理流程

```c
rknn_context ctx;
rknn_init(&ctx, model_data, model_size, 0, NULL);

// 1. 查询原生属性
rknn_tensor_attr input_attrs[1], output_attrs[1];
input_attrs[0].index = 0;
rknn_query(ctx, RKNN_QUERY_NATIVE_INPUT_ATTR, &input_attrs[0],
           sizeof(rknn_tensor_attr));
output_attrs[0].index = 0;
rknn_query(ctx, RKNN_QUERY_NATIVE_OUTPUT_ATTR, &output_attrs[0],
           sizeof(rknn_tensor_attr));

// 2. 创建输入输出内存
rknn_tensor_mem* input_mems[1];
rknn_tensor_mem* output_mems[1];
input_mems[0] = rknn_create_mem(ctx, input_attrs[0].size_with_stride);
output_mems[0] = rknn_create_mem(ctx, output_attrs[0].size_with_stride);

// 3. 绑定内存
rknn_set_io_mem(ctx, input_mems[0], &input_attrs[0]);
rknn_set_io_mem(ctx, output_mems[0], &output_attrs[0]);

// 4. 填充输入（直接写入 DMA buffer）
memcpy(input_mems[0]->virt_addr, img_data, img_size);

// 5. 推理
rknn_run(ctx, NULL);

// 6. 读取输出（直接从 DMA buffer 读取）
int8_t* output_data = (int8_t*)output_mems[0]->virt_addr;

// 7. 清理
rknn_destroy_mem(ctx, input_mems[0]);
rknn_destroy_mem(ctx, output_mems[0]);
rknn_destroy(ctx);
```

### 5.3 外部内存零拷贝（与 RGA/Camera 共享）

```c
// 从 fd 创建（如 DRM/DMA-BUF）
rknn_tensor_mem* mem = rknn_create_mem_from_fd(ctx, dma_fd, virt_addr, size, 0);

// 从物理地址创建
rknn_tensor_mem* mem = rknn_create_mem_from_phys(ctx, phys_addr, virt_addr, size);
```

### 5.4 NC1HWC2 数据排布

零拷贝模式下 NPU 原生输出格式可能是 NC1HWC2（非标准 NCHW/NHWC）。

| 平台 | int8 时 C2 值 | float16 时 C2 值 |
|------|--------------|-----------------|
| RK356X | 8 | 4 |
| RK3588 | 16 | 8 |
| RV1106/RV1103 | 16 | 8 |

**NC1HWC2 → NCHW 转换代码见 → [references/rknn_api_detail.md](references/rknn_api_detail.md)**

### 5.5 零拷贝输入输出支持配置

**RK356X/RK3588 零拷贝输入**：与通用 API 一致

**RV1106/RV1103 零拷贝输入**：

| 数据类型 | pass_through | channel 数 | Layout |
|---------|-------------|-----------|--------|
| uint8 | 0 | - | NHWC（仅 int8 模型） |
| int8 | 1 | 1,3,4 | NHWC |

**零拷贝输出配置**：

| 平台 | 数据类型 | Layout | 备注 |
|------|---------|--------|------|
| RK356X/RK3588 | float32 | NCHW | - |
| RK356X/RK3588 | int8 | NCHW/NC1HWC2 | int8 模型 |
| RK356X/RK3588 | float16 | NCHW/NC1HWC2 | fp16 模型 |
| RV1106/RV1103 | int8 | NC1HWC2 | 仅 int8 模型 |

---

## 6. 多核调度 (RK3588)

### 6.1 核心掩码

```c
// 仅 RK3588 支持，其他平台调用返回错误
rknn_set_core_mask(ctx, RKNN_NPU_CORE_AUTO);      // 自动调度（默认）
rknn_set_core_mask(ctx, RKNN_NPU_CORE_0);          // 固定 Core0
rknn_set_core_mask(ctx, RKNN_NPU_CORE_0_1);        // 双核并行
rknn_set_core_mask(ctx, RKNN_NPU_CORE_0_1_2);      // 三核并行
```

### 6.2 多核加速支持的 OP

双核/三核模式下以下 OP 可获得加速：**Conv、DepthwiseConv、Add、Concat、Relu、Clip、Relu6、ThresholdedRelu、PRelu、LeakyRelu**

其余 OP（如 Pool、ConvTranspose）将 fallback 到单核 Core0。

### 6.3 多线程权重复用

```c
// 同一模型双线程推理，共享权重节省内存（RK356X/RK3588 支持）
rknn_context ctx_in, ctx_out;
rknn_init(&ctx_in, model, 0, 0, NULL);
rknn_dup_context(&ctx_in, &ctx_out);
// ctx_in 和 ctx_out 可在不同线程独立 run
```

---

## 7. SRAM 加速 (RK3588)

RK3588 内含 1MB SRAM，可供 NPU 使用 956KB，减轻 DDR 带宽压力。

### 7.1 启用条件

- NPU 驱动版本 ≥ 0.8.0
- 内核 CONFIG_ROCKCHIP_RKNPU_SRAM=y
- DTS 分配 SRAM 给 RKNPU（注意不与编解码模块 SRAM 重叠）

### 7.2 DTS 配置

```dts
syssram: sram@ff001000 {
    compatible = "mmio-sram";
    reg = <0x0 0xff001000 0x0 0xef000>;
    #address-cells = <1>;
    #size-cells = <1>;
    ranges = <0x0 0x0 0xff001000 0xef000>;
    rknpu_sram: rknpu_sram@0 {
        reg = <0x0 0xef000>; // 956KB
    };
};
// rk3588s.dtsi 中 rknpu 节点增加:
// rockchip,sram = <&rknpu_sram>;
```

### 7.3 环境变量设置

```bash
# Internal 使用 SRAM（自动大小）
export RKNN_INTERNAL_MEM_TYPE=sram

# Internal 使用 SRAM（指定 256KB）
export RKNN_INTERNAL_MEM_TYPE=sram#256

# Weight 使用 SRAM
export RKNN_SEPARATE_WEIGHT_MEM=1
export RKNN_WEIGHT_MEM_TYPE=sram

# 混合：Internal 256KB + Weight 128KB
export RKNN_INTERNAL_MEM_TYPE=sram#256
export RKNN_SEPARATE_WEIGHT_MEM=1
export RKNN_WEIGHT_MEM_TYPE=sram#128
```

---

## 8. 量化策略与精度调优

### 8.1 量化算法对比

| 算法 | 速度 | 精度 | 推荐数据量 | 适用场景 |
|------|------|------|-----------|---------|
| normal | 快 | 一般 | 20~100 张 | 默认首选 |
| mmse | 很慢（暴力迭代） | 最高 | 20~50 张 | 精度敏感 |
| kl_divergence | 中等 | 较好 | 20~100 张 | feature 分布不均匀 |

### 8.2 精度问题排查流程

```
1. 验证 fp16 模型(do_quantization=False) → 对比原始框架结果
   └─ 不一致 → 检查 mean_values/std_values/RGB 顺序/输入 shape
2. fp16 正确后，验证量化模型
   └─ 精度下降 → 尝试:
      a. quantized_method: layer → channel
      b. quantized_algorithm: normal → mmse
      c. 调整 dataset 数量(50~200 张)
      d. 混合量化(指定层用 float16 计算)
3. 使用 accuracy_analysis 逐层分析余弦距离
   └─ 定位精度下降的层 → 混合量化或后处理规避
```

### 8.3 混合量化流程

```python
# Step 1: 生成量化配置文件
rknn.hybrid_quantization_step1(dataset='./dataset.txt')
# 生成 {model}.quantization.cfg / .model / .data

# Step 2: 编辑 .quantization.cfg
# 将精度下降层的输出操作数加入 custom_quantize_layers: {tensor_name: float16}

# Step 3: 构建混合量化模型
rknn.hybrid_quantization_step2(
    model_input='model.model',
    data_input='model.data',
    model_quantization_cfg='model.quantization.cfg')
rknn.export_rknn('./model_hybrid.rknn')
```

---

## 9. 调试方法

### 9.1 日志等级

```bash
export RKNN_LOG_LEVEL=<0-6>
# 0: 仅错误   1: +警告   2: +提示   3: +调试
# 4: +逐层信息（影响性能）  5: +导出逐层npy  6: +导出npy+txt
unset RKNN_LOG_LEVEL   # 恢复默认
```

### 9.2 逐层结果导出

```bash
export RKNN_DUMP_QUANT=0           # 0=float32, 1=原始类型
export RKNN_DUMP_DIR=/data/dumps
export RKNN_LOG_LEVEL=5
```

### 9.3 性能定频测试

```bash
# CPU 定频
echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
echo 1704000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed

# DDR 定频
echo userspace > /sys/class/devfreq/dmc/governor
echo 1560000000 > /sys/class/devfreq/dmc/userspace/set_freq

# NPU 定频 - RK3588
echo userspace > /sys/class/devfreq/fdab0000.npu/governor
echo 1000000000 > /sys/kernel/debug/rknpu/freq

# NPU 定频 - RK356X
echo userspace > /sys/class/devfreq/fde40000.npu/governor
echo 1000000000 > /sys/kernel/debug/clk/clk_scmi_npu/clk_rate
```

### 9.4 NPU 状态查询

```bash
cat /sys/kernel/debug/rknpu/driver_version  # 驱动版本
cat /sys/kernel/debug/rknpu/load            # 各核利用率
cat /sys/kernel/debug/rknpu/power           # 电源状态
cat /sys/kernel/debug/rknpu/freq            # 工作频率(驱动≥0.8.2)
cat /sys/kernel/debug/rknpu/volt            # 工作电压
echo on > /sys/kernel/debug/rknpu/power     # 手动开启 NPU 电源
echo 2000 > /sys/kernel/debug/rknpu/delayms # 延迟关电(ms)
```

---

## 10. 常见故障排查

### 10.1 模型加载/初始化失败

| 现象 | 可能原因 | 解决方案 |
|------|---------|---------|
| RKNN_ERR_MODEL_INVALID (-6) | 模型文件损坏或格式错误 | 重新 export_rknn；确认传入二进制 data 时 size 正确 |
| RKNN_ERR_TARGET_PLATFORM_UNMATCH (-13) | 模型与芯片不匹配 | config 时 target_platform 与板端芯片一致 |
| RKNN_ERR_DEVICE_UNAVAILABLE (-3) | NPU 设备不可用 | 检查驱动加载: `dmesg | grep rknpu`；确认 NPU 电源已开启 |
| RKNN_ERR_DEVICE_UNMATCH (-10) | SDK 版本不匹配 | 更新 librknnrt.so 和 rknn_server 到同一版本 |

### 10.2 推理精度问题

| 现象 | 排查方向 |
|------|---------|
| fp16 模型结果就错 | 检查 mean/std/RGB 顺序/输入 shape/输入输出节点名 |
| 量化后精度大降 | channel→mmse→混合量化；检查 dataset 是否与场景匹配 |
| 模拟器正确板端不对 | 连板 accuracy_analysis 逐层对比；更新 librknnrt.so |
| 输出全零 | 检查 pass_through 设置；确认输入数据非空 |

### 10.3 性能问题

| 现象 | 排查方向 |
|------|---------|
| 推理时间波动大 | CPU/DDR/NPU 定频后测试 |
| 比预期慢 | 检查 want_float 反量化开销；使用零拷贝 API；RK3588 尝试多核 |
| 多模型串行内存不足(RV1103/1106) | RKNN_FLAG_MEM_ALLOC_OUTSIDE + 内存复用 |

### 10.4 内存复用示例（RV1103/RV1106）

```c
rknn_context ctx_a, ctx_b;
rknn_init(&ctx_a, model_a, 0, RKNN_FLAG_MEM_ALLOC_OUTSIDE, NULL);
rknn_init(&ctx_b, model_b, 0, RKNN_FLAG_MEM_ALLOC_OUTSIDE, NULL);

rknn_mem_size mem_a, mem_b;
rknn_query(ctx_a, RKNN_QUERY_MEM_SIZE, &mem_a, sizeof(mem_a));
rknn_query(ctx_b, RKNN_QUERY_MEM_SIZE, &mem_b, sizeof(mem_b));

uint32_t max_internal = MAX(mem_a.total_internal_size, mem_b.total_internal_size);
rknn_tensor_mem* shared = rknn_create_mem(ctx_a, max_internal);

// 分别为 ctx_a/ctx_b 创建 internal mem（从 shared fd 偏移）
rknn_tensor_mem* int_a = rknn_create_mem_from_fd(ctx_a, shared->fd,
    shared->virt_addr, mem_a.total_internal_size, 0);
rknn_set_internal_mem(ctx_a, int_a);

rknn_tensor_mem* int_b = rknn_create_mem_from_fd(ctx_b, shared->fd,
    shared->virt_addr, mem_b.total_internal_size, 0);
rknn_set_internal_mem(ctx_b, int_b);
// 串行运行 ctx_a 和 ctx_b，共享 internal 内存
```

---
### NPU 推理性能参考 (单核, INT8)
| 模型 | RK3588 | RK3568/66 | RV1106 |
|------|--------|-----------|--------|
| MobileNetV2 | ~2ms | ~8ms | ~15ms |
| YOLOv5s(640) | ~18ms | ~80ms | ~200ms |
| ResNet50 | ~6ms | ~25ms | ~60ms |

RK3588 三核并行约 2.5-2.8× 单核。用 `rknn.eval_perf()` 实测。
> **深入参考**
> - [C API 详解](references/rknn_api_detail.md) — API 参数、数据结构、NC1HWC2 转换、兼容性表
> - [Toolkit2 转换与精度](references/toolkit2_conversion.md) — Python API、量化细节、混合量化、精度排查

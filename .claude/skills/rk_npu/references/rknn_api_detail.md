# RKNN C API 完整参考

## 1. API 函数详解

### 1.1 rknn_init

```c
int rknn_init(rknn_context *context, void *model, uint32_t size, uint32_t flag,
              rknn_init_extend *extend);
```

**参数说明**：
- `context`：rknn_context 指针，调用后被赋值
- `model`：RKNN 模型的二进制数据或路径字符串
- `size`：二进制数据时=模型大小；路径时=0
- `flag`：初始化标志位组合
- `extend`：扩展信息，一般传 NULL；共享权重时传入另一个模型的 ctx

**flag 标志位详解**：

| 标志 | 作用 |
|------|------|
| RKNN_FLAG_COLLECT_PERF_MASK | 启用逐层耗时收集（配合 RKNN_QUERY_PERF_DETAIL） |
| RKNN_FLAG_MEM_ALLOC_OUTSIDE | 所有内存（输入/输出/权重/中间tensor）由用户分配 |
| RKNN_FLAG_SHARE_WEIGHT_MEM | 与 extend->ctx 指向的模型共享权重内存 |

**RKNN_FLAG_MEM_ALLOC_OUTSIDE 用途**：
1. 统筹管理整个系统内存
2. 内存复用——两个串行运行的模型可共享中间 tensor 内存（RV1103/RV1106 内存紧张场景）

```c
// 内存复用示例
rknn_context ctx_a, ctx_b;
rknn_init(&ctx_a, model_a, 0, RKNN_FLAG_MEM_ALLOC_OUTSIDE, NULL);
rknn_query(ctx_a, RKNN_QUERY_MEM_SIZE, &mem_size_a, sizeof(mem_size_a));
rknn_init(&ctx_b, model_b, 0, RKNN_FLAG_MEM_ALLOC_OUTSIDE, NULL);
rknn_query(ctx_b, RKNN_QUERY_MEM_SIZE, &mem_size_b, sizeof(mem_size_b));

max_internal = MAX(mem_size_a.total_internal_size, mem_size_b.total_internal_size);
internal_mem_max = rknn_create_mem(ctx_a, max_internal);

internal_mem_a = rknn_create_mem_from_fd(ctx_a, internal_mem_max->fd,
    internal_mem_max->virt_addr, mem_size_a.total_internal_size, 0);
rknn_set_internal_mem(ctx_a, internal_mem_a);

internal_mem_b = rknn_create_mem_from_fd(ctx_b, internal_mem_max->fd,
    internal_mem_max->virt_addr, mem_size_b.total_internal_size, 0);
rknn_set_internal_mem(ctx_b, internal_mem_b);
```

**RKNN_FLAG_SHARE_WEIGHT_MEM 用途**：
模拟不定长输入——生成多个不同分辨率模型共享同一套权重：

```c
rknn_context ctx_a, ctx_b;
rknn_init(&ctx_a, model_path_a, 0, 0, NULL);  // 正常加载模型A

rknn_init_extend extend;
extend.ctx = ctx_a;
rknn_init(&ctx_b, model_path_b, 0, RKNN_FLAG_SHARE_WEIGHT_MEM, &extend);
// model_b 是 rknn.config(remove_weight=True) 生成的无权重模型
```

### 1.2 rknn_set_core_mask（仅 RK3588）

```c
int rknn_set_core_mask(rknn_context context, rknn_core_mask core_mask);
```

| 枚举值 | 含义 |
|--------|------|
| RKNN_NPU_CORE_AUTO | 自动调度到空闲核 |
| RKNN_NPU_CORE_0 | 固定 Core0 |
| RKNN_NPU_CORE_1 | 固定 Core1 |
| RKNN_NPU_CORE_2 | 固定 Core2 |
| RKNN_NPU_CORE_0_1 | 双核并行（Core0+1） |
| RKNN_NPU_CORE_0_1_2 | 三核并行（Core0+1+2） |

多核模式下可加速 OP：Conv, DepthwiseConv, Add, Concat, Relu, Clip, Relu6, ThresholdedRelu, PRelu, LeakyRelu。其余 OP fallback 到 Core0。

### 1.3 rknn_dup_context（RK356X/RK3588）

```c
int rknn_dup_context(rknn_context *context_in, rknn_context *context_out);
```

生成指向同一模型的新 context，复用权重信息。用于多线程推理同一模型。RV1106/RV1103 暂不支持。

### 1.4 rknn_destroy

```c
int rknn_destroy(rknn_context context);
```

释放 rknn_context 及所有相关资源。

### 1.5 rknn_query

```c
int rknn_query(rknn_context context, rknn_query_cmd cmd, void* info, uint32_t size);
```

**查询命令完整列表**：

| 命令 | 结构体 | 功能 | 前置条件 |
|------|--------|------|---------|
| RKNN_QUERY_IN_OUT_NUM | rknn_input_output_num | 输入输出个数 | rknn_init 后 |
| RKNN_QUERY_INPUT_ATTR | rknn_tensor_attr | 输入属性(通用API用) | rknn_init 后 |
| RKNN_QUERY_OUTPUT_ATTR | rknn_tensor_attr | 输出属性(通用API用) | rknn_init 后 |
| RKNN_QUERY_PERF_DETAIL | rknn_perf_detail | 逐层耗时 | COLLECT_PERF_MASK + rknn_run 后 |
| RKNN_QUERY_PERF_RUN | rknn_perf_run | 推理总耗时(μs) | rknn_run 后 |
| RKNN_QUERY_SDK_VERSION | rknn_sdk_version | API/驱动版本 | rknn_init 后 |
| RKNN_QUERY_MEM_SIZE | rknn_mem_size | 内存占用 | MEM_ALLOC_OUTSIDE + rknn_init 后 |
| RKNN_QUERY_CUSTOM_STRING | rknn_custom_string | 自定义字符串 | rknn_init 后 |
| RKNN_QUERY_NATIVE_INPUT_ATTR | rknn_tensor_attr | 原生输入属性(零拷贝) | rknn_init 后 |
| RKNN_QUERY_NATIVE_OUTPUT_ATTR | rknn_tensor_attr | 原生输出属性(零拷贝) | rknn_init 后 |
| RKNN_QUERY_NATIVE_NHWC_INPUT_ATTR | rknn_tensor_attr | NHWC 输入属性(零拷贝) | rknn_init 后 |
| RKNN_QUERY_NATIVE_NHWC_OUTPUT_ATTR | rknn_tensor_attr | NHWC 输出属性(零拷贝) | rknn_init 后 |

### 1.6 rknn_inputs_set（RV1106/RV1103 不支持）

```c
int rknn_inputs_set(rknn_context context, uint32_t n_inputs, rknn_input inputs[]);
```

设置模型输入数据。每个 rknn_input 需设置 index/type/size/fmt/buf/pass_through。

**pass_through 行为**：
- `0`：RKNN 内部自动做格式转换和归一化
- `1`：数据直接送入模型，不做任何转换（width 需做 stride 对齐）

**输入数据类型兼容性**：

| 模型输入类型 | 可设置输入类型 |
|-------------|--------------|
| int8 | int8 / uint8 / float32 |
| float16 | uint8 / float16 / float32 |
| bool | bool |
| int64 | int64 |

### 1.7 rknn_run

```c
int rknn_run(rknn_context context, rknn_run_extend* extend);
```

执行一次推理。extend 当前未使用，传 NULL。

### 1.8 rknn_outputs_get / rknn_outputs_release（RV1106/RV1103 不支持）

```c
int rknn_outputs_get(rknn_context context, uint32_t n_outputs,
                     rknn_output outputs[], rknn_output_extend* extend);
int rknn_outputs_release(rknn_context context, uint32_t n_outputs,
                         rknn_output outputs[]);
```

**want_float 行为（RK356X/RK3588）**：

| want_float | 输出数据类型 | 输出 Layout |
|-----------|-------------|------------|
| 1 | float32 | NCHW |
| 0 | int8（int8模型）或 float16 | NCHW |

### 1.9 内存管理 API

```c
// NPU 内部分配
rknn_tensor_mem* rknn_create_mem(rknn_context ctx, uint32_t size);

// 从 fd 创建（DRM/DMA-BUF 共享）
rknn_tensor_mem* rknn_create_mem_from_fd(rknn_context ctx,
    int32_t fd, void *virt_addr, uint32_t size, int32_t offset);

// 从物理地址创建
rknn_tensor_mem* rknn_create_mem_from_phys(rknn_context ctx,
    uint64_t phys_addr, void *virt_addr, uint32_t size);

// 销毁
int rknn_destroy_mem(rknn_context ctx, rknn_tensor_mem* mem);

// 设置权重内存
int rknn_set_weight_mem(rknn_context ctx, rknn_tensor_mem* mem);

// 设置中间 tensor 内存
int rknn_set_internal_mem(rknn_context ctx, rknn_tensor_mem* mem);

// 设置输入/输出内存（零拷贝核心 API）
int rknn_set_io_mem(rknn_context ctx, rknn_tensor_mem* mem,
                    rknn_tensor_attr* attr);
```

---

## 2. 数据结构定义

### 2.1 rknn_tensor_attr

| 成员 | 类型 | 说明 |
|------|------|------|
| index | uint32_t | tensor 索引 |
| n_dims | uint32_t | 维度个数 |
| dims | uint32_t[] | 各维度值 |
| name | char[] | tensor 名称 |
| n_elems | uint32_t | 元素个数 |
| size | uint32_t | 内存大小 |
| fmt | rknn_tensor_format | NCHW / NHWC / NC1HWC2 |
| type | rknn_tensor_type | FLOAT32/FLOAT16/INT8/UINT8/INT16/UINT16/INT32/INT64/BOOL |
| qnt_type | rknn_tensor_qnt_type | NONE / DFP / AFFINE_ASYMMETRIC |
| fl | int8_t | DFP 量化参数 |
| scale | float | AFFINE_ASYMMETRIC 量化参数 |
| w_stride | uint32_t | 行宽（含对齐填充），像素单位 |
| size_with_stride | uint32_t | 含 stride 对齐的实际内存大小 |
| pass_through | uint8_t | 0=未转换, 1=已转换(含归一化+量化) |
| h_stride | uint32_t | 多 batch 时高度 stride |

### 2.2 rknn_mem_size

| 成员 | 类型 | 说明 |
|------|------|------|
| total_weight_size | uint32_t | 权重内存 |
| total_internal_size | uint32_t | 中间 tensor 内存 |
| total_dma_allocated_size | uint64_t | 所有 DMA 内存总和 |
| total_sram_size | uint32_t | NPU 预留 SRAM（仅 RK3588） |
| free_sram_size | uint32_t | 可用空闲 SRAM（仅 RK3588） |

### 2.3 rknn_tensor_mem

| 成员 | 类型 | 说明 |
|------|------|------|
| virt_addr | void* | 虚拟地址 |
| phys_addr | uint64_t | 物理地址 |
| fd | int32_t | 文件描述符 |
| offset | int32_t | 偏移量 |
| size | uint32_t | 内存大小 |
| flags | uint32_t | ALLOC_INSIDE / FROM_FD / FROM_PHYS |

### 2.4 rknn_input

| 成员 | 类型 | 说明 |
|------|------|------|
| index | uint32_t | 输入索引 |
| buf | void* | 数据指针 |
| size | uint32_t | 数据大小 |
| pass_through | uint8_t | 1=直传, 0=自动转换 |
| type | rknn_tensor_type | 数据类型 |
| fmt | rknn_tensor_format | 数据格式 |

### 2.5 rknn_output

| 成员 | 类型 | 说明 |
|------|------|------|
| want_float | uint8_t | 是否转 float32 输出 |
| is_prealloc | uint8_t | 0=RKNN分配, 1=用户分配 |
| index | uint32_t | 输出索引 |
| buf | void* | 输出数据指针 |
| size | uint32_t | 输出数据大小 |

---

## 3. NC1HWC2 格式转换

### 3.1 C2 值表

| 平台 | int8 | float16 | int16 |
|------|------|---------|-------|
| RK356X | 8 | 4 | 4 |
| RK3588 | 16 | 8 | 8 |
| RV1106/RV1103 | 16 | 8 | 8 |

地址由低到高: C2 → W → H → C1 → N（C2 变化最快）

### 3.2 NC1HWC2 → NCHW 转换

```c
int NC1HWC2_to_NCHW(const int8_t* src, int8_t* dst,
                     int* dims, int channel, int h, int w)
{
    int batch = dims[0];
    int C1    = dims[1];
    int C2    = dims[4];
    int hw_src = dims[2] * dims[3];
    int hw_dst = h * w;
    for (int i = 0; i < batch; i++) {
        const int8_t* src_batch = src + i * C1 * hw_src * C2;
        int8_t* dst_batch = dst + i * channel * hw_dst;
        for (int c = 0; c < channel; ++c) {
            int plane = c / C2;
            const int8_t* src_c = plane * hw_src * C2 + src_batch;
            int offset = c % C2;
            for (int cur_h = 0; cur_h < h; ++cur_h)
                for (int cur_w = 0; cur_w < w; ++cur_w) {
                    int cur_hw = cur_h * w + cur_w;
                    dst_batch[c * hw_dst + cur_h * w + cur_w] =
                        src_c[C2 * cur_hw + offset];
                }
        }
    }
    return 0;
}
```

### 3.3 NC1HWC2 → NHWC 转换

```c
int NC1HWC2_to_NHWC(const int8_t* src, int8_t* dst,
                     int* dims, int channel, int h, int w)
{
    int batch = dims[0];
    int C1    = dims[1];
    int C2    = dims[4];
    int hw_src = dims[2] * dims[3];
    int hw_dst = h * w;
    for (int i = 0; i < batch; i++) {
        const int8_t* src_batch = src + i * C1 * hw_src * C2;
        int8_t* dst_batch = dst + i * channel * hw_dst;
        for (int cur_h = 0; cur_h < h; ++cur_h) {
            for (int cur_w = 0; cur_w < w; ++cur_w) {
                int cur_hw = cur_h * w + cur_w;  // 注意: 实际需用 align_stride
                for (int c = 0; c < channel; ++c) {
                    int plane = c / C2;
                    const int8_t* src_c = plane * hw_src * C2 + src_batch;
                    int offset = c % C2;
                    dst_batch[cur_h * w * channel + cur_w * channel + c] =
                        src_c[C2 * cur_hw + offset];
                }
            }
        }
    }
    return 0;
}
```

---

## 4. 输入输出配置兼容性表

### 4.1 通用 API 输入（rknn_inputs_set）

根据 RKNN_QUERY_NATIVE_INPUT_ATTR 查询到的 layout：

| 查询 Layout | 典型场景 | 数据类型 | 输入格式 |
|------------|---------|---------|---------|
| NHWC | 4维, ch=1/3/4, float32/int8/uint8 | 按 NHWC 排列 | pass_through=1 时需 w_stride 对齐 |
| NCHW | 4维, bool/int64 | 按 NCHW 排列 | - |
| NC1HWC2 | 4维, ch≠1/3/4, float16/int8 | pass_through=0→NHWC; =1→NC1HWC2 | - |
| UNDEFINED | 非4维 | 按 ONNX 原始格式 | NPU 不做 mean/std/layout 转换 |

### 4.2 通用 API 输出（rknn_outputs_get, RK356X/RK3588）

| want_float | 数据类型 | Layout |
|-----------|---------|--------|
| 1 | float32 | NCHW |
| 0 | int8（int8模型）/ float16 | NCHW |

### 4.3 零拷贝输入（RV1106/RV1103）

| 数据类型 | pass_through | channel | Layout | 备注 |
|---------|-------------|---------|--------|------|
| uint8 | 0 | - | NHWC | 仅 int8 模型 |
| int8 | 1 | 1,3,4 | NHWC | - |

### 4.4 零拷贝输出

**RK356X/RK3588**：

| 数据类型 | Layout | 备注 |
|---------|--------|------|
| float32 | NCHW | - |
| int8 | NCHW / NC1HWC2 | int8 模型 |
| float16 | NCHW / NC1HWC2 | fp16 模型 |

**RV1106/RV1103**：

| 数据类型 | Layout | 备注 |
|---------|--------|------|
| int8 | NC1HWC2 | 仅 int8 模型 |

---

## 5. RKNN 输入尺寸限制

假设输入 size = [N, H, W, C]（NHWC）：

| 场景 | 限制条件 |
|------|---------|
| 首层为 Conv (kernel_h × kernel_w) | W × kernel_h < 7168 且 kernel_h × kernel_w < 128 |
| 首层非 Conv 且 C=1/3/4 | W < 7168 |
| 其他 | 无限制 |

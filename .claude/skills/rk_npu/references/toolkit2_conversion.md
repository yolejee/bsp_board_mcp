# RKNN-Toolkit2 模型转换与精度调优

## 1. 安装

### 1.1 pip install 安装

```bash
# 创建 virtualenv
sudo apt install virtualenv
sudo apt-get install python3 python3-dev python3-pip
sudo apt-get install libxslt1-dev zlib1g zlib1g-dev libglib2.0-0 \
  libsm6 libgl1-mesa-glx libprotobuf-dev gcc
virtualenv -p /usr/bin/python3 venv
source venv/bin/activate

# 安装依赖
pip3 install -r doc/requirements*.txt

# 安装 Toolkit2
pip3 install package/rknn_toolkit2*.whl
```

### 1.2 Docker 安装

```bash
docker load --input rknn-toolkit2-1.x.x-cpxx-docker.tar.gz
docker run -t -i --privileged -v /dev/bus/usb:/dev/bus/usb \
  -v /path/to/examples:/examples rknn-toolkit2:1.x.x /bin/bash
```

---

## 2. 完整 Python API 参考

### 2.1 RKNN 对象初始化

```python
rknn = RKNN(verbose=True, verbose_file='./build.log')
# verbose=True: 打印详细日志
# verbose_file: 日志写入文件
rknn.release()  # 释放对象
```

### 2.2 config — 模型预处理配置

```python
rknn.config(
    mean_values=[[128, 128, 128]],       # 减均值（与训练一致）
    std_values=[[128, 128, 128]],         # 除归一化值
    quant_img_RGB2BGR=False,              # Caffe 模型常需 True
    quantized_dtype='asymmetric_quantized-8',  # 量化类型
    quantized_algorithm='normal',         # normal / mmse / kl_divergence
    quantized_method='channel',           # channel（精度高） / layer
    float_dtype='float16',                # 浮点类型
    optimization_level=3,                 # 0~3, 3=全开
    target_platform='rk3588',             # 必填
    custom_string='my_model_v1',          # 嵌入自定义信息
    remove_weight=False,                  # True=生成无权重从模型
    compress_weight=False,                # 压缩权重减小体积
    single_core_mode=False,               # 仅 RK3588，生成单核模型
)
```

**关键说明**：
- `quant_img_RGB2BGR` 仅影响量化阶段读取 jpg/png，不记录到 RKNN 模型
- `quantized_algorithm`:
  - `normal`: 速度快，推荐 20~100 张校正集
  - `mmse`: 暴力迭代，精度最好，20~50 张
  - `kl_divergence`: 适合 feature 分布不均匀
- `quantized_method`:
  - `channel`: 每个通道独立量化参数，精度更高
  - `layer`: 每层一套量化参数

### 2.3 模型加载

```python
# ONNX（opset 12）
rknn.load_onnx(model='./model.onnx')

# PyTorch（需 torchscript .pt 格式）
rknn.load_pytorch(model='./model.pt', input_size_list=[[1,3,224,224]])

# TensorFlow（需指定输入输出节点）
rknn.load_tensorflow(
    tf_pb='./model.pb',
    inputs=['input'],
    outputs=['output'],
    input_size_list=[[1, 224, 224, 3]])

# TFLite
rknn.load_tflite(model='./model.tflite')

# Caffe
rknn.load_caffe(model='./model.prototxt', blobs='./model.caffemodel')

# DarkNet
rknn.load_darknet(model='./model.cfg', weight='./model.weights')

# 加载已转换的 RKNN 模型（仅限连板推理/评估，不支持模拟器或精度分析）
rknn.load_rknn(path='./model.rknn')
```

### 2.4 build — 构建模型

```python
rknn.build(
    do_quantization=True,        # False=fp16 模型
    dataset='./dataset.txt',     # 每行一个图片路径，50~200 张
    rknn_batch_size=1,           # >1 可多帧同时推理（增大内存和延迟）
)
```

**dataset.txt 格式**：
```
img1.jpg
img2.jpg
# 多输入用空格隔开
img1.jpg img1_depth.npy
```

**rknn_batch_size 说明**：
- 不提高一般模型性能，但增大内存和延迟
- 适用于超小模型（CPU 开销 > NPU 开销时可提高帧率）
- 建议 < 32

### 2.5 export_rknn — 导出

```python
rknn.export_rknn('./model.rknn')
```

### 2.6 init_runtime — 初始化运行时

```python
rknn.init_runtime(
    target='rk3588',             # None=模拟器, 'rk3566'/'rk3568'/'rk3588'/'rv1103'/'rv1106'
    device_id='xxx',             # 多设备时指定（list_devices 查看）
    perf_debug=True,             # 性能评估时获取逐层耗时
    eval_mem=False,              # True=进入内存评估模式
    core_mask=RKNN.NPU_CORE_AUTO,  # RK3588 多核配置
)
```

**core_mask 选项**：
- `RKNN.NPU_CORE_AUTO` — 自动调度
- `RKNN.NPU_CORE_0` / `_1` / `_2` — 固定核
- `RKNN.NPU_CORE_0_1` — 双核
- `RKNN.NPU_CORE_0_1_2` — 三核

### 2.7 inference — 推理

```python
outputs = rknn.inference(
    inputs=[img],                # ndarray list
    data_format='nhwc',          # 'nhwc' / 'nchw'（仅4维有效）
    inputs_pass_through=None,    # [1, 0] = 透传input0, 不透传input1
)
```

### 2.8 eval_perf — 性能评估

```python
perf_result = rknn.eval_perf(inputs=[image], is_print=True)
# perf_debug=True 时返回逐层耗时
```

### 2.9 eval_memory — 内存评估

```python
# 需 init_runtime(eval_mem=True)
memory_detail = rknn.eval_memory()
# 返回 {'total_weight_allocation':..., 'total_internal_allocation':..., 'total_model_allocation':...}
```

### 2.10 accuracy_analysis — 精度分析

```python
rknn.accuracy_analysis(
    inputs=['./test.jpg'],       # 图片路径 list
    output_dir='snapshot',       # 输出目录
    target='rk3588',             # None=仅模拟器, 指定则增加板端对比
)
```

输出内容：
- `golden/` — fp32 浮点模型每层结果
- `simulator/` — 量化模型每层结果（已转 float32）
- `runtime/` — 板端每层结果（设置 target 时）
- `error_analysis.txt` — 每层余弦距离（entire_error + per_layer_error）

### 2.11 list_devices — 设备列表

```python
rknn.list_devices()
# 输出: all device(s) with adb mode: VD46C3KM6N
```

### 2.12 export_encrypted_rknn_model — 模型加密

```python
rknn.export_encrypted_rknn_model(
    input_model='test.rknn',
    output_model='test.crypt.rknn',  # 默认 {name}.crypt.rknn
    crypt_level=1,                   # 1~3, 越高越安全，解密越慢
)
```

### 2.13 get_sdk_version — SDK 版本

```python
sdk_version = rknn.get_sdk_version()
# 需先 init_runtime(target=...)
```

---

## 3. 混合量化详解

### 3.1 混合量化流程

```python
# === Step 1: 生成配置文件 ===
rknn = RKNN()
rknn.config(mean_values=[[128,128,128]], std_values=[[128,128,128]],
            target_platform='rk3588')
rknn.load_onnx(model='./model.onnx')
rknn.hybrid_quantization_step1(dataset='./dataset.txt')
# 生成: model.quantization.cfg, model.model, model.data
rknn.release()

# === Step 2: 编辑 model.quantization.cfg ===
# 找到精度下降层的输出操作数，加入 custom_quantize_layers
# custom_quantize_layers:
#   tensor_name_of_bad_layer: float16

# === Step 3: 构建混合量化模型 ===
rknn = RKNN()
rknn.hybrid_quantization_step2(
    model_input='./model.model',
    data_input='./model.data',
    model_quantization_cfg='./model.quantization.cfg')
rknn.export_rknn('./model_hybrid.rknn')
rknn.release()
```

### 3.2 配置文件格式

```yaml
custom_quantize_layers:
  layer_output_tensor_name: float16   # 指定层用 float16 计算

quantize_parameters:
  Preprocessor/sub:0:
    qtype: asymmetric_quantized
    qmethod: layer
    dtype: int8
    min: [-1.0]
    max: [1.0]
    scale: [0.00784313725490196]
    zero_point: [0]
    ori_min: [-1.0]
    ori_max: [1.0]
```

---

## 4. 精度问题排查完整流程

### 4.1 第一步：验证 fp16 模型

```
建议流程:
1. 原始框架推理（caffe/pytorch/onnxruntime）→ 保存结果 A
2. RKNN build(do_quantization=False) + init_runtime(target=None) → 推理 → 保存结果 B
3. 对比 A vs B（余弦距离）
   - 一致 → 配置正确，进入量化验证
   - 不一致 → 检查以下参数:
     * mean_values / std_values
     * cv2.imread 是 BGR，模型输入是 RGB 需转换
     * load_tensorflow 的 inputs/outputs 节点名
     * load_pytorch 的 input_size_list
     * inference 的 data_format 参数
```

### 4.2 第二步：验证量化精度

```
1. build(do_quantization=True) → 推理 → 与原始框架对比
2. 精度不足时的调优策略（按优先级）:
   a. quantized_method: layer → channel（推荐首选）
   b. quantized_algorithm: normal → mmse（耗时但精度最好）
   c. 调整 dataset: 选择与部署场景吻合的图片，50~200 张
   d. accuracy_analysis 逐层分析 → 找出精度下降层
   e. 混合量化: 将精度差的层设为 float16
   f. 最后一层精度差 → 考虑放到后处理中（CPU 计算）
```

### 4.3 第三步：板端运行时精度验证

```
1. init_runtime(target='rk3588') 连板推理 → 与模拟器结果对比
2. 差异大 → accuracy_analysis(target='rk3588') 逐层对比
   - simulator vs runtime 结果差异 → runtime bug, 报告给 RK NPU 团队
3. 连板正确但 C API 推理不对 → 检查:
   - 输入数据预处理与 Toolkit2 一致（RGB 顺序、resize 方式）
   - pass_through / want_float 配置
   - 后处理代码逻辑
```

### 4.4 精度判断标准

| 余弦距离 | 判断 |
|---------|------|
| ≥ 0.99 | 结果一致 |
| 0.98~0.99 | 轻微不一致 |
| < 0.98 | 该层结果错误 |

---

## 5. 连板调试环境配置

### 5.1 前置条件

1. 开发板通过 USB OTG 连接 PC
2. `adb devices` 能看到设备
3. 板端安装最新 rknn_server 和 librknnrt.so

### 5.2 更新板端运行库

```bash
# Android
adb root && adb remount
adb push runtime/RK3588/Android/librknn_api/arm64-v8a/librknnrt.so /vendor/lib64/
adb push runtime/RK3588/Android/rknn_server/arm64-v8a/rknn_server /vendor/bin/
adb shell "chmod +x /vendor/bin/rknn_server"
adb shell "reboot"

# Linux
adb push runtime/RK3588/Linux/librknn_api/aarch64/librknnrt.so /usr/lib/
adb push runtime/RK3588/Linux/rknn_server/aarch64/rknn_server /usr/bin/
adb shell "chmod +x /usr/bin/rknn_server"
adb shell "restart_rknn.sh &"
```

### 5.3 连板推理示例

```python
rknn = RKNN()
rknn.load_rknn('./model.rknn')
rknn.init_runtime(target='rk3588', device_id='your_device_id')

img = cv2.imread('./test.jpg')
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
img = np.expand_dims(img, 0)

outputs = rknn.inference(inputs=[img])
rknn.release()
```

---

## 6. YOLOv5 端到端部署示例

### 6.1 PC 端模型转换

```python
from rknn.api import RKNN

rknn = RKNN(verbose=True)
rknn.config(mean_values=[[0, 0, 0]], std_values=[[255, 255, 255]],
            target_platform='rk3588')
rknn.load_onnx(model='./yolov5s.onnx')
rknn.build(do_quantization=True, dataset='./dataset.txt')
rknn.export_rknn('./yolov5s.rknn')
rknn.release()
```

### 6.2 板端 C 交叉编译

```bash
# 修改 build-linux.sh 中的交叉编译器路径
# GCC_COMPILER=<path-to-gcc>/aarch64-linux-gnu

cd examples/rknn_yolov5_demo
chmod +x build-linux.sh
./build-linux.sh -t rk3588 -a aarch64 -d .

# 推送到板端运行
adb push install/rknn_yolov5_demo_Linux/ /data/
adb shell "cd /data/rknn_yolov5_demo_Linux && ./rknn_yolov5_demo model/yolov5s.rknn model/bus.jpg"
```

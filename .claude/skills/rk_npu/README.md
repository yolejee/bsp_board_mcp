# rk_npu  Rockchip NPU / RKNN SDK 推理技能

> **Version:** V3.0 | **Author:** ovcell | **License:** MIT | **Updated:** 2026-04-05

## 概述

`rk_npu` 是一个面向 Rockchip 瑞芯微 SoC 平台的 NPU 神经网络推理 AI 技能，运行于 GitHub Copilot / Claude 等支持 `.claude/skills/` 体系的 AI 编程助手中。

当用户讨论 Rockchip NPU 的模型转换（RKNN-Toolkit2）、板端 C API 推理（RKNPU2 Runtime）、零拷贝优化、多核调度、SRAM 加速、量化精度分析等问题时，AI 会自动加载本技能，提供 RKNN SDK 全流程的开发指导和性能优化策略。

## 覆盖芯片

| 芯片 | 架构 | NPU 算力 |
|------|------|---------|
| **RK3588 / RK3588S** | 4A76 + 4A55, Mali-G610 | 6 TOPS (3 核 NPU) |
| **RK3568** | 4A55, Mali-G52 | 1 TOPS (单核 NPU) |
| **RK3566** | 4A55, Mali-G52 | 1 TOPS (单核 NPU) |
| **RV1103** | 1A35 | 0.5 TOPS (轻量 NPU) |
| **RV1106** | 1A35, ISP32-lite | 0.5 TOPS (轻量 NPU) |

## 功能说明

### 功能 1：模型转换（RKNN-Toolkit2）

使用 Python API 将 ONNX/PyTorch/TFLite/Caffe 模型转换为 RKNN 格式。

**你可以这样提问：**
- "怎么把 ONNX 模型转成 RKNN？"
- "rknn.config 的 mean_values 和 std_values 怎么设？"
- "量化用 normal 还是 mmse 策略？"
- "转换报错不支持某个算子怎么办？"
- "怎么导出 int8 量化模型？"

**AI 会返回：**
- 完整的 Toolkit2 转换 Python 脚本（load → config → build → export）
- 量化参数设置指导（dataset 准备、mean/std 配置、量化策略选择）
- 不支持算子的处理方案（自定义算子、模型修改、算子替换）
- 各目标平台的 target_platform 设置

### 功能 2：板端 C API 推理（RKNPU2）

使用 C API 在开发板上部署和运行 RKNN 模型推理。

**你可以这样提问：**
- "帮我写一个 RKNN C API 推理的完整代码"
- "rknn_init 的 flag 参数各选项什么意思？"
- "输出 tensor 的 NC1HWC2 格式怎么转回 NCHW？"
- "怎么查看 NPU 利用率？"
- "推理结果和 PC 端模拟不一致怎么排查？"

**AI 会返回：**
- 完整的 RKNN C 推理代码（init → query → inputs_set → run → outputs_get → destroy）
- 输入输出数据预处理/后处理代码
- NC1HWC2 到 NCHW 的转换代码
- 调试方法（RKNN_LOG_LEVEL、逐层 dump、NPU 利用率查看）

### 功能 3：零拷贝与性能优化

零拷贝 API、多核调度、SRAM 加速等高性能推理方案。

**你可以这样提问：**
- "怎么用零拷贝 API 避免内存拷贝？"
- "RK3588 三核 NPU 怎么并行推理？"
- "SRAM 加速怎么配？能提升多少？"
- "怎么做 NPU 定频测试性能？"
- "rknn_dup_context 多线程推理怎么用？"

**AI 会返回：**
- 零拷贝 API 代码（rknn_create_mem → rknn_set_io_mem，DMA fd 共享）
- RK3588 多核调度代码（rknn_set_core_mask：CORE_0 / CORE_0_1 / CORE_0_1_2）
- SRAM 配置方法（DTS sram 节点 + 环境变量 RKNN_INTERNAL_MEM_TYPE）
- NPU 定频命令和性能测试方法

### 功能 4：量化精度分析与排查

模型量化后精度下降的分析、混合量化、逐层精度对比。

**你可以这样提问：**
- "int8 量化后检测精度下降很多怎么办？"
- "怎么做混合量化？哪些层不量化？"
- "accuracy_analysis 工具怎么用？"
- "怎么对比 fp16 和 int8 的逐层输出差异？"

**AI 会返回：**
- 精度排查三步法（fp16 验证 → 量化验证 → 板端验证）
- 混合量化流程（hybrid_quantization_step1/step2）
- accuracy_analysis 使用方法和输出解读
- 量化敏感层识别和针对性优化策略

## 触发方式

本技能在以下场景自动触发（无需手动调用）：

- 提到 **NPU / RKNN / rknn_init / rknn_run / RKNN-Toolkit2 / RKNPU2** 等关键词
- 提到 **模型转换 / ONNX 转 RKNN / 量化 / int8 / fp16** 等模型部署概念
- 提到 **零拷贝 / zero-copy / rknn_create_mem / rknn_set_io_mem** 等优化接口
- 提到 **多核 / rknn_set_core_mask / SRAM / NC1HWC2** 等 RK NPU 特有概念
- 描述 NPU 相关问题：**推理精度差 / NPU 利用率低 / 模型转换报错 / 推理速度慢**

## 文件结构

```
rk_npu/
├── SKILL.md                              # 主技能文件 (AI 自动加载, ~600 行)
├── README.md                             # 本说明文档 (供人阅读)
└── references/                           # 深入参考资料 (AI 按需加载)
    ├── rknn_api_detail.md                # C API 完整参考：所有 API 参数、数据结构、NC1HWC2 转换代码
    └── toolkit2_conversion.md            # Toolkit2 Python API、量化策略、混合量化、精度排查、部署示例
```

### 文件加载机制

- **SKILL.md**：AI 启动时自动加载，包含 NPU 核心知识（硬件参数、SDK 流程、API 概要、多核/SRAM/零拷贝概要）
- **references/**：AI 根据问题按需加载。例如：
  - 用户需要 C API 细节 → 加载 `rknn_api_detail.md`
  - 用户需要模型转换/量化 → 加载 `toolkit2_conversion.md`

## 使用示例

### 示例 1：YOLOv5 模型部署

**用户提问：**
> 帮我把 YOLOv5s ONNX 模型转成 RKNN 并在 RK3588 上推理

**AI 行为：**
1. 自动触发 `rk_npu` 技能
2. 生成 Toolkit2 Python 转换脚本（load_onnx → config → build → export_rknn）
3. 生成板端 C 推理代码（rknn_init → 前处理 → run → 后处理 NMS）
4. 建议使用三核并行和零拷贝提升性能

### 示例 2：量化精度修复

**用户提问：**
> RKNN int8 量化后目标检测 mAP 从 0.85 下降到 0.6，怎么优化？

**AI 行为：**
1. 引导使用 fp16 模式验证是否是量化引起
2. 使用 accuracy_analysis 工具逐层对比
3. 指导混合量化：对精度敏感层保持 fp16
4. 加载 `references/toolkit2_conversion.md` 提供完整混合量化流程

### 示例 3：零拷贝优化

**用户提问：**
> RK3568 NPU 推理延迟太高，输入输出数据拷贝占了大部分时间

**AI 行为：**
1. 给出零拷贝 API 代码（rknn_create_mem + rknn_set_io_mem）
2. 说明如何通过 DMA fd 与 RGA/Camera 共享 buffer
3. 对比普通模式和零拷贝模式的延迟差异
4. 加载 `references/rknn_api_detail.md` 提供完整内存管理 API

## 知识来源

- Rockchip_Developer_Guide_RKNN_API_V1.4.0_CN.pdf (54p)
- RKNN-Toolkit2_User_Guide_V1.4.0_CN.pdf (48p)
- Rockchip_Quick_Start_RKNN_SDK_V1.4.0_CN.pdf (27p)
- RK3588_NPU_SRAM_usage.md
- RKNNToolKit2_OP_Support-1.4.0.md

## License

MIT License — 自由使用、修改和分发。

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V1.0 | 2026-03-28 | 首次发布 |
| V2.0 | 2026-04-01 | 精简主 SKILL.md 至 600 行以内，新增 references/ 参考文件夹 |
| V3.0 | 2026-04-05 | 精简 description 至 800 字符以内，避免系统提示截断 |

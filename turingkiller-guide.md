# TuringKiller 生态完全指南 - 从识别到训练

## 📌 项目生态概览

**TuringKiller 生态** 是一个完整的验证码识别解决方案，包含两个核心项目：

| 项目                   | 功能         | 用途                   |
| ---------------------- | ------------ | ---------------------- |
| **TuringKiller** | OCR 识别库   | 快速集成验证码识别功能 |
| **ocr_trainer**  | 模型训练工具 | 训练自定义识别模型     |

- **开源协议**: MIT
- **主要语言**: Python
- **深度学习框架**: PyTorch + ONNX

---

## 第一部分：ocr_trainer - 模型训练工具

### 1.1 快速介绍

**ocr_trainer** 是 TuringKiller 官方提供的 OCR 模型训练工具，用于训练自定义验证码识别模型。

**GitHub**: https://github.com/ocr_trainer

### 1.2 核心特性

✅ **支持两种网络架构**:

- **CRNN**: 用于多字符 OCR 识别（默认）
- **CNN**: 用于单字符分类或图像分类

✅ **完整训练流程**:

- 数据导入与预处理
- 模型训练与断点恢复
- 自动导出 ONNX 模型
- 无缝集成 TuringKiller

✅ **灵活的数据管理**:

- 支持文件名标注方式
- 支持 labels.txt 标注方式
- 自动数据缓存与验证集划分

✅ **性能优化**:

- GPU 加速训练（NVIDIA 显卡）
- 可配置 Batch Size
- 自动模型检查点保存

### 1.3 环境要求

**硬件**:

- NVIDIA 显卡（N卡）
  - 20 系显卡 → CUDA 10.2
  - 30 系显卡 → CUDA 11.3+
- 建议 8GB+ RAM

**系统**:

- Windows / Linux
- macOS（仅 CPU 训练）

**软件**:

- Python 3.6+
- PyTorch（GPU 版本）
- CUDA Toolkit
- cuDNN

### 1.4 安装 dddd_trainer

```bash
# 1. 安装 PyTorch（根据硬件选择）
# 访问 https://pytorch.org/get-started/locally/
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu113

# 2. 安装 CUDA 和 cuDNN
# https://developer.nvidia.com/cuda-downloads
# https://developer.nvidia.com/zh-cn/cudnn

# 3. Clone 项目
git clone https://github.com/ocr_trainer.git
cd ocr_trainer

# 4. 安装依赖
pip install -r requirements.txt -i https://pypi.douban.com/simple
```

### 1.5 训练流程（6 步）

**步骤 1: 创建训练项目**

```bash
# CRNN 项目（多字符 OCR）
python app.py create my_project

# CNN 项目（单字符分类）
python app.py create my_project --single
```

**步骤 2: 准备数据**

方式 A - 文件名标注（简单场景）:

```
/data/images/
├── abcd_hash.jpg
├── 1234_hash.jpg
└── 验证码_hash.jpg
```

方式 B - labels.txt 标注（复杂场景）:

```
/data/
├── labels.txt
└── images/
    ├── img1.jpg
    └── subdir/img2.jpg
```

labels.txt 内容:

```
img1.jpg	abcd
subdir/img2.jpg	1234
```

**步骤 3: 修改配置文件**

编辑 `projects/my_project/config.yaml`:

```yaml
Model:
  ImageChannel: 1          # 1=灰度图, 3=彩图
  ImageHeight: 64          # 图片高度（16的倍数）
  ImageWidth: -1           # -1=自动调整

System:
  GPU: true                # 启用 GPU
  GPU_ID: 0                # GPU 设备号
  Val: 0.03                # 验证集比例（3%）

Train:
  BATCH_SIZE: 32           # 批次大小
  LR: 0.01                 # 学习率
  SAVE_CHECKPOINTS_STEP: 2000
  TARGET:
    Accuracy: 0.97         # 目标准确率
    Cost: 0.05             # 目标损失
    Epoch: 20              # 最小训练轮数
```

**步骤 4: 缓存数据**

```bash
# 文件名标注方式
python app.py cache my_project /data/images/

# labels.txt 标注方式
python app.py cache my_project /data/ file
```

**步骤 5: 开始训练**

```bash
# 开始新训练
python app.py train my_project

# 恢复中断的训练（自动加载检查点）
python app.py train my_project
```

**步骤 6: 部署模型**

训练完成后自动导出 ONNX 模型，可直接用于 TuringKiller:

```python
from turingkiller import TuringKiller

# 使用自定义模型
ocr = TuringKiller(model_path='/path/to/model.onnx')
result = ocr.classification(image_bytes)
```

### 1.6 配置参数详解

**Model 配置**:

| 参数             | 说明       | 默认值     |
| ---------------- | ---------- | ---------- |
| `ImageChannel` | 图片通道数 | 1          |
| `ImageHeight`  | 图片高度   | 64         |
| `ImageWidth`   | 图片宽度   | -1（自动） |

**Train 配置**:

| 参数                      | 说明           | 默认值  |
| ------------------------- | -------------- | ------- |
| `BATCH_SIZE`            | 训练批次大小   | 32      |
| `CNN`                   | 特征提取模型   | ddddocr |
| `LR`                    | 初始学习率     | 0.01    |
| `SAVE_CHECKPOINTS_STEP` | 检查点保存间隔 | 2000    |

**支持的特征提取模型**:

```
- turingkiller（默认）
- effnetv2_l / effnetv2_m / effnetv2_xl / effnetv2_s
- mobilenetv2
- mobilenetv3_s / mobilenetv3_l
```

### 1.7 dddd_trainer 常见问题

**Q: 如何处理大小写字符？**

- 在样本标注时就需要标注好大小写，项目不会自动处理

**Q: 训练速度太慢？**

- 确保启用 GPU 训练（`GPU: true`）
- 检查 CUDA 和 cuDNN 是否正确安装
- 增加 `BATCH_SIZE`（如果显存允许）
- 使用更轻量的特征提取模型（如 mobilenetv3_s）

**Q: 如何恢复中断的训练？**

- 直接运行 `python app.py train {project_name}`，系统会自动加载最新检查点

**Q: 支持 AMD 显卡吗？**

- 目前仅支持 NVIDIA 显卡（N卡）

---

## 第二部分：完整工作流

### 2.1 场景：识别准确率不满足需求

```
┌─────────────────────────────────────────────────────────┐
│ 1. 使用 TuringKiller 内置模型测试                              │
│    pip install turingkiller                                 
│    ocr = TuringKiller()                                        │
│    result = ocr.classification(image_bytes)              │
└─────────────────────────────────────────────────────────┘
                          ↓
                    准确率不满足？
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. 收集特定验证码样本（100-1000 张）                      │
│    按照 dddd_trainer 要求标注数据                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. 使用 ocr_trainer 训练自定义模型                       │
│    python app.py create my_project                       │
│    python app.py cache my_project /data/                 │
│    python app.py train my_project                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. 导出 ONNX 模型，集成到 TuringKiller                        │
│    ocr = TuringKiller(model_path='model.onnx')                │
│    result = ocr.classification(image_bytes)              │
└─────────────────────────────────────────────────────────┘
```

### 2.2 场景：快速集成验证码识别

```python
# 只需 3 行代码
from turingkiller import TuringKiller

ocr = TuringKiller()
result = ocr.classification(image_bytes)  # 返回识别结果
```

### 2.3 场景：优化特定验证码类型

```python
# 步骤 1: 收集样本并训练
# 使用 ocr_trainer 训练自定义模型

# 步骤 2: 集成自定义模型
from turingkiller import TuringKiller

ocr = TuringKiller(
    model_path='/path/to/custom_model.onnx',
    use_gpu=True,
    use_angle_cls=True
)

# 步骤 3: 使用优化后的模型
result = ocr.classification(image_bytes)
```

---

## 第三部分：性能对比与选择指南

### 3.1 TuringKiller vs 自定义模型

| 特性     | 内置模型   | 自定义模型 |
| -------- | ---------- | ---------- |
| 准确率   | 70-85%     | 90-99%+    |
| 训练时间 | 0          | 1-24 小时  |
| 样本需求 | 0          | 100-1000   |
| 部署难度 | 极简       | 简单       |
| 适用范围 | 通用验证码 | 特定类型   |

### 3.2 选择决策树

```
需要识别验证码？
    ├─ 通用验证码 → 使用 TuringKiller 内置模型
    ├─ 特定类型验证码
    │   ├─ 准确率 > 85% → 使用内置模型
    │   └─ 准确率 < 85% → 使用 ocr_trainer 训练自定义模型
    └─ 需要 99%+ 准确率 → 必须训练自定义模型
```

---

## 第四部分：技术栈与架构

### 4.1 技术栈

| 组件         | 技术                     | 用途           |
| ------------ | ------------------------ | -------------- |
| 深度学习框架 | PyTorch                  | 模型训练与推理 |
| 模型格式     | ONNX                     | 跨平台兼容     |
| 网络架构     | CRNN                     | 多字符 OCR     |
| 特征提取     | EfficientNet / MobileNet | 轻量化模型     |
| 图像处理     | OpenCV / PIL             | 预处理         |

### 4.2 数据流

```
TuringKiller 使用流程:
验证码图片 → TuringKiller → ONNX 模型 → 识别结果

ocr_trainer 训练流程:
样本数据 → 数据缓存 → PyTorch 训练 → ONNX 导出 → TuringKiller 集成
```

---

## 第五部分：最佳实践

### 5.1 TuringKiller 最佳实践

✅ **使用全局单例**:

```python
class OCRSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = TuringKiller()
        return cls._instance

ocr = OCRSingleton()
```

✅ **启用 GPU 加速**:

```python
ocr = TuringKiller(use_gpu=True)
```

✅ **多线程处理**:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(ocr.classification, images))
```

### 5.2 ocr_trainer 最佳实践

✅ **数据质量第一**:

- 确保标注准确
- 样本多样性充分
- 避免类别不平衡

✅ **合理配置参数**:

- BATCH_SIZE 根据显存调整
- 学习率从 0.01 开始
- 验证集比例 3-5%

✅ **监控训练过程**:

- 定期检查 loss 曲线
- 观察准确率变化
- 及时调整参数

---

## 第六部分：常见问题汇总

### 识别相关

**Q: 如何提高识别准确率？**

- 使用 `use_angle_cls=True` 启用角度分类
- 对验证码进行预处理
- 训练自定义模型
- 调整 `charsets` 参数

**Q: 支持哪些验证码类型？**

- 数字验证码
- 字母验证码
- 数字+字母混合
- 滑块验证码
- 图形验证码

### 训练相关

**Q: 需要多少样本才能训练？**

- 最少 100 张
- 推荐 500-1000 张
- 越多越好（>5000 张效果最佳）

**Q: 训练需要多长时间？**

- GPU 训练：1-24 小时
- CPU 训练：24-72 小时
- 取决于样本数量和硬件配置

**Q: 如何选择网络架构？**

- CRNN：多字符 OCR（推荐）
- CNN：单字符分类或图像分类

### 部署相关

**Q: 如何在生产环境部署？**

- 使用 TuringKiller + 自定义 ONNX 模型
- 支持 Docker 容器化
- 支持多线程并发处理

**Q: 模型文件大小？**

- 内置模型：~50MB
- 自定义模型：~50-100MB

---

## 总结

**TuringKiller 生态** 提供了完整的验证码识别解决方案：

1. **快速集成**: 使用 TuringKiller 库，3 行代码即可集成
2. **精准优化**: 使用 ocr_trainer 训练自定义模型
3. **无缝协作**: 训练的模型可直接集成到 TuringKiller
4. **开源友好**: MIT 协议，支持商业使用

**选择建议**:

- 通用场景 → TuringKiller 内置模型
- 特定场景 → ocr_trainer 自定义模型
- 高精度需求 → 两者结合使用

**资源链接**:

- TuringKiller: https://github.com/turingkiller
- ocr_trainer: https://github.com/ocr_trainers
- PyPI: https://pypi.org/project/turingkiller/

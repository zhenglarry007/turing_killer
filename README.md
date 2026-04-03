# TuringKiller (图灵杀手)

**TuringKiller** 是一个专注于图灵仿真测试与验证码识别的完整生态解决方案。本项目以攻促防，提供强大的 OCR (光学字符识别) 和目标检测能力，开箱即用，并支持高度定制化的模型部署。

## 📖 项目简介

本项目提供了一个基于 ONNX Runtime 和 Flask 的轻量级、高性能验证码识别服务。支持多模型并发加载、API 服务化部署，涵盖通用验证码文字识别、目标检测（用于滑块或点选验证码）等多种场景。

核心特性：

- 🚀 **开箱即用**：提供现成的 Flask API 服务，轻松集成到各种爬虫或自动化测试框架中。
- ⚡ **高性能**：基于 ONNX Runtime 推理，支持 CPU/GPU 切换，速度快，内存占用低。
- 🧩 **多模型支持**：通过 `tk_server.json` 动态配置和加载多个 ONNX 模型，按需调用。
- 🎯 **多功能聚合**：
  - **OCR 分类 (`/ocr`)**：通用验证码识别、自定义字符集识别。
  - **目标检测 (`/det`)**：定位验证码中的特定元素（如滑块、汉字点选）。

## 📂 目录结构

```text
turing_killer/
├── tk_server.py           # 核心服务入口，基于 Flask 的 API Server
├── tk_server.json         # 模型配置文件，定义加载的 ONNX 模型和字符集
├── tk_ddddocr.py          # 核心识别引擎，封装了 ONNX Runtime 的推理和图像预处理
├── turingkiller-guide.md  # 官方生态完整指南（包含训练工具说明）
├── my_model/              # 模型存放目录
│   ├── dddd_det.onnx / .json  # 目标检测默认模型及配置
│   ├── dddd_ocr.onnx / .json  # OCR识别默认模型及配置
│   ├── jrcpcx.onnx / .json    # 自定义训练模型示例
│   └── README.txt
├── demo/                  # 测试脚本和样例图片
│   ├── test_det_api.py    # 目标检测 API 调用测试脚本 (附带裁剪和画框功能)
│   ├── test_ocr_api.py    # OCR 识别 API 调用测试脚本
│   ├── pic_det/           # 目标检测测试图片
│   └── pic_ocr/           # OCR 识别测试图片
└── REDEME.md              # 本说明文档
```

## 🛠️ 安装与运行

### 1. 环境依赖

推荐使用 Python 3.7+。安装所需依赖：

```bash
pip install flask onnxruntime opencv-python Pillow numpy requests
# 如果需要 GPU 加速，请安装 onnxruntime-gpu
```

### 2. 启动 API 服务

使用 `tk_server.py` 启动服务：

```bash
cd turing_killer
python tk_server.py -p 9890
```

启动成功后，控制台会输出加载的模型信息及耗时：

```text
欢迎使用turing_killer，本项目专注图灵仿真测试，由topliu和zhi共同发起，以攻促防，带动行业升级
jrcpcx loaded | cost=0.05s
dddd_ocr loaded | cost=0.04s
dddd_det loaded | cost=0.06s
Total models loaded: 3
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:9890
```

## 🔌 API 接口文档

### 1. OCR 文字识别接口

- **接口地址**：`POST /ocr`
- **功能**：对传入的验证码图片进行字符识别。
- **请求参数** (Form-Data):
  - `image`: 图片文件。
  - `model`: 使用的模型名称 (必须在 `tk_server.json` 中配置，如 `dddd_ocr`, `jrcpcx`)。
- **返回结果** (JSON):
  ```json
  {
    "status": 200,
    "result": "abcd",
    "msg": ""
  }
  ```

### 2. 目标检测接口

- **接口地址**：`POST /det`
- **功能**：检测图片中的目标（如点选验证码的文字坐标）。
- **请求参数** (Form-Data):
  - `image`: 图片文件。
  - `model`: 使用的模型名称 (如 `dddd_det`)。
- **返回结果** (JSON): 返回检测框的坐标数组 `[x_min, y_min, x_max, y_max]`。
  ```json
  {
    "status": 200,
    "result": [
      [10, 20, 50, 60],
      [70, 20, 110, 60]
    ],
    "msg": ""
  }
  ```

## 💻 客户端测试示例 (Demo)

在 `demo` 目录下提供了两个完整的测试脚本，展示了如何调用服务端的 API 接口。

### 1. 测试 OCR 识别

运行 `demo/test_ocr_api.py`，它会遍历 `pic_ocr` 目录下的图片并调用服务进行文字识别：

```bash
cd demo
python test_ocr_api.py
```

### 2. 测试目标检测

运行 `demo/test_det_api.py`，它不仅调用检测 API，还会使用 OpenCV 对原图进行目标裁剪、画框标记（红色边框）并保存：

```bash
cd demo
python test_det_api.py
```

检测结果及可视化标记图片会保存在 `demo/output` 目录下。

## ⚙️ 模型配置与自定义模型

通过修改 `tk_server.json` 可以自由增加或更改模型映射，服务在启动时会自动加载这些模型：

```json
{
    "jrcpcx": {
        "onnx_path": "./my_model/jrcpcx.onnx",
        "charsets_path": "./my_model/jrcpcx.json"
    },
    "dddd_ocr": {
        "onnx_path": "./my_model/dddd_ocr.onnx",
        "charsets_path": "./my_model/dddd_ocr.json"
    },
    "dddd_det": {
        "onnx_path": "./my_model/dddd_det.onnx",
        "charsets_path": "./my_model/dddd_det.json"
    }
}
```

**如何获取自定义模型？**
结合官方生态工具 **ocr_trainer**（详见 [`turingkiller-guide.md`](./turingkiller-guide.md)），你可以轻松训练针对特定复杂验证码的识别模型，并将其导出为 `.onnx` 格式，配合生成的 `.json` 字符集配置文件放入 `my_model` 目录中即可无缝集成。

## 📜 鸣谢

- 本项目由 topliu 和 zhilong 共同发起，专注于图灵仿真测试。
- 以攻促防，带动行业升级。

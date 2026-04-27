#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云 DashScope Qwen-VL API 示例
支持图像识别、OCR、物体定位等多模态能力

接入方式：
1. 获取 API Key: https://help.aliyun.com/zh/model-studio/get-api-key
2. 设置环境变量: export DASHSCOPE_API_KEY="sk-xxx"
3. 或直接在代码中替换 api_key 参数

支持的模型：
- qwen3.6-plus      最新最强，推荐使用
- qwen3.6-flash     速度更快，成本更低
- qwen3-vl-plus     Qwen3-VL 系列，支持3D定位
- qwen-vl-max       Qwen2.5-VL 系列
"""

import os
import base64
from PIL import Image
import io

# ========================================
# 方式1: 使用 OpenAI 兼容方式（推荐）
# ========================================
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("提示: 安装 openai 库以使用 OpenAI 兼容方式: pip install openai")

# ========================================
# 方式2: 使用 DashScope 原生 SDK
# ========================================
try:
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    print("提示: 安装 dashscope 库以使用原生方式: pip install dashscope>=1.24.6")


def encode_image_to_base64(image_path):
    """将本地图片转换为 base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def image_to_data_url(image_path):
    """将本地图片转换为 data URL"""
    base64_data = encode_image_to_base64(image_path)
    # 根据图片类型选择 MIME 类型
    if image_path.lower().endswith('.png'):
        mime_type = 'image/png'
    elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
        mime_type = 'image/jpeg'
    else:
        mime_type = 'image/png'
    return f"data:{mime_type};base64,{base64_data}"


class QwenVLClient:
    """Qwen-VL API 客户端封装"""
    
    def __init__(self, api_key=None, model="qwen3.6-plus", region="beijing"):
        """
        初始化客户端
        
        参数:
            api_key: DashScope API Key，不传则从环境变量 DASHSCOPE_API_KEY 读取
            model: 模型名称，默认 qwen3.6-plus
            region: 地区，可选 beijing, singapore, virginia
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model
        
        # 各地区 API 地址
        region_urls = {
            "beijing": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "singapore": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "virginia": "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        }
        self.base_url = region_urls.get(region, region_urls["beijing"])
        
        if not self.api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或传入 api_key 参数")
        
        # 初始化 OpenAI 兼容客户端
        if OPENAI_AVAILABLE:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
    
    def recognize_image(self, image_source, prompt="请描述这张图片中的内容"):
        """
        识别图片内容（通用场景）
        
        参数:
            image_source: 图片路径或 URL 或 base64 data URL
            prompt: 询问的问题
        
        返回:
            模型回复内容
        """
        # 处理图片来源
        if image_source.startswith(('http://', 'https://')):
            # 网络图片
            image_url = image_source
        elif image_source.startswith('data:'):
            # 已经是 data URL
            image_url = image_source
        else:
            # 本地文件，转换为 data URL
            if not os.path.exists(image_source):
                raise FileNotFoundError(f"图片文件不存在: {image_source}")
            image_url = image_to_data_url(image_source)
        
        if OPENAI_AVAILABLE:
            return self._call_openai_compatible(image_url, prompt)
        else:
            return self._call_native_dashscope(image_url, prompt)
    
    def _call_openai_compatible(self, image_url, prompt):
        """使用 OpenAI 兼容方式调用"""
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
        )
        return completion.choices[0].message.content
    
    def _call_native_dashscope(self, image_url, prompt):
        """使用 DashScope 原生 SDK 调用"""
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("请安装 dashscope: pip install dashscope")
        
        # 设置 API 地址
        if "intl" in self.base_url:
            dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        elif "us" in self.base_url:
            dashscope.base_http_api_url = "https://dashscope-us.aliyuncs.com/api/v1"
        else:
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image_url},
                    {"text": prompt}
                ]
            }
        ]
        
        response = dashscope.MultiModalConversation.call(
            api_key=self.api_key,
            model=self.model,
            messages=messages
        )
        
        return response.output.choices[0].message.content[0]["text"]
    
    # ========================================
    # 验证码识别专用方法
    # ========================================
    
    def recognize_captcha_text(self, image_path):
        """
        识别验证码中的文字（OCR 场景）
        
        参数:
            image_path: 验证码图片路径
        
        返回:
            识别到的文字
        """
        prompt = "识别图中的所有汉字，按从左到右、从上到下顺序输出。不要任何解释，只返回文字。"
        return self.recognize_image(image_path, prompt)
    
    def detect_and_localize(self, image_path, target_texts):
        """
        检测图片中指定文字的位置（物体定位场景）
        
        参数:
            image_path: 图片路径
            target_texts: 要定位的文字列表，如 ["村", "总", "令"]
        
        返回:
            定位结果，包含各文字的坐标
        """
        targets_str = "、".join(target_texts)
        prompt = f"请定位图中以下文字的位置：{targets_str}。" \
                 f"以 JSON 格式输出，格式为：{{\"文字\": {{\"bbox\": [x1, y1, x2, y2], \"center\": [x, y]}}}}。" \
                 f"只返回 JSON，不要其他解释。"
        
        result = self.recognize_image(image_path, prompt)
        return result
    
    def extract_coordinates(self, image_path, title_chars):
        """
        酒仙网验证码专用：提取标题汉字在大图中的坐标
        
        参数:
            image_path: 大图验证码路径
            title_chars: 标题汉字列表，如 ["村", "总", "令"]
        
        返回:
            {"center": {"村": "x,y", ...}, "bbox": {"村": [x1,y1,x2,y2], ...}}
        """
        chars_str = "、".join(title_chars)
        prompt = f"这是一张验证码图片，请找出以下汉字在图中的位置：{chars_str}。" \
                 f"按以下 JSON 格式输出坐标：" \
                 f"{{\"center\": {{\"汉字\": \"x,y\", ...}}, \"bbox\": {{\"汉字\": [x1, y1, x2, y2], ...}}}}。" \
                 f"只返回 JSON，不要任何其他文字。"
        
        result = self.recognize_image(image_path, prompt)
        
        # 尝试解析 JSON
        import json
        try:
            # 清理可能的 markdown 格式
            result_clean = result.strip()
            if result_clean.startswith('```json'):
                result_clean = result_clean[7:]
            if result_clean.startswith('```'):
                result_clean = result_clean[3:]
            if result_clean.endswith('```'):
                result_clean = result_clean[:-3]
            
            return json.loads(result_clean.strip())
        except json.JSONDecodeError:
            print(f"无法解析 JSON，原始返回: {result}")
            return None


# ========================================
# 使用示例
# ========================================

if __name__ == "__main__":
    # 检查 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("=" * 60)
        print("请先设置 DASHSCOPE_API_KEY 环境变量:")
        print("  export DASHSCOPE_API_KEY=\"sk-你的API密钥\"")
        print("")
        print("获取 API Key: https://help.aliyun.com/zh/model-studio/get-api-key")
        print("=" * 60)
        exit(1)
    
    print(f"使用模型: qwen3.6-plus")
    print(f"API Key: {api_key[:10]}...{api_key[-5:]}")
    print("")
    
    # 创建客户端
    client = QwenVLClient(model="qwen3.6-plus")
    
    # 示例图片路径
    test_image = "/Users/larryzheng/Downloads/code/turing_killer/demo/pic/0001.png"
    
    if os.path.exists(test_image):
        print("=" * 60)
        print(f"测试图片: {test_image}")
        print("=" * 60)
        
        # 1. 通用识别
        print("\n【1】通用识别 - 描述图片内容")
        result = client.recognize_image(test_image, "请描述这张图片的内容")
        print(result)
        
        # 2. OCR 识别
        print("\n【2】OCR 识别 - 识别所有文字")
        ocr_result = client.recognize_captcha_text(test_image)
        print(f"识别结果: {ocr_result}")
        
        # 3. 如果是验证码，可以尝试定位
        print("\n【3】物体定位 - 定位指定文字")
        print("(需要知道目标文字才能演示)")
    else:
        print(f"测试图片不存在: {test_image}")
        print("\n使用网络图片示例:")
        
        # 使用文档中的示例图片
        sample_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
        
        result = client.recognize_image(sample_url, "图中描绘的是什么景象?")
        print(f"\n网络图片识别结果:")
        print(result)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

# encoding=utf-8
import torch
import time
from io import BytesIO
from PIL import Image
# 1. 使用最新的类名
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig
import argparse
import base64
import json

from flask import Flask, request

parser = argparse.ArgumentParser(description="使用turing_server 搭建的最简api服务")
parser.add_argument("-p", "--port", type=int, default=9895)
parser.add_argument("--qwen-config", type=str, default='int8')
args = parser.parse_args()

app = Flask(__name__)

class Server():
    def __init__(self):
        
        print("欢迎使用turing_killer系列，本项目专注图灵仿真测试，由topliu和zhi共同发起，以攻促防，带动行业升级")   
        MODEL_ID = "Qwen/Qwen3-VL-8B-Instruct"
        print("正在加载 processor...["+MODEL_ID+"]")
        self.processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)

        qwen_config = args.qwen_config
        print("正在配置 "+qwen_config+" 量化...")
        # 2. 使用 BitsAndBytesConfig 对象来配置量化
        if qwen_config == 'int4':
            # 2. 配置量化 (INT4 速度最快)
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
        elif qwen_config == 'int8':
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True
            )
        print("正在加载模型...")
        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID,
            device_map="auto",
            trust_remote_code=True,
            quantization_config=quantization_config # 3. 将配置对象传入
        ).eval()

       
  
server = Server()

def get_img(request, img_type='file', img_name='image'):
    try:
        if img_type == 'b64':
            img_data = request.get_data()
            if not img_data:
                return None
                
            # 尝试解析JSON
            try:
                data = json.loads(img_data)
                if isinstance(data, dict) and img_name in data:
                    img_data = data[img_name].encode()
            except:
                pass
                
            return base64.b64decode(img_data)
        else:
            if img_name not in request.files:
                return None
                
            file = request.files[img_name]
            if not file or file.filename == '':
                return None
                
            return file.read()
            
    except Exception:
        return None

def set_ret(result, ret_type='text'):
    if ret_type == 'json':
        if isinstance(result, Exception):
            return json.dumps({"status": 200, "result": "", "msg": str(result)})
        else:
            return json.dumps({"status": 200, "result": result, "msg": ""})
    else:
        if isinstance(result, Exception):
            return ''
        else:
            return str(result).strip()

@app.route('/<opt>', methods=['POST'])
def ocr(opt):
    try:
        data = request.get_json(silent=True) or request.form or request.args        
                     
        img = get_img(request)
        if img is None:
           return {"status": "error", "message": "No image provided"}, 400

        if isinstance(img, bytes):
            image = Image.open(BytesIO(img))

        processor = server.processor;  
        model = server.model;
        if opt == 'ocr':                
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": "识别图中所有文字，按从左到右、从上到下顺序输出。不要任何解释，只返回文字。"}
                    ]
                }
            ]

            text_input = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
            inputs = processor(text=text_input, images=[image], return_tensors="pt", padding=True).to(model.device)

            print("开始推理...")
            # 1. --- 开始计时 ---
            start_time = time.time()

            with torch.no_grad():
                generated_ids = model.generate(**inputs, max_new_tokens=256, do_sample=False)

            # 2. --- 结束计时 ---
            end_time = time.time()

            # 3. 计算耗时
            inference_duration = end_time - start_time

            response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            response = response.split("assistant\n")[1].strip()  

            # 4. 计算生成速度 (可选：统计生成的 token 数量)
            # 注意：这需要减去输入的 token 长度
            input_len = inputs.input_ids.shape[1]
            output_len = generated_ids.shape[1] - input_len
            tokens_per_second = output_len / inference_duration if inference_duration > 0 else 0
            # print cost
            print(f"推理总耗时: {inference_duration:.2f} 秒 | 生成速度: {tokens_per_second:.2f} tokens/秒 | 生成Token数: {output_len}")            
            return set_ret(response, 'json')  
             
        else:
            return {"status": "error", "message": "not support opt="+str(opt)}, 500
            
    except Exception as e:
        print(f'Error in: {str(e)}')
        return {"status": "error", "message": str(e)}, 500

@app.route('/ping', methods=['GET'])
def ping():
    return "pong"


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=args.port)

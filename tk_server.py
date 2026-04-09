# encoding=utf-8
import argparse
import base64
import json
import time

from tk_ddddocr import TuringKillerOcr
from flask import Flask, request

parser = argparse.ArgumentParser(description="使用turing_server 搭建的最简api服务")
parser.add_argument("-p", "--port", type=int, default=9890)
parser.add_argument("--model-config", type=str, default='tk_server.json')
args = parser.parse_args()

app = Flask(__name__)

class Server():
    def __init__(self):
        with open(args.model_config, 'r', encoding='utf-8') as f:
            model_configs = json.load(f)
        self.models = {}
        # 加载模型
        for model_name, config in model_configs.items():     
            onnx_path = config['onnx_path']
            charsets_path = config['charsets_path']
            start_time = time.time()           
            ocr = TuringKillerOcr(import_onnx_path=onnx_path,charsets_path=charsets_path)
            if model_name == 'dddd_ocr':
                ocr.use_import_onnx = False;
            # 存储模型信息
            self.models[model_name] = ocr                        
            cost_time = round(time.time() - start_time, 2)
            print(f"{model_name} loaded | cost={cost_time}s")
        # 添加打印模型个数
        print(f"Total models loaded: {len(self.models)}")
       
  
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
        # return json.dumps({"succ": isinstance(result, str), "result": str(result)})
    else:
        if isinstance(result, Exception):
            return ''
        else:
            return str(result).strip()

@app.route('/<opt>', methods=['POST'])
def ocr(opt):
    try:
        data = request.get_json(silent=True) or request.form or request.args
        model_name = data.get('model')
            
        if not model_name:
            return {"status": "error", "message": "Model parameter is required"}, 400
        ocr = server.models[model_name];               
        img = get_img(request)
        if img is None:
           return {"status": "error", "message": "No image provided"}, 400

        if opt == 'ocr':     
            result = ocr.classification(img)    
            return set_ret(result, 'json')

        elif opt == 'det':           
            result = ocr.detection(img)  
            return set_ret(result, "json")         
            
    except Exception as e:
        print(f'Error in model_name={model_name}: {str(e)}')
        return {"status": "error", "message": str(e)}, 500

@app.route('/ping', methods=['GET'])
def ping():
    return "pong"


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=args.port)

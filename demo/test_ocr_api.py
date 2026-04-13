# -*- coding: utf-8 -*-
import os
import requests
from config import Config

class MyOcr(object):
    def __init__(self, api_url=None):
        """
        初始化OCR处理器
        参数:
            api_url: 远程OCR服务的API地址
        """
        self.api_url = api_url
        self.supported_formats = Config.SUPPORTED_FORMATS

    def process_directory(self, input_path, output_path):
        """
        主处理方法：遍历处理输入目录中的所有图片文件
        参数:
            input_path: 输入图片所在目录路径
            output_path: 处理结果输出目录路径
        """
        if not self.api_url:
            print("API地址未设置")
            return
            
        if not os.path.exists(input_path):
            print(f"输入目录不存在: {input_path}")
            return
            
        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)
            
        for filename in os.listdir(input_path):
            file_path = os.path.join(input_path, filename)
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                continue
            
            # 检查文件扩展名是否在支持的格式中
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in self.supported_formats:
                continue
            
            try:
                # 读取图片文件
                with open(file_path, 'rb') as f:
                    files = {'image': f}
                    # 将model参数放在data中
                    data = {'model': 'dddd_ocr'}  # 关键修正！
                    resp = requests.post(self.api_url, files=files, data=data)
                
                if resp.status_code != 200:
                    print(f"API请求失败，状态码：{resp.status_code}")
                    print(f"响应内容：{resp.text}")
                    continue
                
                # 解析响应
                result = resp.json()
                
                # 根据服务端返回格式，提取result字段
                if isinstance(result, dict):
                    if 'result' in result:
                        ocr_text = result['result']
                    else:
                        ocr_text = result
                else:
                    ocr_text = result
                    
                print(f"文件: {filename} -> 识别结果: {ocr_text}")
                
                # 将识别结果保存到输出目录
                file_base = os.path.splitext(filename)[0]
                output_file_path = os.path.join(output_path, f"{file_base}.txt")
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(str(ocr_text))
                
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")

# 主程序入口
if __name__ == '__main__':
    # 配置参数（根据实际情况修改）
    input_dir = Config.get_input_dir("ocr")   # 输入图片目录
    output_dir = Config.get_output_dir("ocr") # 输出结果目录
    api_url = Config.OCR_API_URL  # OCR API地址
    
    # 创建OCR处理器实例（传入API地址）
    my_ocr = MyOcr(api_url=api_url)
    
    # 检查输入目录是否有文件
    my_ocr.process_directory(input_dir, output_dir)

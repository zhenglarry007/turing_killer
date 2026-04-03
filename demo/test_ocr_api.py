import os
import requests

# 配置
api_url = "http://localhost:9890/ocr"  # 不要在这里加model参数
current_dir = os.path.dirname(os.path.abspath(__file__))
directory_path = "pic_ocr"  # 请替换为实际的目录路径
supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}  # 支持的图片格式

# 遍历目录中的所有文件
for filename in os.listdir(directory_path):
    file_path = os.path.join(directory_path, filename)
    
    # 检查是否是文件
    if not os.path.isfile(file_path):
        continue  # 不是文件，跳过
    
    # 检查文件扩展名是否在支持的格式中
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in supported_formats:
        continue  # 不支持的文件格式，跳过
    
    try:
        # 读取图片文件
        with open(file_path, 'rb') as f:
            files = {'image': f}
            # 将model参数放在data中
            data = {'model': 'dddd_ocr'}  # 关键修正！
            resp = requests.post(api_url, files=files, data=data)
        
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
        
    except Exception as e:
        print(f"处理文件 {filename} 时出错: {e}")
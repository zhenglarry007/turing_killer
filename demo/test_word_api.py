# 导入必要的库
# -*- coding: utf-8 -*-
import os       # 用于文件和目录操作
import requests # 用于HTTP请求（远程API调用）
import time     # 用于计算耗时
import numpy as np  # 添加numpy用于图像合并
import cv2      # OpenCV库，用于图像处理
import json     # 用于处理JSON数据
import re       # 用于正则表达式判断汉字
from PIL import Image, ImageDraw, ImageFont  # 添加PIL库用于中文显示
from config import Config

class MyOcr(object):
    def __init__(self, api_url=None, ocr_api_url=None, ext_rate=0.05):
        """
        初始化OCR处理器
        参数:
            api_url: 目标检测API地址
            ocr_api_url: OCR文字识别API地址
            ext_rate: 扩展截取面积的比例，默认为0.05（5%）
        """
        self.api_url = api_url or ''
        self.ocr_api_url = ocr_api_url
        self.ext_rate = ext_rate  # 扩展比例
    
    def is_chinese_char(self, text):
        """
        判断文本是否为汉字（不包含标点符号、字母、数字）
        参数:
            text: 待判断的文本
        返回:
            True表示是汉字，False表示不是
        """
        if not text or len(text.strip()) == 0:
            return False
        
        # 使用正则表达式匹配汉字（Unicode范围：\u4e00-\u9fff）
        chinese_pattern = re.compile(r'^[\u4e00-\u9fff]+$')
        return bool(chinese_pattern.match(text.strip()))
    
    def enlarge_bbox(self, bbox, img_width, img_height, ext_rate):
        """
        扩展检测框区域
        参数:
            bbox: 原始检测框 [x1, y1, x2, y2]
            img_width: 原图宽度
            img_height: 原图高度
            ext_rate: 扩展比例
        返回:
            扩展后的检测框 [x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = bbox
        
        if ext_rate > 0:
            # 计算扩展的像素值
            deltaX = int(img_width * ext_rate + 0.5)  # 四舍五入
            deltaY = int(img_height * ext_rate + 0.5)  # 四舍五入
            
            # 扩展坐标并确保不超出图像边界
            enlarged_x1 = max(0, x1 - deltaX)
            enlarged_y1 = max(0, y1 - deltaY)
            enlarged_x2 = min(img_width, x2 + deltaX)
            enlarged_y2 = min(img_height, y2 + deltaY)
            
            print(f"  原始框: [{x1},{y1},{x2},{y2}], 扩展后: [{enlarged_x1},{enlarged_y1},{enlarged_x2},{enlarged_y2}], deltaX={deltaX}, deltaY={deltaY}")
            
            return [enlarged_x1, enlarged_y1, enlarged_x2, enlarged_y2]
        else:
            return bbox
    
    def detect_objects(self, filename, img_bytes):
        """
        对象检测方法（远程模式）
        参数:
            filename: 文件名
            img_bytes: 图片的二进制数据
        返回:
            检测框坐标列表，每个框格式为[x1,y1,x2,y2]
        """
        # 远程API模式
        if not self.api_url:
            print("API地址未设置")
            return []
            
        try:
            # 发送POST请求到API服务
            files = {'image': (filename, img_bytes, 'image/jpeg')}
            # 将model参数放在data中
            data = {'model': 'dddd_det'}  # 关键修正！
            resp = requests.post(
                self.api_url,
                files=files,
                data=data,
                timeout=10
            )
            resp.raise_for_status()  # 检查HTTP错误
            return resp.json().get('result')  # 假设API返回JSON格式的检测结果
        except Exception as e:
            print(f"调用检测API服务出错: {str(e)}")
            return []
    
    def recognize_text(self, img_bytes):
        """
        OCR文字识别方法
        参数:
            img_bytes: 图片的二进制数据
        返回:
            识别出的文字字符串，失败返回空字符串
        """
        if not self.ocr_api_url:
            print("未配置OCR API地址")
            return ""
        
        try:
            # 调用OCR API
            files = {'image': img_bytes}
            data = {'model': 'dddd_ocr'}  # 关键修正！
            resp = requests.post(self.ocr_api_url, files=files, data=data)
            
            if resp.status_code != 200:
                print(f"OCR API请求失败，状态码：{resp.status_code}")
                print(f"响应内容：{resp.text}")
                return ""
            
            # 解析响应
            result_json = resp.json()
            
            # 提取result字段作为识别文字
            if isinstance(result_json, dict) and 'result' in result_json:
                recognized_text = result_json.get('result', '')
                if recognized_text:
                    return recognized_text
                else:
                    print(f"OCR识别结果为空")
                    return ""
            else:
                print(f"OCR返回格式异常: {result_json}")
                return ""
                
        except Exception as e:
            print(f"调用OCR API服务出错: {str(e)}")
            return ""
    
    def get_text_position(self, bbox, img_height, text_height=30):
        """
        计算文字标签的位置，避免与检测框重叠
        参数:
            bbox: 检测框坐标 [x1, y1, x2, y2]
            img_height: 图片高度
            text_height: 文字标签的大致高度（像素）
        返回:
            文字标签的位置 (x, y)
        """
        x1, y1, x2, y2 = bbox
        
        # 默认尝试放在框的上方
        text_x = x1
        text_y = y1 - text_height  # 在框上方
        
        # 判断上方是否有足够空间
        if text_y < 0:
            # 上方空间不足，放在框的下方
            text_y = y2 + 2  # 框的底部，留2像素间距
            print(f"  框上方空间不足，文字标签放在下方: y={text_y}")
        else:
            print(f"  文字标签放在上方: y={text_y}")
        
        return (text_x, text_y)
    
    def draw_chinese_text_on_image(self, img, text, position, font_size=20, color=(0, 255, 0)):
        """
        在图片上绘制中文文字（严格参考vis函数）
        参数:
            img: OpenCV格式的图片（BGR）
            text: 要绘制的文字
            position: 文字位置 (x, y)
            font_size: 字体大小
            color: 文字颜色 (B, G, R)
        返回:
            绘制后的图片（OpenCV格式）
        """
        # 将OpenCV图片转换为PIL图片（BGR -> RGB）
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        try:
            # 尝试加载中文字体（Windows系统用"simsun.ttc"）
            font = ImageFont.truetype("simsun.ttc", font_size, encoding="utf-8")
        except:
            # 回退到默认字体（不支持中文）
            font = ImageFont.load_default()
            print("警告: 未找到中文字体(simsun.ttc)，将使用默认字体（可能不支持中文）")
        
        # 计算文本尺寸
        try:
            if hasattr(draw, 'textbbox'):
                bbox = draw.textbbox((0, 0), text, font=font)
                txt_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
            else:
                # 兼容旧版本 PIL
                txt_size = draw.textsize(text, font=font) # type: ignore
        except Exception:
            txt_size = (20 * len(text), 20) # fallback
        
        x, y = position
        
        # 绘制文本背景（半透明效果）
        txt_bk_color = (0, 0, 0)  # 黑色背景
        draw.rectangle(
            [x, y, x + txt_size[0] + 4, y + txt_size[1] + 4],
            fill=txt_bk_color
        )
        
        # 绘制文本（使用绿色）
        txt_color = (color[2], color[1], color[0])  # 转换为RGB顺序
        draw.text((x + 2, y + 2), text, fill=txt_color, font=font)
        
        # 转换回OpenCV格式（RGB -> BGR）
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    def process_directory(self, input_path, output_path):
        """
        主处理方法：遍历处理输入目录中的所有图片文件
        参数:
            input_path: 输入图片所在目录路径
            output_path: 输出结果目录路径（out_word）
        功能流程:
            1. 自动创建输出目录(如果不存在)
            2. 遍历输入目录中的图片文件
            3. 对每个图片：
               a. 截取所有检测到的目标区域
               b. 扩展检测框区域（ext_rate比例）
               c. 对扩展后的区域进行OCR识别
               d. 只保留识别结果为汉字的区域
               e. 在原图上标注保留的目标区域（使用原始框）并保存
               f. 保存OCR识别结果为JSON文件（使用扩展框？使用原始框？）
        """
        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)
        
        # 遍历输入目录中的所有文件
        for filename in os.listdir(input_path):
            # 检查文件是否是支持的图片格式
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                # 提取文件名(不含扩展名)和扩展名
                file_base, file_ext = os.path.splitext(filename)
                # 构建完整文件路径
                file_path = os.path.join(input_path, filename)
                
                try:
                    # 步骤1: 读取图片二进制数据用于目标检测
                    with open(file_path, 'rb') as f:
                        img_bytes = f.read()
                    
                    # 步骤2: 调用检测方法（远程模式）
                    poses = self.detect_objects(filename, img_bytes)
                    print(f"文件 {filename} 检测到 {len(poses)} 个目标区域")
                    
                    # 如果没有检测到任何目标，跳过后续处理
                    if not poses:
                        print(f"警告: 文件 {filename} 未检测到任何目标")
                        continue

                    print("原始检测框坐标="+str(poses))
                    
                    # 步骤3: 使用OpenCV读取图片用于裁剪和标注                    
                    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    if img is None:
                        print(f"警告: 无法解码图片 {filename}")
                        continue
                        
                    # 获取图片尺寸
                    img_height, img_width = img.shape[:2]
                    print(f"图片尺寸: {img_width}x{img_height}")
                    
                    # 复制原图用于绘制检测框（只画框，不画文字）
                    marked_img = img.copy()
                    
                    # 存储所有OCR识别结果，格式: {"识别文字": 原始框坐标}
                    all_ocr_results = {}
                    # 存储需要保留的区域（识别结果为汉字的区域）
                    valid_regions = []
                    
                    # 步骤4: 处理所有目标区域的截取、扩展和OCR识别
                    for i, box in enumerate(poses):
                        # 处理坐标（按原比例和固定边距提取）
                        # 检测结果格式为 [xmin, ymin, xmax, ymax]
                        # 增加固定的2像素边距（不使用比例扩展，避免框过大）
                        padding = 2
                        x1 = max(0, int(box[0]) - padding)
                        y1 = max(0, int(box[1]) - padding)
                        x2 = min(img_width, int(box[2]) + padding)
                        y2 = min(img_height, int(box[3]) + padding)
                        box = [x1, y1, x2, y2]

                        # 计算区域宽度和高度
                        width = x2 - x1
                        height = y2 - y1
                        
                        # 计算宽高比和高度比
                        ratio_w_h = width / height if height != 0 else float('inf')
                        ratio_h_w = height / width if width != 0 else float('inf')
                        
                        # 如果宽高比或高宽比大于2倍，则跳过该区域
                        if ratio_w_h > 2 or ratio_h_w > 2:
                            print(f"跳过区域 {i}: 宽高比异常 (宽:{width}, 高:{height}, 宽高比:{ratio_w_h:.2f})")
                            continue
                        
                        # 4.1 扩展检测框区域
                        enlarged_box = self.enlarge_bbox(box, img_width, img_height, self.ext_rate)
                        
                        # 4.2 使用扩展后的区域进行裁剪
                        enlarged_x1, enlarged_y1, enlarged_x2, enlarged_y2 = enlarged_box
                        cropped_img = img[enlarged_y1:enlarged_y2, enlarged_x1:enlarged_x2]
                        
                        # 4.3 OCR识别裁剪区域的文字
                        recognized_text = ""
                        if self.ocr_api_url:
                            # 将裁剪图像编码为JPEG格式的字节数据
                            success, encoded_cropped = cv2.imencode('.jpg', cropped_img)
                            if success:
                                cropped_bytes = encoded_cropped.tobytes()
                                recognized_text = self.recognize_text(cropped_bytes)
                                if recognized_text:
                                    # 判断识别结果是否为汉字
                                    if self.is_chinese_char(recognized_text):
                                        print(f"区域 {i} OCR识别结果为汉字: '{recognized_text}'")
                                        print(f"  原始框: {box}")
                                        print(f"  扩展框: {enlarged_box}")
                                        # 保存识别结果和原始框坐标
                                        all_ocr_results[recognized_text] = box
                                        valid_regions.append({
                                            'box': box,  # 使用原始框进行标注
                                            'text': recognized_text
                                        })
                                    else:
                                        print(f"区域 {i} OCR识别结果不是汉字: '{recognized_text}'，跳过该区域")
                                else:
                                    print(f"区域 {i} OCR识别失败或无文字，跳过该区域")
                            else:
                                print(f"区域 {i} 图像编码失败，无法进行OCR识别")
                        else:
                            print(f"区域 {i} 未配置OCR API，跳过该区域")
                    
                    # 步骤5: 只对保留的区域（汉字区域）进行标注（使用原始框）
                    print(f"文件 {filename} 共保留 {len(valid_regions)} 个汉字区域")
                    
                    for region in valid_regions:
                        x1, y1, x2, y2 = region['box']
                        recognized_text = region['text']
                        
                        # 5.1 在副本图上绘制矩形标记(红色边框，线宽2像素)
                        marked_img = cv2.rectangle(
                            marked_img, 
                            (x1, y1), (x2, y2), 
                            color=(0, 0, 255),  # BGR格式的红色
                            thickness=2
                        )
                        
                        # 5.2 计算文字标签位置（自动避免重叠）
                        text_position = self.get_text_position(region['box'], img_height, text_height=25)
                        
                        # 5.3 使用PIL绘制中文文字
                        marked_img = self.draw_chinese_text_on_image(
                            marked_img, 
                            recognized_text, 
                            text_position, 
                            font_size=18,  # 字体大小
                            color=(0, 255, 0)  # 绿色文字
                        )
                    
                    # 步骤6: 保存标注后的原图
                    marked_path = os.path.join(
                        output_path,
                        f"{file_base}_marked{file_ext}"
                    )
                    
                    # 使用imencode保存标记后的图片（处理中文路径）
                    if file_ext.lower() in ['.jpg', '.jpeg']:
                        success, encoded_img = cv2.imencode('.jpg', marked_img)
                    elif file_ext.lower() == '.png':
                        success, encoded_img = cv2.imencode('.png', marked_img)
                    elif file_ext.lower() == '.bmp':
                        success, encoded_img = cv2.imencode('.bmp', marked_img)
                    else:
                        success, encoded_img = cv2.imencode('.jpg', marked_img)
                    
                    if success:
                        with open(marked_path, 'wb') as f:
                            f.write(encoded_img.tobytes())
                        print(f"保存标注图片成功: {marked_path}")
                    else:
                        print(f"保存标注图片失败: {marked_path}")
                    
                    # 步骤7: 保存OCR识别结果为JSON文件（只包含汉字结果，使用原始框坐标）
                    if all_ocr_results:
                        # 保存JSON文件到输出目录，格式: {"识别文字": [x1,y1,x2,y2]}
                        json_path = os.path.join(output_path, f"{file_base}_ocr_result.json")
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(all_ocr_results, f, ensure_ascii=False, indent=2)
                        print(f"保存OCR结果JSON文件成功: {json_path}")
                        print(f"汉字识别结果: {all_ocr_results}")
                    else:
                        print(f"文件 {filename} 未识别到任何汉字")

                    print(f"成功处理文件 {filename}，结果已保存到 {output_path}")
                
                except Exception as e:
                    # 捕获并打印处理过程中出现的任何异常
                    print(f"处理文件 {filename} 时出错: {str(e)}")
                    continue

# 主程序入口
if __name__ == '__main__':
    # 配置参数
    input_dir = Config.get_input_dir("word")       # 输入图片目录
    output_dir = Config.get_output_dir("word")      # 输出结果目录
    api_url = Config.DET_API_URL   # 目标检测API地址
    ocr_api_url = Config.OCR_API_URL  # OCR文字识别API地址
    ext_rate = 0.05  # 扩展比例，默认5%
    
    # 创建OCR处理器实例
    my_ocr = MyOcr(api_url, ocr_api_url, ext_rate)
    
    # 调用处理方法
    my_ocr.process_directory(input_dir, output_dir)
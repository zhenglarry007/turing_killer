# 导入必要的库
import ddddocr  # 用于本地目标检测和OCR识别
import cv2      # OpenCV库，用于图像处理
import os       # 用于文件和目录操作
import requests # 用于HTTP请求（远程API调用）
import numpy as np  # 添加numpy用于图像合并

class MyOcr(object):
    def __init__(self, api_url=None):
        """
        初始化OCR处理器
        参数:
            api_url: 可选，远程OCR服务的API地址。如果为None则使用本地ddddocr
        """
        self.api_url = api_url
        # 如果没有提供API地址，初始化本地OCR
        if not self.api_url:
            print('api_url='+str(api_url))
            self.ocr = ddddocr.DdddOcr(det=True)
    
    def detect_objects(self, filename, img_bytes):
        """
        对象检测方法（支持本地/远程两种模式）
        参数:
            img_bytes: 图片的二进制数据
        返回:
            检测框坐标列表，每个框格式为[x1,y1,x2,y2]
        """
        if self.api_url:
            # 远程API模式
            try:
                # 发送POST请求到API服务
                files = {'image': (filename, img_bytes, 'image/jpeg')}  # 修正这里
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
                print(f"调用API服务出错: {str(e)}")
                return []
        else:
            # 本地OCR模式
            return self.ocr.detection(img_bytes)
    
    def merge_images_horizontally(self, images):
        """
        横向合并多个图像
        参数:
            images: 图像列表
        返回:
            合并后的图像
        """
        if not images:
            return None
            
        # 获取所有图像的高度和宽度
        heights = [img.shape[0] for img in images]
        widths = [img.shape[1] for img in images]
        
        # 使用最大高度作为合并后图像的高度
        max_height = max(heights)
        
        # 计算总宽度
        total_width = sum(widths)
        
        # 创建空白图像
        merged_image = np.zeros((max_height, total_width, 3), dtype=np.uint8)
        
        # 将每个图像粘贴到合并图像中
        x_offset = 0
        for img in images:
            h, w = img.shape[:2]
            merged_image[0:h, x_offset:x_offset+w] = img
            x_offset += w
            
        return merged_image
    
    def recognize_merged_image(self, image):
        """
        识别合并后的图像
        参数:
            image: 合并后的图像
        返回:
            OCR识别结果
        """
        # 这里可以根据需要实现OCR识别逻辑
        # 例如使用ddddocr或其他OCR库进行识别
        # 暂时返回空字符串作为示例
        return ""
    
    def process_directory(self, input_path, output_path):
        """
        主处理方法：遍历处理输入目录中的所有图片文件
        参数:
            input_path: 输入图片所在目录路径
            output_path: 处理结果输出目录路径
        功能流程:
            1. 自动创建输出目录(如果不存在)
            2. 遍历输入目录中的图片文件
            3. 对每个图片：
               a. 先截取所有检测到的目标区域并保存
               b. 最后在原图上标注所有目标区域
        """
        # 确保输出目录和label子目录存在
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
                    
                    # 步骤2: 调用检测方法（自动区分本地/远程模式）
                    poses = self.detect_objects(filename, img_bytes)
                    print(f"文件 {filename} 检测到 {len(poses)} 个目标区域")
                    
                    # 如果没有检测到任何目标，跳过后续处理
                    if not poses:
                        print(f"警告: 文件 {filename} 未检测到任何目标")
                        continue

                    print("poses="+str(poses))
                    
                    # 步骤3: 使用OpenCV读取图片用于裁剪和标注
                    im = cv2.imread(file_path)
                    # 创建原图的副本用于标注（避免修改影响裁剪）
                    marked_img = im.copy()
                    
                    # 初始化cropped_images列表，用于存储所有裁剪的图像
                    cropped_images = []
                    
                    # 步骤4: 先处理所有目标区域的截取
                    for i, box in enumerate(poses):
                        # 解包坐标值
                        x1, y1, x2, y2 = box

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
                        
                        # 4.1 裁剪目标区域
                        cropped_img = im[y1:y2, x1:x2]
                        
                        # 将裁剪的图像添加到列表中
                        cropped_images.append(cropped_img)
                        
                        # 4.2 构建裁剪图的保存路径
                        # 格式: 原文件名_序号.扩展名
                        os.makedirs(os.path.join(output_path, file_base), exist_ok=True)
                        cropped_path = os.path.join(
                            output_path, 
                            file_base,
                            f"{file_base}_{i}{file_ext}"
                        )
                        
                        # 4.3 保存裁剪后的图片
                        cv2.imwrite(cropped_path, cropped_img)
                        
                        # 4.4 在副本图上绘制矩形标记(红色边框，线宽2像素)
                        marked_img = cv2.rectangle(
                            marked_img, 
                            (x1, y1), (x2, y2), 
                            color=(0, 0, 255),  # BGR格式的红色
                            thickness=2
                        )
                    
                    # 步骤5: 横向合并所有截取的区域并进行OCR识别
                    if cropped_images:
                        merged_image = self.merge_images_horizontally(cropped_images)
                        ocr_result = self.recognize_merged_image(merged_image)
                        print(f"文件 {filename} 合并区域OCR识别结果: {ocr_result}")
                    else:
                        print(f"文件 {filename} 无有效区域可合并识别")
                    
                    # 步骤6: 最后保存标记后的原图到label子目录
                    # 文件名格式: 原文件名_mark.扩展名
                    marked_path = os.path.join(
                        output_path,
                        f"{file_base}_mark{file_ext}"  # 修复了这里的语法错误
                    )
                    cv2.imwrite(marked_path, marked_img)
                    
                    print(f"成功处理文件 {filename}，结果已保存到 {output_path}")
                
                except Exception as e:
                    # 捕获并打印处理过程中出现的任何异常
                    print(f"处理文件 {filename} 时出错: {str(e)}")
                    continue

# 主程序入口
if __name__ == '__main__':
    # 配置参数（根据实际情况修改）
    input_dir = "pic_det"   # 输入图片目录
    output_dir = "output"     # 输出结果目录
    api_url = "http://localhost:9890/det"  # OCR API地址
    #api_url = None;
    # 创建OCR处理器实例（传入API地址）
    my_ocr = MyOcr(api_url)
    
    # 调用处理方法
    my_ocr.process_directory(input_dir, output_dir)
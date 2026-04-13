import os

# 获取当前文件所在目录（即 demo 目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 通用配置
class Config:
    # OCR文字识别API地址
    OCR_API_URL = "http://localhost:9890/ocr"
    
    # 目标检测API地址
    DET_API_URL = "http://localhost:9890/det"

    # 输入图片基础目录
    INPUT_BASE_DIR = os.path.join(BASE_DIR, "pic")
    
    # 输出结果基础目录
    OUTPUT_BASE_DIR = os.path.join(BASE_DIR, "output")

    # 支持的图片格式
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    
    @classmethod
    def get_input_dir(cls, task_type):
        """获取指定任务类型的输入目录"""
        return os.path.join(cls.INPUT_BASE_DIR, task_type)
        
    @classmethod
    def get_output_dir(cls, task_type):
        """获取指定任务类型的输出目录"""
        return os.path.join(cls.OUTPUT_BASE_DIR, task_type)

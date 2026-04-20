import os
import re
import hashlib
import time
import json
import numpy as np
import sys
import importlib.util
from datetime import datetime
from PIL import Image
import io

from api_layer import call_ocr_api, call_det_api

MyOcr = None

def _load_myocr_class():
    """
    动态加载 test_word_api.py 中的 MyOcr 类
    使用 importlib 从指定路径加载，避免 config 模块冲突
    """
    global MyOcr
    
    # 计算 demo 目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    demo_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'demo')
    
    if not os.path.exists(demo_dir):
        print(f"警告: demo 目录不存在: {demo_dir}")
        return None
    
    test_word_api_path = os.path.join(demo_dir, 'test_word_api.py')
    if not os.path.exists(test_word_api_path):
        print(f"警告: test_word_api.py 不存在: {test_word_api_path}")
        return None
    
    original_config_module = None
    try:
        # 保存原始的 sys.modules['config']
        original_config_module = sys.modules.get('config', None)
        
        # 保存原始 sys.path
        original_sys_path = sys.path.copy()
        
        # 将 demo 目录添加到 sys.path 最前面
        if demo_dir not in sys.path:
            sys.path.insert(0, demo_dir)
        
        # 先加载 demo/config.py 中的 Config 类
        config_path = os.path.join(demo_dir, 'config.py')
        if os.path.exists(config_path):
            spec_config = importlib.util.spec_from_file_location("demo_config", config_path)
            if spec_config and spec_config.loader:
                demo_config = importlib.util.module_from_spec(spec_config)
                sys.modules["demo_config"] = demo_config
                spec_config.loader.exec_module(demo_config)
                
                # 临时将 sys.modules['config'] 设置为 demo_config
                # 这样 test_word_api 在加载时会使用 demo/config.py 中的 Config 类
                sys.modules['config'] = demo_config
        
        # 现在加载 test_word_api.py
        spec = importlib.util.spec_from_file_location("test_word_api", test_word_api_path)
        if spec and spec.loader:
            test_word_api_module = importlib.util.module_from_spec(spec)
            sys.modules["test_word_api"] = test_word_api_module
            spec.loader.exec_module(test_word_api_module)
            
            # 获取 MyOcr 类
            if hasattr(test_word_api_module, 'MyOcr'):
                MyOcr = test_word_api_module.MyOcr
                print("✓ 成功加载 MyOcr 类")
        
        # 恢复原始的 sys.modules['config']
        if original_config_module is not None:
            sys.modules['config'] = original_config_module
        else:
            # 如果之前没有 config 模块，删除它
            if 'config' in sys.modules:
                del sys.modules['config']
        
        # 恢复原始 sys.path
        sys.path = original_sys_path
        
        return MyOcr
        
    except Exception as e:
        print(f"加载 MyOcr 类失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 确保恢复原始状态
        if 'config' in sys.modules and 'original_config_module' in dir():
            if original_config_module is not None:
                sys.modules['config'] = original_config_module
        
        return None

# 尝试加载 MyOcr 类
_load_myocr_class()

# 导入配置（在 _load_myocr_class 之后导入，确保使用正确的 config 模块）
from config import DET_API_URL, OCR_API_URL


class PicFinger:
    HASH_SIZE = 16

    def __init__(self, source):
        if isinstance(source, np.ndarray):
            if source.size != self.HASH_SIZE * self.HASH_SIZE:
                raise ValueError(f"length of hashValue must be {self.HASH_SIZE * self.HASH_SIZE}")
            self.binaryzation_matrix = source.flatten()
        elif isinstance(source, list):
            self.binaryzation_matrix = np.array(source, dtype=np.uint8)
        else:
            if isinstance(source, str):
                img = Image.open(source)
            elif isinstance(source, Image.Image):
                img = source
            else:
                raise ValueError("Unsupported source type. Must be image path, PIL Image, list or numpy array.")
            self.binaryzation_matrix = self._hash_value(img)

    def get_hash_code(self):
        compact_data = self.compact()
        md5_hash = hashlib.md5(compact_data).hexdigest()
        return md5_hash.upper()

    def _hash_value(self, img):
        img_resized = img.resize((self.HASH_SIZE, self.HASH_SIZE), Image.Resampling.LANCZOS)
        img_gray = img_resized.convert('L')
        pixels = np.array(img_gray).flatten()
        mean_val = np.mean(pixels)
        binary_matrix = (pixels >= mean_val).astype(np.uint8)
        return binary_matrix

    def compact(self):
        return self._compact_array(self.binaryzation_matrix)

    @staticmethod
    def _compact_array(hash_value):
        result_len = (len(hash_value) + 7) >> 3
        result = bytearray(result_len)
        b = 0
        for i in range(len(hash_value)):
            if (i & 7) == 0:
                b = 0
            if hash_value[i] == 1:
                b |= 1 << (i & 7)
            elif hash_value[i] != 0:
                raise ValueError("invalid hashValue, every element must be 0 or 1")
            if (i & 7) == 7 or i == len(hash_value) - 1:
                result[i >> 3] = b
        return bytes(result)


def is_chinese_char(text):
    if not text or len(text.strip()) == 0:
        return False
    chinese_pattern = re.compile(r'^[\u4e00-\u9fff]+$')
    return bool(chinese_pattern.match(text.strip()))


def _normalize_box_with_padding(bbox, img_width, img_height, padding=2):
    x1, y1, x2, y2 = bbox
    x1 = max(0, int(x1) - padding)
    y1 = max(0, int(y1) - padding)
    x2 = min(img_width, int(x2) + padding)
    y2 = min(img_height, int(y2) + padding)
    return [x1, y1, x2, y2]


def _is_valid_box_shape(box):
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    if width <= 0 or height <= 0:
        return False

    ratio_w_h = width / height
    ratio_h_w = height / width
    return ratio_w_h <= 2 and ratio_h_w <= 2


def get_word_by_det(image_bytes, ext_rate=0.05):
    if MyOcr is None:
        print("警告: 无法导入 MyOcr 类，使用备用实现")
        return _get_word_by_det_fallback(image_bytes, ext_rate)
    
    my_ocr = MyOcr(api_url=DET_API_URL, ocr_api_url=OCR_API_URL, ext_rate=ext_rate)
    
    bboxes = my_ocr.detect_objects("captcha.jpg", image_bytes)
    if not bboxes:
        return None
    
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    img_width, img_height = img.size
    
    result = {"center": {}, "bbox": {}}
    
    for bbox in bboxes:
        # 与 demo/test_word_api.py 的处理逻辑保持一致：
        # 1) 原框先加固定2像素padding；2) 过滤宽高比异常框；3) 再做比例扩展后OCR
        box = _normalize_box_with_padding(bbox, img_width, img_height, padding=2)
        if not _is_valid_box_shape(box):
            continue

        x1, y1, x2, y2 = box
        enlarged_box = my_ocr.enlarge_bbox(box, img_width, img_height, ext_rate)
        
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        cropped = img.crop((enlarged_box[0], enlarged_box[1], enlarged_box[2], enlarged_box[3]))
        buf = io.BytesIO()
        cropped.save(buf, format='JPEG')
        cropped_bytes = buf.getvalue()
        
        text = my_ocr.recognize_text(cropped_bytes)
        
        if text and my_ocr.is_chinese_char(text):
            result["center"][text] = f"{center_x},{center_y}"
            result["bbox"][text] = [x1, y1, x2, y2]
    
    return result


def _get_word_by_det_fallback(image_bytes, ext_rate=0.05):
    bboxes = call_det_api(image_bytes)
    if not bboxes:
        return None
    
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    img_width, img_height = img.size
    
    result = {"center": {}, "bbox": {}}
    
    for bbox in bboxes:
        # 与 demo/test_word_api.py 的处理逻辑保持一致：
        # 1) 原框先加固定2像素padding；2) 过滤宽高比异常框；3) 再做比例扩展后OCR
        box = _normalize_box_with_padding(bbox, img_width, img_height, padding=2)
        if not _is_valid_box_shape(box):
            continue

        x1, y1, x2, y2 = box
        
        if ext_rate > 0:
            delta_x = int(img_width * ext_rate + 0.5)
            delta_y = int(img_height * ext_rate + 0.5)
            enlarged_x1 = max(0, x1 - delta_x)
            enlarged_y1 = max(0, y1 - delta_y)
            enlarged_x2 = min(img_width, x2 + delta_x)
            enlarged_y2 = min(img_height, y2 + delta_y)
            enlarged_box = [enlarged_x1, enlarged_y1, enlarged_x2, enlarged_y2]
        else:
            enlarged_box = [x1, y1, x2, y2]
        
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        cropped = img.crop((enlarged_box[0], enlarged_box[1], enlarged_box[2], enlarged_box[3]))
        buf = io.BytesIO()
        cropped.save(buf, format='JPEG')
        cropped_bytes = buf.getvalue()
        
        text = call_ocr_api(cropped_bytes)
        
        if text and is_chinese_char(text):
            result["center"][text] = f"{center_x},{center_y}"
            result["bbox"][text] = [x1, y1, x2, y2]
    
    return result


def crop_image(image_bytes, crop_box):
    img = Image.open(io.BytesIO(image_bytes))
    cropped = img.crop((crop_box[0], crop_box[1], crop_box[2], crop_box[3]))
    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue()


def crop_chars_from_image(image_bytes, bbox_dict, title_chars):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    cropped_chars = []
    matched_chars = []
    
    for char in title_chars:
        if char in bbox_dict:
            x1, y1, x2, y2 = bbox_dict[char]
            char_img = img.crop((x1, y1, x2, y2))
            cropped_chars.append(char_img)
            matched_chars.append(char)
    
    return cropped_chars, matched_chars


def combine_chars_to_image(char_images, spacing=10):
    if not char_images:
        return None
    
    total_width = sum(img.width for img in char_images) + spacing * (len(char_images) - 1)
    max_height = max(img.height for img in char_images)
    
    new_img = Image.new('RGB', (total_width, max_height), (255, 255, 255))
    
    x_offset = 0
    for char_img in char_images:
        new_img.paste(char_img, (x_offset, 0))
        x_offset += char_img.width + spacing
    
    return new_img


def generate_image_hash(image):
    if image is None:
        return None
    try:
        pic_finger = PicFinger(image)
        return pic_finger.get_hash_code()
    except Exception as e:
        print(f"生成图片指纹失败: {e}")
        return hashlib.md5(str(time.time()).encode()).hexdigest().upper()


def ensure_data_dirs(data_path):
    os.makedirs(os.path.join(data_path, "title"), exist_ok=True)
    os.makedirs(os.path.join(data_path, "data"), exist_ok=True)


def ensure_save_dirs(base_dir, is_success):
    time_dir_name = datetime.now().strftime('%Y%m%d%H')
    result_dir_name = "success" if is_success else "fail"
    save_dir = os.path.join(base_dir, time_dir_name, result_dir_name)
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def ensure_time_dir(base_dir):
    time_dir_name = datetime.now().strftime('%Y%m%d%H')
    time_dir = os.path.join(base_dir, time_dir_name)
    title_dir = os.path.join(time_dir, "title")
    os.makedirs(title_dir, exist_ok=True)
    return time_dir, title_dir


def save_captcha_data(save_dir, title, big_bytes, bbox_dict, combined_img, matched_chars):
    matched_title = "".join(matched_chars)
    
    hash_code = generate_image_hash(combined_img) if combined_img else "unknown"
    
    base_filename = f"{matched_title}_{hash_code}" if matched_title else f"unknown_{hash_code}"
    
    jpg_path = os.path.join(save_dir, f"{base_filename}.jpeg")
    json_path = os.path.join(save_dir, f"{base_filename}.json")
    
    if combined_img:
        combined_img.save(jpg_path, format='JPEG', quality=95)
        print(f"组合图片已保存: {jpg_path}")
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(bbox_dict, f, ensure_ascii=False, indent=2)
    print(f"检测数据已保存: {json_path}")
    
    return base_filename


def save_captcha_data_keep_big_image(save_dir, title, big_bytes, bbox_dict, matched_chars):
    matched_title = "".join(matched_chars)

    hash_code = "unknown"
    image_ext = "png"
    if big_bytes:
        try:
            big_img = Image.open(io.BytesIO(big_bytes))
            hash_code = generate_image_hash(big_img)
            img_format = (big_img.format or "PNG").lower()
            image_ext = "jpg" if img_format == "jpeg" else img_format
        except Exception as e:
            print(f"解析大图验证码失败，使用字节MD5作为hash: {e}")
            hash_code = hashlib.md5(big_bytes).hexdigest().upper()

    base_filename = f"{matched_title}_{hash_code}" if matched_title else f"unknown_{hash_code}"

    image_path = os.path.join(save_dir, f"{base_filename}.{image_ext}")
    json_path = os.path.join(save_dir, f"{base_filename}.json")

    if big_bytes:
        with open(image_path, 'wb') as f:
            f.write(big_bytes)
        print(f"大图验证码已保存: {image_path}")

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(bbox_dict, f, ensure_ascii=False, indent=2)
    print(f"检测数据已保存: {json_path}")

    return base_filename


def gen_checksum(data):
    return hashlib.md5(data).hexdigest()

import os
import re
import hashlib
import time
import json
import numpy as np
from datetime import datetime
from PIL import Image
import io

from api_layer import call_ocr_api


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


def get_word_by_det(image_bytes, ext_rate=0.15):
    from api_layer import call_det_api
    
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
    
    for i, bbox in enumerate(bboxes):
        x1, y1, x2, y2 = bbox
        
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


def gen_checksum(data):
    return hashlib.md5(data).hexdigest()

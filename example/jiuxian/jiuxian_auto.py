#!/usr/bin/env python3
import os
import re
import time
import hashlib
import json
import tempfile
import numpy as np
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import io
from PIL import Image
import requests
import base64


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


DATA_PATH = os.path.join(tempfile.gettempdir(), "JiuXian")
INDEX_URL = "https://login.jiuxian.com/login.htm"
OCR_API_URL = "http://127.0.0.1:9890/ocr"
DET_API_URL = "http://127.0.0.1:9890/det"
EXECUTE_COUNT = 10


def ensure_data_dirs():
    os.makedirs(os.path.join(DATA_PATH, "title"), exist_ok=True)
    os.makedirs(os.path.join(DATA_PATH, "data"), exist_ok=True)


def gen_checksum(data):
    return hashlib.md5(data).hexdigest()


def call_ocr_api(image_bytes, model="dddd_ocr"):
    try:
        files = {"image": ("captcha.jpg", image_bytes, "image/jpeg")}
        data = {"model": model}
        response = requests.post(OCR_API_URL, files=files, data=data, timeout=10)
        response.raise_for_status()
        res_json = response.json()
        if res_json.get("status") == 200:
            return res_json.get("result", "")
        else:
            print(f"OCR API 返回错误: {res_json}")
            return ""
    except Exception as e:
        print(f"调用 OCR API 失败: {e}")
        return ""


def call_det_api(image_bytes, model="dddd_det"):
    try:
        files = {"image": ("captcha.jpg", image_bytes, "image/jpeg")}
        data = {"model": model}
        response = requests.post(DET_API_URL, files=files, data=data, timeout=10)
        response.raise_for_status()
        res_json = response.json()
        if res_json.get("status") == 200:
            return res_json.get("result", [])
        else:
            print(f"DET API 返回错误: {res_json}")
            return []
    except Exception as e:
        print(f"调用 DET API 失败: {e}")
        return []


def get_word_by_det(image_bytes, ext_rate=0.15):
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


def is_chinese_char(text):
    if not text or len(text.strip()) == 0:
        return False
    chinese_pattern = re.compile(r'^[\u4e00-\u9fff]+$')
    return bool(chinese_pattern.match(text.strip()))


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


def ensure_save_dirs(base_dir, is_success):
    time_dir_name = datetime.now().strftime('%Y%m%d%H')
    result_dir_name = "success" if is_success else "fail"
    save_dir = os.path.join(base_dir, time_dir_name, result_dir_name)
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


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


def get_image_by_js(driver, element_id):
    try:
        element = driver.find_element(By.ID, element_id)
        
        tag_name = element.tag_name.lower()
        
        if tag_name == 'canvas':
            data_url = driver.execute_script(
                "return arguments[0].toDataURL('image/png');", element
            )
            if data_url and data_url.startswith('data:image'):
                base64_str = data_url.split(',', 1)[1]
                return base64.b64decode(base64_str)
        
        elif tag_name == 'img':
            src = element.get_attribute('src')
            if src and src.startswith('data:image'):
                base64_str = src.split(',', 1)[1]
                return base64.b64decode(base64_str)
            elif src and src.startswith('http'):
                data_url = driver.execute_script("""
                    var img = arguments[0];
                    var canvas = document.createElement('canvas');
                    canvas.width = img.naturalWidth || img.width;
                    canvas.height = img.naturalHeight || img.height;
                    var ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    return canvas.toDataURL('image/png');
                """, element)
                if data_url and data_url.startswith('data:image'):
                    base64_str = data_url.split(',', 1)[1]
                    return base64.b64decode(base64_str)
        
        location = element.location
        size = element.size
        
        png = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(png))
        
        left = location['x']
        top = location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']
        
        img = img.crop((left, top, right, bottom))
        
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
        
    except Exception as e:
        print(f"获取图片失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def crop_image(image_bytes, crop_box):
    img = Image.open(io.BytesIO(image_bytes))
    cropped = img.crop((crop_box[0], crop_box[1], crop_box[2], crop_box[3]))
    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue()


def action_move_word_click(driver, element, scale, result_str):
    if not result_str:
        return False
    
    actions = ActionChains(driver)
    location = element.location
    size = element.size
    
    points = result_str.split("|")
    
    for point in points:
        if not point:
            continue
        try:
            x, y = point.split(",")
            x = int(float(x) * scale)
            y = int(float(y) * scale)
            
            target_x = location['x'] + x
            target_y = location['y'] + y
            
            actions.move_to_element_with_offset(element, x, y)
            actions.click()
            actions.pause(0.2)
        except Exception as e:
            print(f"解析坐标点失败: {point}, error: {e}")
            continue
    
    actions.perform()
    return True


def wait_element(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        return None


def wait_element_visible(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        return None


def wait_element_clickable(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        return element
    except TimeoutException:
        return None


class RetEntity:
    def __init__(self):
        self.ret = -1
        self.msg = ""
    
    def set_msg(self, msg):
        self.msg = msg
    
    def set_ret(self, ret):
        self.ret = ret


def jiuxian_send(driver, area_code, phone):
    ret_entity = RetEntity()
    ensure_data_dirs()
    
    current_base_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        print(f"访问登录页: {INDEX_URL}")
        driver.get(INDEX_URL)
        
        print("1. 切换到手机动态密码登录")
        tab_element = wait_element_clickable(
            driver, 
            By.XPATH, 
            "//a[text()='手机动态密码登录']", 
            10
        )
        if tab_element:
            tab_element.click()
        else:
            ret_entity.set_msg("未找到手机动态密码登录标签")
            return ret_entity
        
        print("2. 输入手机号")
        phone_element = wait_element(driver, By.NAME, "phone", 5)
        if phone_element:
            phone_element.clear()
            phone_element.send_keys(phone)
        else:
            ret_entity.set_msg("未找到手机号输入框")
            return ret_entity
        
        print("3. 获取标题验证码小图")
        wait_element(driver, By.ID, "captchaImage_mobile", 10)
        
        title_bytes = get_image_by_js(driver, "captchaImage_mobile")
        if title_bytes is None:
            ret_entity.set_msg("获取标题验证码图片失败")
            return ret_entity
        
        title_image = Image.open(io.BytesIO(title_bytes)) if title_bytes else None
        
        crop_x1, crop_y1, crop_x2, crop_y2 = 91, 0, 168, title_image.height if title_image else 0
        small_byte = crop_image(title_bytes, [crop_x1, crop_y1, crop_x2, crop_y2]) if title_image else None
        
        small_len = len(small_byte) if small_byte else -1
        if small_len < 100:
            ret_entity.set_msg(f"smallLen:{small_len}")
            return ret_entity
        
        print("4. OCR识别标题汉字")
        title_org = call_ocr_api(small_byte, model="dddd_ocr")
        print(f"title_org={title_org}")
        
        title = re.sub(r'[^\u4e00-\u9fa5]', '', title_org) if title_org else None
        if title is None or len(title) != 3:
            print(f"titleOrg={title_org}->{title}")
            return ret_entity
        
        title_file = os.path.join(DATA_PATH, "title", f"{title}.png")
        with open(title_file, 'wb') as f:
            f.write(small_byte)
        print(f"标题验证码已保存: {title_file}")
        
        print("5. 点击触发大图验证码")
        find_element = driver.find_element(By.ID, "captchaImage_mobile")
        find_element.click()
        
        print("6. 等待大图验证码出现")
        big_element = wait_element_visible(driver, By.ID, "captchaImage2_mobile", 10)
        if not big_element:
            ret_entity.set_msg("大图验证码未出现")
            return ret_entity
        
        print("7. 获取大图验证码")
        big_bytes = get_image_by_js(driver, "captchaImage2_mobile")
        big_len = len(big_bytes) if big_bytes else -1
        if big_len < 100:
            ret_entity.set_msg(f"bigLen:{big_len}")
            return ret_entity
        
        print("8. 检测大图中的汉字")
        begin = time.time()
        word_list = get_word_by_det(big_bytes, 0.15)
        
        center_json = word_list.get("center") if word_list else None
        bbox_json = word_list.get("bbox", {}) if word_list else {}
        
        center_len = len(center_json) if center_json else -1
        
        print(f"检测到 {center_len} 个汉字: {list(center_json.keys()) if center_json else []}")
        
        matched_chars = []
        center_points = []
        is_success = False
        
        if center_json and len(title) == 3:
            for i in range(3):
                word = title[i:i+1]
                center_xy = center_json.get(word)
                if center_xy:
                    center_points.append(center_xy)
                    matched_chars.append(word)
        
        print(f"标题汉字: {title}, 匹配到: {matched_chars}")
        
        cropped_chars = []
        combined_img = None
        
        if bbox_json:
            cropped_chars, actual_matched = crop_chars_from_image(
                big_bytes, bbox_json, title
            )
            if cropped_chars:
                combined_img = combine_chars_to_image(cropped_chars)
        
        all_detected_bbox = bbox_json if bbox_json else {}
        save_dir = ensure_save_dirs(current_base_dir, len(matched_chars) == 3)
        
        if all_detected_bbox:
            save_captcha_data(
                save_dir, 
                title, 
                big_bytes, 
                all_detected_bbox, 
                combined_img, 
                matched_chars
            )
        
        if len(center_points) != 3:
            result = "|".join(center_points)
            print(f"{result} -> size not 3 (需要3个，实际{len(center_points)}个)")
            ret_entity.set_msg(f"size[{len(center_points)}] not 3")
            return ret_entity
        
        result = "|".join(center_points)
        cost = time.time() - begin
        
        print(f"      |title={title},result={result}->cost={cost:.2f}s")
        
        print("9. 执行点击")
        bg_element = driver.find_element(By.ID, "captchaImage2_mobile")
        
        use_robot = False
        if use_robot:
            print("使用 RobotMove (暂未实现)")
        else:
            action_move_word_click(driver, bg_element, 1.0, result)
        
        time.sleep(0.5)
        
        print("10. 校验验证码通过状态")
        succ_xpath = "//p[@id='captchaImage_mobile_success' and not(contains(@style,'display: none'))]"
        succ_element = wait_element_visible(driver, By.XPATH, succ_xpath, 30)
        succ_txt = succ_element.text if succ_element else None
        print(f"      |succTxt={succ_txt}")
        
        print("11. 获取短信验证码")
        send_element = wait_element_clickable(driver, By.XPATH, "//span[@id='idenCodePhone']", 1)
        if send_element:
            driver.execute_script("arguments[0].click();", send_element)
        else:
            ret_entity.set_msg("未找到获取短信验证码按钮")
            return ret_entity
        
        print("12. 等待倒计时文案")
        gt_xpath = "//span[@id='idenCodePhoneNum' and contains(.,'秒后重新获取')]"
        gt_element = wait_element_visible(driver, By.XPATH, gt_xpath, 30)
        msg = gt_element.text if gt_element else None
        ret_entity.set_msg(f"msg:{msg}")
        
        if msg is not None:
            ret_entity.set_ret(0)
            save_dir_success = ensure_save_dirs(current_base_dir, True)
            save_captcha_data(
                save_dir_success, 
                title, 
                big_bytes, 
                bbox_json, 
                combined_img, 
                matched_chars
            )
        
        return ret_entity
        
    except Exception as e:
        print(f"phone={phone},e={e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        print("清理Cookie...")
        driver.delete_all_cookies()


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"使用默认方式启动Chrome失败: {e}")
        print("尝试使用Service方式...")
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.maximize_window()
    
    return driver


def main():
    import random
    
    execute_count = EXECUTE_COUNT
    
    print(f"开始执行酒仙网自动化任务，执行次数: {execute_count} 次")
    
    driver = create_driver()
    
    try:
        for i in range(execute_count):
            current_round = i + 1
            
            print(f"\n{'='*60}")
            print(f"第 {current_round}/{execute_count} 次执行")
            print(f"{'='*60}")
            print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            phone_prefixes = ["131", "132", "133", "135", "136", "137", "138", "139", "150", "151", "152", "153", "155", "156", "157", "158", "159", "186", "187", "188", "189"]
            random_prefix = random.choice(phone_prefixes)
            random_suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
            random_phone = f"{random_prefix}{random_suffix}"
            
            result = jiuxian_send(driver, "62", random_phone)
            
            if result:
                print(f"执行结果: ret={result.ret}, msg={result.msg}")
            else:
                print(f"执行结果: 失败")
            
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"任务完成！共执行 {execute_count} 次")
        print(f"{'='*60}")
            
    finally:
        print("正在关闭浏览器...")
        driver.quit()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import base64
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import io
from PIL import Image
import requests

try:
    from pic_finger import PicFinger
except ImportError:
    print("警告: pic_finger 模块未找到，将使用备用方案")
    PicFinger = None


def test_ocr(image_bytes):
    """
    调用 turing_server API 识别验证码
    """
    try:
        url = "http://127.0.0.1:9890/ocr"
        data = {"model": "jrcpcx"}
        files = {"image": ("captcha.jpg", image_bytes, "image/jpeg")}
        
        response = requests.post(url, data=data, files=files, timeout=10)
        response.raise_for_status()
        
        res_json = response.json()
        if res_json.get("status") == 200:
            return res_json.get("result")
        else:
            print(f"API 返回错误: {res_json}")
    except Exception as e:
        print(f"调用 API 识别验证码失败: {e}")
        
    return ""


def wait_element(driver, by, value, timeout=10):
    """
    等待元素出现
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        return None


def wait_element_visible(driver, by, value, timeout=10):
    """
    等待元素可见
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        return None


def get_captcha_and_recognize(driver):
    """
    使用 Selenium 获取验证码图片，识别并保存
    每次执行前刷新并清除 cookie
    """
    try:
        driver.delete_all_cookies()
        print("已清除 cookie，正在刷新页面...")
        driver.refresh()
        
        time.sleep(2)
        
        img_selector = (By.CSS_SELECTOR, "img.code-img.pointer")
        img_element = wait_element_visible(driver, img_selector[0], img_selector[1], timeout=10)
        
        if not img_element:
            print("未能找到验证码图片元素")
            return
        
        src = img_element.get_attribute("src")
        
        if not src or not src.startswith("data:image"):
            print("未能获取到有效的验证码图片 Base64 数据")
            return
            
        print("成功获取验证码图片 Base64 数据")
        
        base64_str = src.split(",")[1]
        image_bytes = base64.b64decode(base64_str)
        
        img_buffer = Image.open(io.BytesIO(image_bytes))
        if img_buffer.mode != 'RGB':
            img_buffer = img_buffer.convert('RGB')
            
        try:
            if PicFinger:
                pic_finger = PicFinger(img_buffer)
                img_md5 = pic_finger.get_hash_code()
            else:
                img_md5 = str(int(time.time()))
        except Exception as e:
            print(f"计算图片指纹失败: {e}")
            img_md5 = str(int(time.time()))
        
        print("正在识别验证码...")
        rgb_byte_arr = io.BytesIO()
        img_buffer.save(rgb_byte_arr, format='JPEG')
        rgb_image_bytes = rgb_byte_arr.getvalue()
        
        result = ""
        max_retries = 3
        for attempt in range(max_retries):
            result = test_ocr(rgb_image_bytes)
            if result and len(result.strip()) > 0:
                break
            print(f"第 {attempt+1} 次识别失败，重试中...")
            time.sleep(1)
        
        print("-" * 30)
        print(f"识别结果: {result}")
        print("-" * 30)
        
        if not result or len(result.strip()) == 0:
            print("未能识别出验证码，停止流程")
            return

        phone_prefixes = ["131", "132", "133", "135", "136"]
        random_prefix = random.choice(phone_prefixes)
        random_suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
        random_phone = f"{random_prefix}{random_suffix}"
        
        phone_input_selector = (By.CSS_SELECTOR, 'input[placeholder="请输入手机号"]')
        phone_input = wait_element_visible(driver, phone_input_selector[0], phone_input_selector[1], timeout=5)
        if phone_input:
            phone_input.clear()
            phone_input.send_keys(random_phone)
            print(f"已输入手机号: {random_phone}")
        else:
            print("未找到手机号输入框")
            return

        code_input_selector = (By.CSS_SELECTOR, 'input[placeholder="请输入验证码"]')
        code_input = wait_element_visible(driver, code_input_selector[0], code_input_selector[1], timeout=5)
        if code_input:
            code_input.clear()
            code_input.send_keys(str(result))
            print("已输入验证码")
        else:
            print("未找到验证码输入框")
            return

        send_btn_selector = (By.XPATH, '//button[contains(text(), "发送验证码")]')
        send_btn = wait_element_visible(driver, send_btn_selector[0], send_btn_selector[1], timeout=5)
        if send_btn:
            send_btn.click()
            print("已点击发送验证码按钮")
        else:
            print("未找到发送验证码按钮")
            return

        is_success = True
        try:
            message_selector = (By.CSS_SELECTOR, '.el-message__content')
            message_element = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located(message_selector)
            )
            msg_text = message_element.text
            print(f"页面提示: {msg_text}")
            
            if "验证码错误" in msg_text:
                is_success = False
            elif "频繁" in msg_text or "上限" in msg_text:
                print("可能发送过于频繁，但暂不认为是验证码错误")
        except TimeoutException:
            print("未捕获到错误提示，假设验证码正确")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        time_dir_name = datetime.now().strftime('%Y%m%d%H')
        time_dir = os.path.join(current_dir, time_dir_name)
        result_dir_name = "success" if is_success else "fail"
        save_dir = os.path.join(time_dir, result_dir_name)
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        img_format = "jpg"
        save_path = os.path.join(save_dir, f"{result}_{img_md5}.{img_format}")
        
        try:
            img_to_save = Image.open(io.BytesIO(image_bytes))
            if img_to_save.mode != 'RGB':
                img_to_save = img_to_save.convert('RGB')
            img_to_save.save(save_path, format="JPEG")
            print(f"已将图片保存至: {save_path}")
        except Exception as e:
            print(f"保存图片为 jpg 格式失败: {e}")
            
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


def create_driver():
    """
    创建 Selenium WebDriver 实例
    """
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
    target_count = 100
    total_duration = 48 * 3600
    
    start_time = time.time()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"开始执行自动化任务，目标收集 {target_count} 张图片，最大兜底时长: {total_duration/3600}小时")
    
    driver = create_driver()
    
    try:
        url = "https://www.jrcpcx.cn/#/login"
        print(f"正在首次访问: {url}")
        driver.get(url)
        
        time.sleep(3)
        
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            time_dir_name = datetime.now().strftime('%Y%m%d%H')
            time_dir = os.path.join(current_dir, time_dir_name)
            success_dir = os.path.join(time_dir, "success")
            fail_dir = os.path.join(time_dir, "fail")
            
            saved_count = 0
            if os.path.exists(success_dir):
                saved_count += len(os.listdir(success_dir))
            if os.path.exists(fail_dir):
                saved_count += len(os.listdir(fail_dir))
            
            if saved_count >= target_count:
                print(f"\n当前目录 {time_dir_name} 任务圆满完成！已成功收集 {target_count} 张图片。")
                break
                
            if elapsed_time >= total_duration:
                print("已达到最大设定的运行时长，任务结束。")
                break
                
            print(f"\n--- 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (已运行 {int(elapsed_time)} 秒, 已保存 {saved_count}/{target_count} 张) ---")
            
            get_captcha_and_recognize(driver)
            
            time.sleep(2)
            
    finally:
        print("正在关闭浏览器...")
        driver.quit()


if __name__ == "__main__":
    main()

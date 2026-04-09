#!/usr/bin/env python3
import os
import base64
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
import io
from PIL import Image
import requests

try:
    from pic_finger import PicFinger
except ImportError:
    from pic_finger import PicFinger

def test_ocr(image_bytes):
    """
    调用 turing_server API 识别验证码
    """
    try:
        url = "http://127.0.0.1:9890/ocr"
        # 远程地址 192.169.9.20
        # 传递 model 参数和 image 文件 
        data = {"model": "jrcpcx"}  # 根据配置文件可使用 'jrcpcx' 或 'dddd_ocr'
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

def get_captcha_and_recognize(page):
    """
    使用 Playwright 获取验证码图片，识别并保存
    这里复用传入的 page 实例以提高效率，每次执行前刷新并清除 cookie
    """
    try:
        # 清除 cookie 并刷新当前页面
        page.context.clear_cookies()
        print("已清除 cookie，正在刷新页面...")
        page.reload(wait_until="networkidle", timeout=30000)
        
        # 等待验证码图片元素出现
        # 根据提供的 HTML 结构，图片有 class="code-img pointer"
        img_selector = "img.code-img.pointer"
        page.wait_for_selector(img_selector, timeout=10000)
        
        # 获取 src 属性（即 Base64 数据）
        src = page.get_attribute(img_selector, "src")
        
        if not src or not src.startswith("data:image"):
            print("未能获取到有效的验证码图片 Base64 数据")
            return
            
        print("成功获取验证码图片 Base64 数据")
        
        # 提取 Base64 字符串（去掉 "data:image/gif;base64," 前缀）
        # 兼容可能的其他格式如 png, jpeg 等
        base64_str = src.split(",")[1]
        
        # 将 Base64 解码为图片字节
        image_bytes = base64.b64decode(base64_str)
        
        # 将二进制数据转为 PIL Image 对象
        img_buffer = Image.open(io.BytesIO(image_bytes))
        if img_buffer.mode != 'RGB':
            img_buffer = img_buffer.convert('RGB')
            
        # 计算图片指纹 MD5
        try:
            pic_finger = PicFinger(img_buffer)
            img_md5 = pic_finger.get_hash_code()
        except Exception as e:
            print(f"计算图片指纹失败: {e}")
            img_md5 = str(int(time.time()))
        
        # 调用 ddddocr 识别
        print("正在识别验证码...")
        # ddddocr 需要直接的图片字节数据，我们把转为 RGB 的图片再转回字节
        rgb_byte_arr = io.BytesIO()
        img_buffer.save(rgb_byte_arr, format='JPEG')
        rgb_image_bytes = rgb_byte_arr.getvalue()
        
        result = test_ocr(rgb_image_bytes)
        
        print("-" * 30)
        print(f"识别结果: {result}")
        print("-" * 30)
        
        if not result:
            print("未能识别出验证码，停止流程")
            return

        # 1. 填写手机号
        phone_prefixes = ["131", "132", "133", "135", "136"]
        random_prefix = random.choice(phone_prefixes)
        random_suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
        random_phone = f"{random_prefix}{random_suffix}"
        
        phone_input_selector = 'input[placeholder="请输入手机号"]'
        page.wait_for_selector(phone_input_selector, timeout=5000)
        page.fill(phone_input_selector, random_phone)
        print(f"已输入手机号: {random_phone}")

        # 2. 填写验证码
        code_input_selector = 'input[placeholder="请输入验证码"]'
        page.wait_for_selector(code_input_selector, timeout=5000)
        page.fill(code_input_selector, str(result))
        print("已输入验证码")

        # 3. 准备捕获消息 (使用 page.on("dialog") 或者监听 DOM 变化)
        # 在很多 Vue/Element UI 项目中，提示通常是以 class="el-message" 的形式挂在 body 下
        
        # 点击发送验证码按钮
        send_btn_selector = 'button:has-text("发送验证码")'
        page.wait_for_selector(send_btn_selector, timeout=5000)
        page.click(send_btn_selector)
        print("已点击发送验证码按钮")

        # 4. 判断结果
        # 等待一小段时间让提示框出现
        is_success = True
        try:
            # 尝试捕获错误提示
            message_selector = '.el-message__content'
            page.wait_for_selector(message_selector, timeout=3000)
            msg_text = page.inner_text(message_selector)
            print(f"页面提示: {msg_text}")
            
            if "验证码错误" in msg_text:
                is_success = False
            elif "频繁" in msg_text or "上限" in msg_text:
                # 如果遇到发送频繁等其他提示，也可视为不成功或另外处理
                print("可能发送过于频繁，但暂不认为是验证码错误")
                # 这里依然算作没有明确报验证码错误
        except Exception as e:
            # 如果没有弹出提示，或者不是"验证码错误"，暂时假设成功
            print("未捕获到错误提示，假设验证码正确")
        
        # 获取当前目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 根据当前时间生成年月日时的目录名
        time_dir_name = datetime.now().strftime('%Y%m%d%H')
        time_dir = os.path.join(current_dir, time_dir_name)
        
        # 根据结果保存到不同的子目录
        result_dir_name = "success" if is_success else "fail"
        save_dir = os.path.join(time_dir, result_dir_name)
        
        # 如果目录不存在则创建
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 强制将图片格式转为 jpg，并保存
        img_format = "jpg"
        save_path = os.path.join(save_dir, f"{result}_{img_md5}.{img_format}")
        
        try:
            # 使用 PIL 将原始字节转为 RGB 模式后保存为 JPEG
            # 前面在计算指纹时，可能已经将图片打开过，我们在这里复用或者重新打开转换
            img_to_save = Image.open(io.BytesIO(image_bytes))
            if img_to_save.mode != 'RGB':
                img_to_save = img_to_save.convert('RGB')
            img_to_save.save(save_path, format="JPEG")
            print(f"已将图片保存至: {save_path}")
        except Exception as e:
            print(f"保存图片为 jpg 格式失败: {e}")
            
    except Exception as e:
        print(f"发生错误: {e}")

def main():
    # 目标保存图片数量
    target_count = 100
    
    # 设置最大兜底运行时长为 48 小时 (172800秒)，防止网络波动导致死循环
    total_duration = 48 * 3600 
    
    start_time = time.time()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"开始执行自动化任务，目标收集 {target_count} 张图片，最大兜底时长: {total_duration/3600}小时")
    
    with sync_playwright() as p:
        # 启动一个浏览器实例复用
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        url = "https://www.jrcpcx.cn/#/login"
        print(f"正在首次访问: {url}")
        page.goto(url, wait_until="networkidle", timeout=30000)
        
        try:
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # 获取当前时间的目录路径
                time_dir_name = datetime.now().strftime('%Y%m%d%H')
                time_dir = os.path.join(current_dir, time_dir_name)
                success_dir = os.path.join(time_dir, "success")
                fail_dir = os.path.join(time_dir, "fail")
                
                # 统计当前时间目录下已保存的文件数量
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
                
                # 执行一次任务
                get_captcha_and_recognize(page)
                
        finally:
            browser.close()

if __name__ == "__main__":
    main()
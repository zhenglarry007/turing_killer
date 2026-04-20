import os
import re
import time
import tempfile
from PIL import Image
import io
from selenium.webdriver.common.by import By

from config import (
    DATA_PATH, 
    INDEX_URL, 
    TITLE_CROP_BOX, 
    MIN_IMAGE_SIZE
)
from api_layer import call_ocr_api
from image_layer import (
    ensure_data_dirs,
    ensure_time_dir,
    ensure_save_dirs,
    save_captcha_data_keep_big_image,
    crop_image,
    get_word_by_det,
    is_chinese_char
)
from browser_layer import (
    RetEntity,
    wait_element,
    wait_element_visible,
    wait_element_clickable,
    get_image_by_js,
    action_move_word_click
)


def get_system_tmp_dir() -> str:
    tmp = tempfile.gettempdir()

    if not os.path.exists(tmp):
        # 极端兜底（几乎不会发生）
        tmp = os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp"

    return tmp


def jiuxian_send(driver, area_code, phone):
    ret_entity = RetEntity()
    ensure_data_dirs(DATA_PATH)
    
    current_base_dir = os.path.join(get_system_tmp_dir(), "JiuXian")
    os.makedirs(current_base_dir, exist_ok=True)
    
    try:
        print(f"访问登录页: {INDEX_URL}")
        driver.get(INDEX_URL)
        time.sleep(0.1)
        
        print("1. 切换到手机动态密码登录")
        tab_element = wait_element_clickable(
            driver, 
            By.XPATH, 
            "//a[text()='手机动态密码登录']", 
            3
        )
        if tab_element:
            tab_element.click()
            time.sleep(0.1)
        else:
            ret_entity.set_msg("未找到手机动态密码登录标签")
            return ret_entity
        
        print("2. 输入手机号")
        phone_element = wait_element_visible(driver, By.NAME, "phone", 3)
        if phone_element:
            phone_element.clear()
            phone_element.send_keys(phone)
            time.sleep(0.1)
        else:
            ret_entity.set_msg("未找到手机号输入框")
            return ret_entity
        
        print("3. 获取标题验证码小图")
        captcha_element = wait_element_visible(driver, By.ID, "captchaImage_mobile", 3)
        if not captcha_element:
            ret_entity.set_msg("标题验证码元素不可见")
            return ret_entity
        
        title_bytes = get_image_by_js(driver, "captchaImage_mobile")
        if title_bytes is None:
            ret_entity.set_msg("获取标题验证码图片失败")
            return ret_entity
        
        title_image = Image.open(io.BytesIO(title_bytes)) if title_bytes else None
        
        crop_x1, crop_y1, crop_x2 = TITLE_CROP_BOX
        crop_y2 = title_image.height if title_image else 0
        small_byte = crop_image(title_bytes, [crop_x1, crop_y1, crop_x2, crop_y2]) if title_image else None
        
        small_len = len(small_byte) if small_byte else -1
        if small_len < MIN_IMAGE_SIZE:
            ret_entity.set_msg(f"smallLen:{small_len}")
            return ret_entity
        
        print("4. OCR识别标题汉字")
        title_org = call_ocr_api(small_byte, model="dddd_ocr")
        print(f"title_org={title_org}")
        
        title = re.sub(r'[^\u4e00-\u9fa5]', '', title_org) if title_org else None
        if title is None or len(title) != 3:
            print(f"titleOrg={title_org}->{title}")
            return ret_entity
        
        time_dir, title_dir = ensure_time_dir(current_base_dir)
        title_file = os.path.join(title_dir, f"{title}.png")
        if small_byte is None:
            ret_entity.set_msg("small captcha is empty")
            return ret_entity
        with open(title_file, 'wb') as f:
            f.write(small_byte)
        print(f"标题验证码已保存: {title_file}")
        
        print("5. 点击触发大图验证码")
        find_element = driver.find_element(By.ID, "captchaImage_mobile")
        find_element.click()
        time.sleep(0.1)
        
        print("6. 等待大图验证码出现")
        big_element = wait_element_visible(driver, By.ID, "captchaImage2_mobile", 3)
        if not big_element:
            ret_entity.set_msg("大图验证码未出现")
            return ret_entity
        
        print("7. 获取大图验证码")
        big_bytes = get_image_by_js(driver, "captchaImage2_mobile")
        big_len = len(big_bytes) if big_bytes else -1
        if big_len < MIN_IMAGE_SIZE:
            ret_entity.set_msg(f"bigLen:{big_len}")
            return ret_entity
        
        big_image_file = os.path.join(title_dir, f"{title}_big.png")
        with open(big_image_file, 'wb') as f:
            f.write(big_bytes)
        print(f"大图验证码已保存: {big_image_file}")
        
        print("8. 检测大图中的汉字")
        begin = time.time()
        # 与 demo/test_word_api.py 保持一致，使用 0.05 的扩展比例
        word_list = get_word_by_det(big_bytes, 0.05)
        
        center_json = word_list.get("center") if word_list else None
        bbox_json = word_list.get("bbox", {}) if word_list else {}
        
        center_len = len(center_json) if center_json else -1
        
        print(f"检测到 {center_len} 个汉字: {list(center_json.keys()) if center_json else []}")
        
        matched_chars = []
        center_points = []
        
        if center_json and len(title) == 3:
            for i in range(3):
                word = title[i:i+1]
                center_xy = center_json.get(word)
                if center_xy:
                    center_points.append(center_xy)
                    matched_chars.append(word)
        
        print(f"标题汉字: {title}, 匹配到: {matched_chars}")
        
        if len(center_points) != 3:
            result = "|".join(center_points)
            print(f"{result} -> size not 3 (需要3个，实际{len(center_points)}个)")
            ret_entity.set_msg(f"size[{len(center_points)}] not 3")
            return ret_entity
        
        result = "|".join(center_points)
        cost = time.time() - begin
        
        print(f"      |title={title},result={result}->cost={cost:.2f}s")
        
        print("9-12. (已跳过) 直接保存样本数据")
        ret_entity.set_ret(0)
        ret_entity.set_msg("已跳过点击，仅采集样本")
        save_dir_success = ensure_save_dirs(current_base_dir, True)
        save_captcha_data_keep_big_image(
            save_dir_success, 
            title, 
            big_bytes, 
            bbox_json, 
            matched_chars
        )
        return ret_entity
        
        '''
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
            save_captcha_data_keep_big_image(
                save_dir_success, 
                title, 
                big_bytes, 
                bbox_json, 
                matched_chars
            )
        
        return ret_entity
        '''
        
    except Exception as e:
        print(f"phone={phone},e={e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        print("清理Cookie...")
        driver.delete_all_cookies()

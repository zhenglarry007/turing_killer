import io
import base64
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class RetEntity:
    def __init__(self):
        self.ret = -1
        self.msg = ""
    
    def set_msg(self, msg):
        self.msg = msg
    
    def set_ret(self, ret):
        self.ret = ret


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
            
            actions.move_to_element_with_offset(element, x, y)
            actions.click()
            actions.pause(0.2)
        except Exception as e:
            print(f"解析坐标点失败: {point}, error: {e}")
            continue
    
    actions.perform()
    return True

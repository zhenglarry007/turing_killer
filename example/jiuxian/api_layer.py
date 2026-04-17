import requests
from config import OCR_API_URL, DET_API_URL


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

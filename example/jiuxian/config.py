import os
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(tempfile.gettempdir(), "JiuXian")
INDEX_URL = "https://login.jiuxian.com/login.htm"
OCR_API_URL = "http://127.0.0.1:9890/ocr"
DET_API_URL = "http://127.0.0.1:9890/det"
EXECUTE_COUNT = 10

TITLE_CROP_BOX = [91, 0, 168]
MIN_IMAGE_SIZE = 100

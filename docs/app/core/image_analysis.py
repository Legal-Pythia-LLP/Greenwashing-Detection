from PIL import Image
import pytesseract
import os

# 自动定位项目内封装的 tesseract.exe 路径
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TESSERACT_PATH = os.path.join(BASE_DIR, "..", "..", "tesseract", "tesseract.exe")

# 路径校验（防止运行报错）
if not os.path.exists(TESSERACT_PATH):
    raise FileNotFoundError(f"[OCR配置错误] 找不到 tesseract.exe，请确认路径：{TESSERACT_PATH}")

# 绑定路径
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def extract_text_from_image(image_path: str) -> str:
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="eng+chi_sim+spa+ita+deu")
    return text.strip()

from paddleocr import PaddleOCR
from PIL import Image
import pytesseract
import os

# === 配置 Tesseract 路径 ===
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TESSERACT_PATH = os.path.join(BASE_DIR, "..", "..", "tesseract", "tesseract.exe")

if not os.path.exists(TESSERACT_PATH):
    raise FileNotFoundError(f"[OCR配置错误] 找不到 tesseract.exe，请确认路径：{TESSERACT_PATH}")

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# === 初始化 PaddleOCR（中英文）===
ocr = PaddleOCR(use_angle_cls=True, lang='ch')



def extract_text(image_path: str) -> str:
    """
    主用 PaddleOCR，失败时回退 Tesseract
    """
    try:
        results = ocr.ocr(image_path)
        lines = []
        for line in results:
            for box, (text, score) in line:
                if score > 0.5:
                    lines.append(text)
        if lines:
            return "\n".join(lines).strip()
        else:
            raise ValueError("PaddleOCR 未识别出文字")
    except Exception as e:
        print(f"[警告] PaddleOCR 识别失败，尝试使用 Tesseract：{e}")
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang="eng+chi_sim+spa+ita+deu")
            return text.strip()
        except Exception as e2:
            print(f"[错误] Tesseract 识别也失败：{e2}")
            return ""
extract_text_from_image = extract_text

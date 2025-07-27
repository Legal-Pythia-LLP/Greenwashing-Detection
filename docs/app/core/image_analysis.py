from PIL import Image
import pytesseract
import os

pytesseract.pytesseract.tesseract_cmd = r"D:\OCR\tesseract.exe"

def extract_text_from_image(image_path: str) -> str:
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="eng+chi_sim+spa+ita+deu")

    return text.strip()

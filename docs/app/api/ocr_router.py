from fastapi import APIRouter, UploadFile, File
from app.core.image_analysis import extract_text_from_image
from app.core.ocr_analysis import analyse_ocr_text
from app.models.vision_models import OCRAnalysisResponse
import tempfile, shutil, os

ocr_router = APIRouter(prefix="/ocr", tags=["OCR"])

@ocr_router.post("/image/analyse", response_model=OCRAnalysisResponse)
async def ocr_image_analyse(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    try:
        text = extract_text_from_image(temp_path)
        analysis = analyse_ocr_text(text)
        return {
            "text": text,
            "highlights": analysis.get("highlights", []),
            "comment": analysis.get("comment", "")
        }
    finally:
        os.remove(temp_path)

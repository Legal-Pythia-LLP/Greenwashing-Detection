from fastapi import APIRouter, UploadFile, File
from app.core.image_analysis import extract_text_from_image
from app.models.vision_models import OCRResponse
import shutil
import os

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/ocr", response_model=OCRResponse)
async def ocr_image(file: UploadFile = File(...)):
    temp_path = f"uploads/{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text_from_image(temp_path)
    os.remove(temp_path)

    return {"text": text}

from fastapi import APIRouter, UploadFile, File, Query
from app.core.image_analysis import extract_text_from_image
from app.core.text_engine import analyse_text
from app.models.vision_models import OCRResponse, OCRAnalysisResponse
import tempfile, shutil, os

router = APIRouter(prefix="/ocr", tags=["OCR"])

@router.post("/image", response_model=OCRResponse)
async def ocr_image(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        shutil.copyfileobj(file.file, tmp); temp_path = tmp.name
    try:
        text = extract_text_from_image(temp_path)
        return {"text": text}
    finally:
        try: os.remove(temp_path)
        except: pass

@router.post("/image/analyse", response_model=OCRAnalysisResponse)
async def ocr_image_analyse(file: UploadFile = File(...), mode: str = Query("hybrid")):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        shutil.copyfileobj(file.file, tmp); temp_path = tmp.name
    try:
        text = extract_text_from_image(temp_path)
        r = analyse_text(text, mode=mode)
        return {"text": text, "highlights": r.get("highlights", []), "comment": r.get("comment", "")}
    finally:
        try: os.remove(temp_path)
        except: pass

from fastapi import APIRouter, UploadFile, File, Query
from app.core.image_analysis import extract_text_from_image
from app.core.ocr_analysis import analyse_ocr_text
from app.models.vision_models import OCRResponse, OCRAnalysisResponse
import tempfile, shutil, os

router = APIRouter(prefix="/ocr", tags=["OCR"])

@router.post("/image", response_model=OCRResponse)
async def ocr_image(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    try:
        text = extract_text_from_image(temp_path)
        return {"text": text}
    finally:
        try: os.remove(temp_path)
        except FileNotFoundError: pass

@router.post("/image/analyse", response_model=OCRAnalysisResponse)
async def ocr_image_analyse(
    file: UploadFile = File(...),
    # 先保留参数，后面要用的时候能直接接：mode=rules/llm/hybrid
    mode: str = Query("llm", description="rules|llm|hybrid（预留）")
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    try:
        text = extract_text_from_image(temp_path)
        analysis = analyse_ocr_text(text)  # 先不传 mode，等你准备好再接
        return {
            "text": text,
            "highlights": analysis.get("highlights", []),
            "comment": analysis.get("comment", "")
        }
    finally:
        try: os.remove(temp_path)
        except FileNotFoundError: pass

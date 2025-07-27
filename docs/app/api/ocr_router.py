# app/api/ocr_router.py

from fastapi import APIRouter, UploadFile, File
from app.core.image_analysis import extract_text
import os

ocr_router = APIRouter()

@ocr_router.post("/upload")
async def ocr_upload(file: UploadFile = File(...)):
    contents = await file.read()
    temp_path = "temp_ocr_input.png"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        result = extract_text(temp_path)
    finally:
        os.remove(temp_path)

    return {"text": result}

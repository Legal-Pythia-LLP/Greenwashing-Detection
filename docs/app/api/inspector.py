from fastapi import APIRouter, UploadFile, File, Query
import tempfile, shutil, os
from pypdf import PdfReader
from app.core.image_analysis import extract_text_from_image
from app.core.text_engine import analyse_text
from app.models.inspector_models import InspectResponse

router = APIRouter(prefix="/inspect", tags=["Inspect"])

@router.post("/file", response_model=InspectResponse)
async def inspect_file(file: UploadFile = File(...), mode: str = Query("hybrid")):
    name = (file.filename or "").lower()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    try:
        if name.endswith(".pdf"):
            reader = PdfReader(temp_path)
            texts = []
            for page in reader.pages:
                t = page.extract_text() or ""
                if t:
                    texts.append(t)
            text = "\n".join(texts)
            r = analyse_text(text, mode=mode)
            return {"file_type":"pdf","text":text,"highlights":r.get("highlights",[]),"comment":r.get("comment","")}
        if name.endswith((".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff")):
            text = extract_text_from_image(temp_path) or ""
            r = analyse_text(text, mode=mode)
            return {"file_type":"image","text":text,"highlights":r.get("highlights",[]),"comment":r.get("comment","")}
        return {"file_type":"other","text":"","highlights":[],"comment":"Unsupported file type"}
    finally:
        try: os.remove(temp_path)
        except: pass

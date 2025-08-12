from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal
from app.core.text_engine import analyse_text

router = APIRouter(prefix="/analysis", tags=["Analysis"])

class TextAnalysisRequest(BaseModel):
    text: str
    mode: Literal["rules","llm","hybrid"] = "hybrid"

class TextAnalysisResponse(BaseModel):
    text: str
    highlights: List[str]
    comment: str

@router.post("/text", response_model=TextAnalysisResponse)
async def analyze_text(req: TextAnalysisRequest):
    r = analyse_text(req.text, mode=req.mode)
    return {"text": req.text, "highlights": r.get("highlights", []), "comment": r.get("comment", "")}

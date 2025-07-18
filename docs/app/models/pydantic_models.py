from pydantic import BaseModel
from typing import List, Dict, Any

class ChatBaseMessage(BaseModel):
    message: str
    session_id: str

class ESGAnalysisResult(BaseModel):
    greenwashing_score: float
    confidence: float
    reasoning: str
    evidence: List[str]
    metrics: Dict[str, Any]
    detected_language: str 
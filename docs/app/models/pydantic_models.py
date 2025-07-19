from pydantic import BaseModel
from typing import List, Dict, Any, Optional, TypedDict

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

# 用于 LangGraph/流程状态的类型定义
class ESGAnalysisState(TypedDict):
    company_name: str
    vector_store: Any
    detected_language: str
    original_text: str
    translated_text: str
    initial_thoughts: List[str]
    selected_thoughts: List[str]
    document_analysis: str
    news_validation: str
    metrics: str
    final_synthesis: str
    iteration: int
    max_iterations: int
    error: Optional[str] 
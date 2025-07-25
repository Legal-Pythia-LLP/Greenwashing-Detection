from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel

# ESG 分析的返回结果结构
class ESGAnalysisResult(BaseModel):
    greenwashing_score: float
    confidence: float
    reasoning: str
    evidence: List[str]
    metrics: Dict[str, Any]

# LangGraph State Definition
class ESGAnalysisState(TypedDict):
    company_name: str
    vector_store: Any
    initial_thoughts: List[str]
    selected_thoughts: List[str]
    document_analysis: str
    news_validation: str
    metrics: str
    final_synthesis: str
    iteration: int
    max_iterations: int
    error: Optional[str] 
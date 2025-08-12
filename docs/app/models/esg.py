from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel

# ESG 分析的返回结果结构
class ESGAnalysisResult(BaseModel):
    greenwashing_score: float
    confidence: float
    reasoning: str
    evidence: List[str]
    metrics: Dict[str, Any]

class WikirateValidationResult(BaseModel):
    company_found: bool
    metrics_verified: Dict[str, Any]
    discrepancies: List[str]
    verification_score: float

# LangGraph State Definition
class ESGAnalysisState(TypedDict):
    company_name: str
    vector_store: Any
    output_language: str
    initial_thoughts: List[str]
    selected_thoughts: List[str]
    document_analysis: List[str]
    quotations: List[Dict[str, Any]]  # ✅ 加这一行
    tool_plan: List[Dict[str, Any]]   # ✅ 如果你要传 tool 决策
    validations: List[Dict[str, Any]] # ✅ 如果你有验证逻辑
    news_validation: str
    wikirate_validation: str
    metrics: str
    final_synthesis: str
    iteration: int
    max_iterations: int
    error: Optional[str]
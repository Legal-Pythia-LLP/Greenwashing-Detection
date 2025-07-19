from pydantic import BaseModel
from typing import List, Dict, Any, Optional, TypedDict

class ChatBaseMessage(BaseModel):
    """
    聊天消息基础模型，包含消息内容和会话ID。
    """
    message: str
    session_id: str

class ESGAnalysisResult(BaseModel):
    """
    ESG分析结果模型，包含分数、置信度、推理、证据、指标和检测语言。
    """
    greenwashing_score: float
    confidence: float
    reasoning: str
    evidence: List[str]
    metrics: Dict[str, Any]
    detected_language: str

# 用于 LangGraph/流程状态的类型定义
class ESGAnalysisState(TypedDict):
    """
    ESG分析流程状态，支持多节点自动推理。
    """
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
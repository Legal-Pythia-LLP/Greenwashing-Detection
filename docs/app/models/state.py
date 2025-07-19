from typing import TypedDict, Any, List, Optional, Dict

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
from pydantic import BaseModel
from typing import List

class OCRAnalysisResponse(BaseModel):
    text: str                   # 提取出来的原始文字
    highlights: List[str]       # 模糊用语高亮
    comment: str                # LLM 分析说明

class OCRResponse(BaseModel):
    text: str

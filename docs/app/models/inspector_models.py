from pydantic import BaseModel
from typing import List, Literal

class InspectResponse(BaseModel):
    file_type: Literal["image","pdf","other"]
    text: str
    highlights: List[str]
    comment: str

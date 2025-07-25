from pydantic import BaseModel

# 定义用户与系统对话的基础结构
class ChatBaseMessage(BaseModel):
    message: str
    session_id: str 
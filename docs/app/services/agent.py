from app.services.memory import memories
from app.config import SUPPORTED_LANGUAGES

def create_multilingual_esg_agent(session_id: str, vector_store, language: str):
    # 这里只做结构迁移，实际应初始化 agent
    return None  # 占位，实际应返回 AgentExecutor 
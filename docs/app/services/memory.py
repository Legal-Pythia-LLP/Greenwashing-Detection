# 全局内存管理，用于存储会话级向量库、Agent和对话历史

# 存储所有会话的向量库
document_stores = {}
# 存储所有会话的Agent实例
agent_executors = {}
# 存储所有会话的对话历史
memories = {}

def get_document_store(session_id: str):
    """根据 session_id 获取对应的向量库"""
    return document_stores.get(session_id)

def set_document_store(session_id: str, store):
    """设置/更新 session_id 对应的向量库"""
    document_stores[session_id] = store

def get_agent_executor(session_id: str):
    """根据 session_id 获取对应的 Agent 实例"""
    return agent_executors.get(session_id)

def set_agent_executor(session_id: str, agent):
    """设置/更新 session_id 对应的 Agent 实例"""
    agent_executors[session_id] = agent

def get_memory(session_id: str):
    """根据 session_id 获取对应的对话历史"""
    return memories.get(session_id)

def set_memory(session_id: str, memory):
    """设置/更新 session_id 对应的对话历史"""
    memories[session_id] = memory 
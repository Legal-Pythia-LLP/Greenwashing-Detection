# 全局内存管理，用于存储会话级向量库、Agent和对话历史

document_stores = {}
agent_executors = {}
memories = {}

def get_document_store(session_id: str):
    return document_stores.get(session_id)

def set_document_store(session_id: str, store):
    document_stores[session_id] = store

def get_agent_executor(session_id: str):
    return agent_executors.get(session_id)

def set_agent_executor(session_id: str, agent):
    agent_executors[session_id] = agent

def get_memory(session_id: str):
    return memories.get(session_id)

def set_memory(session_id: str, memory):
    memories[session_id] = memory 
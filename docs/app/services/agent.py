from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain.memory import ConversationBufferWindowMemory
from app.config import SUPPORTED_LANGUAGES
from app.services.esg_analysis import (
    MultilingualESGDocumentAnalysisTool,
    MultilingualNewsValidationTool,
    MultilingualESGMetricsCalculatorTool,
)
from app.utils.language import detect_language, is_esg_related_multilingual
from app.utils.translation import translate_text
from typing import Any


def create_multilingual_esg_agent(session_id: str, vector_store: Any, language: str, llm: Any) -> Any:
    """
    创建多语言ReAct Agent，集成ESG分析工具。
    支持多语言文档分析、新闻验证、指标计算、ESG相关性判别、语言检测、翻译等。
    """
    tools = [
        MultilingualESGDocumentAnalysisTool(vector_store, language, llm),
        MultilingualNewsValidationTool("", language, llm),
        MultilingualESGMetricsCalculatorTool(language, llm),
        Tool(
            name="multilingual_esg_classifier",
            description=f"Classifies text as ESG-related or not in {SUPPORTED_LANGUAGES[language]}",
            func=lambda text: str(is_esg_related_multilingual(text, language))
        ),
        Tool(
            name="language_detector",
            description="Detects the language of the input text",
            func=lambda text: f"Detected language: {detect_language(text)} ({SUPPORTED_LANGUAGES.get(detect_language(text), 'Unknown')})"
        ),
        Tool(
            name="text_translator",
            description="Translates text between supported languages",
            func=lambda text_and_lang: translate_text(
                text_and_lang.split('|')[0],
                text_and_lang.split('|')[1] if '|' in text_and_lang else 'en'
            )
        )
    ]
    # 对话历史内存
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=10,
        return_messages=True
    )
    # 系统消息模板
    system_messages = {
        'en': "You are an expert ESG analyst specialized in identifying greenwashing. Respond in English.",
        'de': "Sie sind ein ESG-Experte, spezialisiert auf die Identifizierung von Greenwashing. Antworten Sie auf Deutsch.",
        'it': "Sei un esperto ESG specializzato nell'identificazione del greenwashing. Rispondi in italiano."
    }
    system_message = system_messages.get(language, system_messages['en'])
    agent_prompt = f"""
    {system_message}
    You have access to multilingual ESG analysis tools. Use them to:
    1. Analyze ESG documents for greenwashing indicators
    2. Validate claims against news sources
    3. Calculate greenwashing metrics
    4. Classify ESG-related content
    5. Detect languages and translate when needed
    Always consider cultural and linguistic nuances when analyzing documents in different languages.
    Pay attention to language-specific greenwashing indicators and terminology.
    Current analysis language: {SUPPORTED_LANGUAGES[language]}
    """
    # 初始化多语言Agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        max_iterations=15,
        early_stopping_method="force",
        agent_kwargs={"system_message": agent_prompt}
    )
    return agent 
from langchain.schema import HumanMessage
from app.core.llm import llm  # 你们组已有模块

def analyse_ocr_text(text: str) -> dict:
    prompt = f"""
You are an assistant that detects vague or greenwashing claims in marketing or product descriptions.

Given the following text, identify any phrases that may be vague or suggest greenwashing. Return JSON like:

{{
  "highlights": ["example phrase", "another example"],
  "comment": "Explain why they are potentially misleading."
}}

Text:
\"\"\"{text}\"\"\"
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        return eval(response.content)  # 暂用 eval，后续可改 json.loads
    except:
        return {"highlights": [], "comment": "LLM failed to parse."}

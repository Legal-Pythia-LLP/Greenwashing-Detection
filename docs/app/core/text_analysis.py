from langchain.schema import HumanMessage
from app.core.llm import llm
from app.core.rules_engine import RuleEngine
import json

_engine = RuleEngine()

def analyse_text(text: str, mode: str = "llm") -> dict:
    text = text or ""
    if mode == "rules":
        return _engine.analyze(text)

    llm_res = _analyse_with_llm(text)

    if mode == "hybrid":
        rule_res = _engine.analyze(text)
        highlights = list(dict.fromkeys(
            [*rule_res.get("highlights", []), *llm_res.get("highlights", [])]
        ))
        comment = f"[Rules] {rule_res.get('comment','')} [LLM] {llm_res.get('comment','')}"
        return {"highlights": highlights, "comment": comment}

    return llm_res

def _analyse_with_llm(text: str) -> dict:
    prompt = f"""
You are an assistant that detects vague or greenwashing claims in ESG/financial reports.
Return ONLY valid JSON like: {{"highlights": ["..."], "comment": "..."}}

Text:
\"\"\"{text}\"\"\"
"""
    resp = llm.invoke([HumanMessage(content=prompt)])
    try:
        return json.loads(resp.content)
    except Exception:
        return {"highlights": [], "comment": "LLM failed to produce valid JSON."}

import json, re, ast
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import llm

def analyse_ocr_text(text: str) -> dict:
    sys = SystemMessage(content='Return ONLY a JSON object with keys exactly: "highlights" (array of strings) and "comment" (string). No extra text.')
    user = HumanMessage(content=f'Detect vague/greenwashing phrases.\n\nText:\n"""{text}"""')

    resp = llm.invoke([sys, user])
    s = resp.content.strip()

    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        return {"highlights": [], "comment": "Model returned no JSON."}
    payload = m.group(0)

    try:
        data = json.loads(payload)  # 优先严格 JSON
    except json.JSONDecodeError:
        try:
            data = ast.literal_eval(payload)  # 兜底解析 Python 风格字典
        except Exception:
            return {"highlights": [], "comment": "Model returned non-JSON."}

    h = data.get("highlights")
    c = data.get("comment")
    return {
        "highlights": h if isinstance(h, list) else [],
        "comment": c if isinstance(c, str) else ""
    }

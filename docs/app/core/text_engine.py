import json, re, hashlib, math
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import llm
from app.core.rules_engine import RuleEngine

_engine = RuleEngine()
_JSON = re.compile(r"\{.*\}", re.S)
_cache = {}

CHUNK_CHARS = 4000
CHUNK_OVERLAP = 400

def _clean(s: str) -> str:
    return " ".join((s or "").split())

def _chunks(s: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP):
    n = len(s)
    if n <= size:
        yield s
        return
    step = max(1, size - overlap)
    for start in range(0, n, step):
        yield s[start:start+size]

def _parse_json(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return {"highlights": [], "comment": "Model returned non-JSON."}

def _llm_one(text: str) -> dict:
    key = hashlib.sha1(text.encode("utf-8")).hexdigest()
    if key in _cache:
        return _cache[key]
    sys = SystemMessage(content='Return only a JSON object with keys "highlights" (array of strings) and "comment" (string).')
    user = HumanMessage(content=f'Detect vague or greenwashing claims.\n\nText:\n"""{text}"""')
    resp = llm.invoke([sys, user])
    m = _JSON.search(resp.content or "")
    data = {"highlights": [], "comment": "Model returned no JSON."} if not m else _parse_json(m.group(0))
    _cache[key] = data
    return data

def _llm_all(text: str) -> dict:
    hs, comments = [], []
    parts = list(_chunks(text))
    for part in parts:
        r = _llm_one(part)
        comments.append(r.get("comment", ""))
        hs.extend(r.get("highlights", []))
    seen, merged = set(), []
    for h in hs:
        k = " ".join(str(h).split()).lower()
        if k and k not in seen:
            seen.add(k); merged.append(h)
    return {"highlights": merged, "comment": f"Analyzed {len(parts)} chunk(s). " + " | ".join([c for c in comments if c])}

def analyse_text(text: str, mode: str = "llm") -> dict:
    text = _clean(text)
    if mode == "rules":
        return _engine.analyze(text)
    llm_res = _llm_all(text)
    if mode == "hybrid":
        rule_res = _engine.analyze(text)
        seen, hs = set(), []
        for h in [*rule_res.get("highlights", []), *llm_res.get("highlights", [])]:
            k = " ".join(str(h).split()).lower()
            if k and k not in seen:
                seen.add(k); hs.append(h)
        return {"highlights": hs, "comment": f'[Rules] {rule_res.get("comment","")} [LLM] {llm_res.get("comment","")}'}
    return llm_res

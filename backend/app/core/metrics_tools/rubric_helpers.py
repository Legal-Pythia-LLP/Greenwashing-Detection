"""
Helpers for rubric-driven LLM scoring:
- Build rubric instructions
- Call LLM
- Parse/repair JSON
- Enforce schema (clamp & defaults)
- Add legacy compatibility fields
"""

from app.core.llm import llm
from langchain.schema import HumanMessage
import json, re

def build_llm_rubric(evidence: dict) -> str:
    """
    Build a strict scoring instruction (rubric) for the LLM.
    The model must score ONLY based on evidence.hits.
    """
    return f"""
You are an ESG rater. Score ONLY based on RULE_HITS_JSON below. Do not invent facts.
If there is no evidence for a dimension, score 0 for that dimension.

RULE_HITS_JSON:
{json.dumps(evidence, ensure_ascii=False)}

Scoring rubric (0–100 per dimension; 0–10 overall), keys:
- "vague": higher if multiple vague/hedging claims; lower if concrete KPI/year/baseline near claims.
- "lack_metrics": higher if targets lack year/baseline/absolute/coverage; lower if SMART-like targets.
- "misleading": higher if scope-2 basis not specified (market/location), REC quality/retire missing, avoided/enabled not separately disclosed.
- "cherry": higher if only scope1/2 are disclosed, missing scope3, comparisons with no baseline, selected geographies only.
- "no_3rd": higher if "carbon neutral via offsets" with no PAS2060/Verra/Gold Standard/ICROA/ISAE3000/AA1000; lower if present.

Output STRICT JSON ONLY (no markdown, no prose). Schema:
{{
  "radar": {{"vague": 0, "lack_metrics": 0, "misleading": 0, "cherry": 0, "no_3rd": 0}},
  "overall": 0.0,
  "confidence": "low" | "medium" | "high",
  "rationale": {{
    "vague":"...", "lack_metrics":"...", "misleading":"...", "cherry":"...", "no_3rd":"..."
  }}
}}

Rules:
- radar values must be integers 0–100; overall float 0.0–10.0.
- confidence must be one of low/medium/high.
- Rationale must cite which hits (quotes or phrases) triggered the score.
- If evidence is empty, return all zeros and confidence "low".
    """.strip()

def llm_invoke(content: str) -> str:
    """Invoke the LLM and return raw text."""
    resp = llm.invoke([HumanMessage(content=content)])
    return (resp.content or "").strip()

def parse_json_strict(text: str) -> dict | None:
    """
    Remove common code fences; parse JSON; best-effort brace extraction if needed.
    """
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(json)?", "", t, flags=re.IGNORECASE).strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None

def ensure_schema(metrics: dict) -> dict:
    """
    Enforce keys, types, and ranges (clamp).
    Always returns a dict with radar/overall/confidence/rationale/evidence/engine.
    """
    if not isinstance(metrics, dict):
        metrics = {}
    # Radar
    radar = metrics.get("radar")
    if not isinstance(radar, dict):
        radar = {}
    keys = ["vague", "lack_metrics", "misleading", "cherry", "no_3rd"]
    clean_radar = {}
    for k in keys:
        v = radar.get(k, 0)
        try:
            v = int(round(float(v)))
        except Exception:
            v = 0
        clean_radar[k] = max(0, min(100, v))
    metrics["radar"] = clean_radar
    # Overall
    try:
        ov = float(metrics.get("overall", 0.0))
    except Exception:
        ov = 0.0
    metrics["overall"] = max(0.0, min(10.0, ov))
    # Confidence
    conf = str(metrics.get("confidence", "low")).lower()
    metrics["confidence"] = conf if conf in ("low", "medium", "high") else "low"
    # Rationale
    rat = metrics.get("rationale")
    if not isinstance(rat, dict):
        rat = {}
    for k in keys:
        if k not in rat or not isinstance(rat[k], str):
            rat[k] = ""
    metrics["rationale"] = rat
    # Evidence holder
    if "evidence" not in metrics or not isinstance(metrics["evidence"], dict):
        metrics["evidence"] = {"hits": []}
    # Engine tag default
    if "engine" not in metrics:
        metrics["engine"] = "llm-rubric"
    return metrics

def ensure_backward_compat(metrics: dict) -> None:
    """
    Add legacy fields expected by existing frontend:
      - breakdown[] (0–100 per dimension)
      - overall_greenwashing_score.score (0–10)
    """
    radar = metrics.get("radar", {})
    if "breakdown" not in metrics:
        metrics["breakdown"] = [
            {"type": "Vague or unsubstantiated claims", "value": float(radar.get("vague", 0))},
            {"type": "Lack of specific metrics or targets", "value": float(radar.get("lack_metrics", 0))},
            {"type": "Misleading terminology", "value": float(radar.get("misleading", 0))},
            {"type": "Cherry-picked data", "value": float(radar.get("cherry", 0))},
            {"type": "Absence of third-party verification", "value": float(radar.get("no_3rd", 0))},
        ]
    ogs = metrics.get("overall_greenwashing_score")
    if not (isinstance(ogs, dict) and isinstance(ogs.get("score"), (int, float))):
        metrics["overall_greenwashing_score"] = {"score": float(metrics.get("overall") or 0.0)}

def empty_metrics(engine: str = "none", error: str | None = None) -> dict:
    """
    Return safe empty metrics with legacy fields.
    """
    m = {
        "radar": {"vague":0,"lack_metrics":0,"misleading":0,"cherry":0,"no_3rd":0},
        "overall": 0.0,
        "confidence": "low",
        "evidence": {"hits": []},
        "engine": engine
    }
    if error:
        m["error"] = error
    ensure_backward_compat(m)
    return m

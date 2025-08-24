"""
New tool: rules annotate -> LLM rubric scoring.
Does NOT modify legacy ESGMetricsCalculatorTool.
"""

from app.core import rules_engine
from .rubric_helpers import (
    build_llm_rubric, llm_invoke, parse_json_strict,
    ensure_schema, ensure_backward_compat, empty_metrics
)
import json

class LLMRubricScoringTool:
    name = "esg_metrics_calculator_rules_llm"
    description = "Calculate greenwashing metrics via rules evidence + LLM rubric scoring."

    def _run(self, text: str) -> str:
        try:
            # 1) Run rule scan to collect evidence
            print(f"[LLM-RUBRIC] scanning text len={len(text)}")
            try:
                scan = rules_engine.scan(text=text, company=None) or {}
            except Exception as se:
                print(f"[LLM-RUBRIC] rules scan failed: {se}")
                scan = {}
            hits = scan.get("hits", [])
            print(f"[LLM-RUBRIC] hits={len(hits)}")
            evidence = {"hits": hits[:200]} if isinstance(hits, list) else {"hits": []}

            # 2) Build rubric prompt -> first LLM call
            prompt = build_llm_rubric(evidence)
            raw1 = llm_invoke(prompt)
            print("[LLM-RUBRIC RAW1]", (raw1 or "")[:500])
            data = parse_json_strict(raw1)

            # 2b) If parsing failed -> retry with stricter prompt
            if data is None:
                strict_header = (
                    "Return STRICT JSON ONLY, no prose, no markdown, no code fences.\n"
                    'Schema: {"radar":{"vague":0,"lack_metrics":0,"misleading":0,"cherry":0,"no_3rd":0},'
                    '"overall":0.0,"confidence":"low",'
                    '"rationale":{"vague":"","lack_metrics":"","misleading":"","cherry":"","no_3rd":""}}\n\n'
                )
                raw2 = llm_invoke(strict_header + prompt)
                print("[LLM-RUBRIC RAW2]", (raw2 or "")[:500])
                data = parse_json_strict(raw2)

            # 3) Normalize output and attach evidence/engine (fallback if still None)
            metrics = ensure_schema(data or {})
            metrics["evidence"] = evidence
            
            metrics["engine"] = (metrics.get("engine", "") + "|rules-v1|llm-rubric").strip("|")

            # 4) Add backward compatibility fields for frontend
            ensure_backward_compat(metrics)

            return json.dumps(metrics, ensure_ascii=False)

        except Exception as e:
            # Any error -> return safe empty metrics to avoid crash
            print(f"[LLM-RUBRIC] error: {e}")
            return json.dumps(empty_metrics(engine="error", error=str(e)), ensure_ascii=False)

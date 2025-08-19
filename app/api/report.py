from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import json
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.report import Report

router = APIRouter()


def _to_percentage(x: Any) -> float:
    try:
        val = float(x)
        # Compatible with 0-10 or 0-100 scale
        return val * 10 if val <= 10 else val
    except Exception:
        return 0.0


def _transform(session_data: Dict[str, Any]) -> Dict[str, Any]:
    company_name = session_data.get("company_name") or "Unknown Company"
    metrics = session_data.get("graphdata") or session_data.get("metrics") or {}

    overall = 0.0
    breakdown: List[Dict[str, Any]] = []

    # Try to parse metrics structure
    if isinstance(metrics, str):
        try:
            import json
            metrics = json.loads(metrics)
        except:
            metrics = {}
    
    if isinstance(metrics, dict):
        for k, v in metrics.items():
            if k == "overall_greenwashing_score":
                score = v.get("score") if isinstance(v, dict) else v
                overall = _to_percentage(score)
            else:
                score = v.get("score") if isinstance(v, dict) else v
                type_i18n = v.get("type_i18n") if isinstance(v, dict) else None

                breakdown.append({
                    "type": k.replace("_", " "),
                    "type_i18n": type_i18n or {
                        "en": k.replace("_", " "),
                        "de": k.replace("_", " "),
                        "it": k.replace("_", " "),
                    },
                    "value": _to_percentage(score)
                })

    # Evidence and external information
    validations = session_data.get("validations") or []
    quotations = session_data.get("quotations") or []

    evidence_groups: Dict[str, List[Dict[str, str]]] = {}

    for q in quotations if isinstance(quotations, list) else []:
        q_text = q.get("quotation") or ""
        why = q.get("explanation") or ""
        cat = "Key statements"
        evidence_groups.setdefault(cat, []).append({"quote": q_text, "why": why})

    for v in validations if isinstance(validations, list) else []:
        q = v.get("quotation", {})
        q_text = (q.get("quotation") if isinstance(q, dict) else None) or ""
        news = v.get("validation", {}).get("news")
        wiki = v.get("validation", {}).get("wikirate")
        why_parts = []
        if news:
            why_parts.append(f"News: {str(news)[:200]}")
        if wiki:
            why_parts.append(f"Wikirate: {str(wiki)[:200]}")
        if q_text or why_parts:
            evidence_groups.setdefault("External validation highlights", []).append({
                "quote": q_text,
                "why": " | ".join(why_parts)
            })

    evidence = [
        {"type": k, "items": v} for k, v in evidence_groups.items()
    ]

    summary_src = session_data.get("final_synthesis") or session_data.get("response") or ""
    summary = summary_src.strip().split("\n\n")[0][:200] if isinstance(summary_src, str) else ""

    external: List[str] = []
    nv = session_data.get("news_validation")
    if isinstance(nv, str) and nv.strip():
        external.append(nv.strip()[:140])
    wv = session_data.get("wikirate_validation")
    if isinstance(wv, str) and wv.strip():
        external.append(wv.strip()[:140])

    return {
        "session_id": session_data.get("session_id"),
        "company_name": company_name,
        "overall_score": round(overall, 1),
        "summary": summary,
        "breakdown": breakdown[:8],
        "evidence": evidence,
        "final_synthesis": session_data.get("final_synthesis") or "",
        "external": external,
    }



@router.get("/report/{session_id}")
async def get_report(session_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    report = db.query(Report).filter(Report.session_id == session_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Session not found")
    
    metrics = json.loads(report.metrics) if report.metrics else {}
    i18n = {}
    try:
        if report.analysis_summary_i18n:
            i18n = json.loads(report.analysis_summary_i18n)
    except Exception:
        i18n = {}

    default_final = report.analysis_summary or i18n.get("en") or i18n.get("de") or i18n.get("it") or ""

    data = {
        "session_id": session_id,
        "company_name": report.company_name,
        "graphdata": metrics,
        "metrics": metrics,
        "final_synthesis": default_final,
        "final_synthesis_i18n": i18n,
        "validations": [],
        "quotations": []
    }
    
    return {"ok": True, "data": _transform(data) | {
        "final_synthesis_i18n": i18n
    }}


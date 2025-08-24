from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from typing import Annotated, Dict, Any, Optional
from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime  #  for session_data timestamp
from app.core.store import session_store, save_session
from app.core.esg_analysis import agent_executors

# Global dictionary to store analysis results
analysis_results_by_session = defaultdict(dict)

from app.core.utils import hash_file, translate_text
from app.core.document import process_pdf_document, process_ocr_text
from app.core.vector_store import embedding_model
from app.config import REPORT_DIR, VALID_UPLOAD_TYPES, VALID_COMPANIES, VECTOR_STORE_DIR
from app.core.llm import llm
from app.core.company import extract_company_info
from app.models import ChatBaseMessage
from app.core.esg_analysis import comprehensive_esg_analysis, document_stores
from app.models.report import Report, ReportFile
from app.db import get_db
from sqlalchemy.orm import Session
from langchain.schema import HumanMessage
import uuid
from PyPDF2 import PdfReader
from langdetect import detect, DetectorFactory
from PIL import Image
import io
from app.core.ocr_service import ocr_service
from langchain_community.vectorstores import Chroma
from app.core.metrics_tools.schema_utils import (
    ensure_unified_metrics_schema as _ensure_unified_metrics_schema,
)

IMAGE_UPLOAD_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff", "image/bmp"
}

def _get_main_risk_type(analysis_results: Dict[str, Any]) -> str:
    """Extract main risk type from analysis results"""
    breakdown = analysis_results.get("metrics", {}).get("breakdown", [])
    if not breakdown:
        return "Unknown type"
    max_score = 0.0
    main_type = "Unknown type"
    for item in breakdown:
        score = item.get("value", 0)
        try:
            score = float(score)
        except Exception:
            score = 0.0
        if score > max_score:
            max_score = score
            main_type = item.get("type", "Unknown type")
    return main_type

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    session_id: Optional[str] = Form(None),
    overrided_language: Optional[str] = Form(None),
    force_new: Optional[bool] = Form(False),  # re-analysis flag
    rules_mode: Optional[str] = Form(None),   #  rules switch: legacy | rules_llm
    db: Session = Depends(get_db)
) -> Dict[str, Any]:

    # --- normalize rules_mode ---
    mode = (rules_mode or "").lower().strip()
    if mode not in ("legacy", "rules_llm"):
        mode = "legacy"
    print(f"[UPLOAD] received rules_mode={rules_mode} -> using mode={mode}")

    DetectorFactory.seed = 0  # Ensure consistent lang-detect
    detected_language = "unknown"

    # session id
    if not session_id:
        session_id = f"s_{uuid.uuid4().hex[:16]}"
        print(f"[SESSION DEBUG] Generated new session ID: {session_id}")

    # --- Content-Type whitelist ---
    if (file.content_type not in VALID_UPLOAD_TYPES) and (file.content_type not in IMAGE_UPLOAD_TYPES):
        print(f"[DEBUG] Rejected content-type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Invalid content type")

    # --- Read once ---
    file_b = await file.read()
    if len(file_b) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    lower_name = file.filename.lower()
    is_pdf = lower_name.endswith(".pdf")
    is_image = lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"))
    if not (is_pdf or is_image):
        raise HTTPException(status_code=400, detail="Invalid filename. Must be a PDF or image file")

    # --- Paths / filenames ---
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    import re
    original_name = Path(file.filename).stem
    safe_name = re.sub(r"[^\w\-_]", "_", original_name)
    analysis_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = Path(file.filename).suffix.lower()
    file_path = REPORT_DIR / f"{safe_name}_{analysis_time}{suffix}"

    # --- Persist upload & build vector store ---
    try:
        with file_path.open("wb") as f:
            f.write(file_b)

        if is_image:
            # OCR branch
            ocr_out = ocr_service.read(str(file_path), mode="smart")
            ocr_text = (ocr_out.get("cleaned_text") or ocr_out.get("full_text") or "").strip()
            if not ocr_text:
                raise HTTPException(status_code=400, detail="The uploaded image contains no recognizable text for analysis.")
            try:
                detected_language = detect(ocr_text[:2000]) if ocr_text else "unknown"
            except Exception:
                detected_language = "unknown"

            # Vector store from OCR text (persisted)
            persist_path = VECTOR_STORE_DIR / session_id
            vector_store = Chroma.from_texts(
                [ocr_text],
                embedding=embedding_model,
                metadatas=[{"source": "image_ocr"}],
                collection_name=f"img_{session_id[:8]}",
                persist_directory=str(persist_path)
            )
        else:
            # PDF branch
            # Detect language (sample)
            sample_text = ""
            try:
                reader = PdfReader(str(file_path))
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        sample_text += text
                    if len(sample_text) > 1000:
                        break
                detected_language = detect(sample_text[:2000]) if sample_text.strip() else "unknown"
            except Exception as e:
                print(f"[Warning] Language detection failed: {e}")
                detected_language = "unknown"

            # Chunk PDF & persist
            chunks = await process_pdf_document(str(file_path))
            persist_path = VECTOR_STORE_DIR / session_id
            vector_store = Chroma.from_documents(
                chunks,
                embedding_model,
                persist_directory=str(persist_path)
            )

        # keep vector store in memory, and on disk
        from app.core.store import save_vector_store
        save_vector_store(session_id, vector_store)
        document_stores[session_id] = vector_store

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Vector store stage failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vector store creation failed: {e}")

    # --- DB bookkeeping with file hash ---
    file_hash = hash_file(file_b)
    report_file = db.query(ReportFile).filter_by(file_hash=file_hash).first()
    if not report_file:
        report_file = ReportFile(
            file_hash=file_hash,
            file_path=str(file_path),
            original_filename=file_path.name
        )
        db.add(report_file)
        db.commit()
        db.refresh(report_file)
    elif force_new:
        report_file.file_path = str(file_path)
        report_file.original_filename = file_path.name
        db.commit()
        db.refresh(report_file)

    # Dedupe (unless force_new)
    if not force_new:
        latest_report = db.query(Report).filter_by(file_id=report_file.id).order_by(Report.analysis_time.desc()).first()
        if latest_report:
            # reuse old analysis; delete newly uploaded file to save space
            file_path.unlink(missing_ok=True)
            return {
                "filename": report_file.original_filename,
                "company_name": latest_report.company_name,
                "session_id": latest_report.session_id,
                "response": latest_report.analysis_summary,
                "metrics": json.loads(latest_report.metrics),
                "status": "duplicate",
                "previous_result": {
                    "response": latest_report.analysis_summary,
                    "metrics": json.loads(latest_report.metrics)
                }
            }

    try:
        # --- Company extraction via retrieval ---
        company_query = "What is the name of the company that published this report?"
        company_docs = vector_store.similarity_search(company_query, k=3)
        company_context = "\n".join([getattr(doc, "page_content", "") for doc in company_docs])
        company_prompt = (
            f"Extract the company name from this context:\n{company_context}\n\n"
            f"Return only the company name, nothing else."
        )
        company_response = llm.invoke([HumanMessage(content=company_prompt)])
        company_name = (company_response.content or "").strip() or "Unknown Company"

        # --- ESG analysis (with rules_mode) ---
        print(f"[INFO] Starting ESG analysis for company: {company_name}")
        analysis_result = await comprehensive_esg_analysis(
            session_id=session_id,
            vector_store=vector_store,
            company_name=company_name,
            output_language=overrided_language or "en",
            rules_mode=mode,  #  pass-through
        )
        print(f"[INFO] ESG analysis completed")

        if analysis_result.get("error"):
            raise Exception(analysis_result["error"])

        # --- Metrics: robust coercion + schema unify ---
        raw_metrics = analysis_result.get("metrics", {})
        if isinstance(raw_metrics, str):
            try:
                metrics_parsed = json.loads(raw_metrics)
            except Exception:
                metrics_parsed = {}
        elif isinstance(raw_metrics, dict):
            metrics_parsed = raw_metrics
        else:
            metrics_parsed = {}
        metrics_parsed = _ensure_unified_metrics_schema(metrics_parsed)

        # overall for DB (0–100). If 'overall' is 0–10 scale, multiply by 10.
        overall_0_10 = 0.0
        if isinstance(metrics_parsed.get("overall"), (int, float)):
            overall_0_10 = float(metrics_parsed["overall"])
        else:
            ogs = metrics_parsed.get("overall_greenwashing_score", {})
            if isinstance(ogs, dict) and isinstance(ogs.get("score"), (int, float)):
                overall_0_10 = float(ogs["score"])  # sometimes legacy 0–1
        overall_for_report = overall_0_10 * (10 if overall_0_10 <= 1.0 else 10.0)  # normalize to 0–100

        # --- i18n final synthesis ---
        final_synthesis_en = analysis_result.get("final_synthesis", "")
        final_synthesis_de = await translate_text(final_synthesis_en, "German")
        final_synthesis_it = await translate_text(final_synthesis_en, "Italian")
        finals_by_lang = {"en": final_synthesis_en, "de": final_synthesis_de, "it": final_synthesis_it}

        # --- Persist report ---
        report = Report(
            session_id=session_id,
            company_name=company_name,
            overall_score=overall_for_report,
            risk_type=_get_main_risk_type({"metrics": metrics_parsed}),
            metrics=json.dumps(metrics_parsed, ensure_ascii=False),
            analysis_summary=final_synthesis_en,
            analysis_summary_i18n=json.dumps(finals_by_lang, ensure_ascii=False),
            file_id=report_file.id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # --- Response payload ---
        result = {
            "filename": file_path.name,
            "company_name": company_name,
            "session_id": session_id,
            "response": final_synthesis_en,
            "initial_analysis": analysis_result.get("initial_analysis"),
            "document_analysis": analysis_result.get("document_analysis"),
            "news_validation": analysis_result.get("news_validation"),
            "wikirate_validation": analysis_result.get("wikirate_validation"),
            "graphdata": metrics_parsed,
            "metrics": metrics_parsed,
            "mode_used": mode,                      #  echo rules mode
            "rules_mode": mode,                     #  echo rules mode
            "comprehensive_analysis": analysis_result.get("comprehensive_analysis"),
            "tool_plan": analysis_result.get("tool_plan"),
            "validations": analysis_result.get("validations"),
            "quotations": analysis_result.get("quotations"),
            "final_synthesis": final_synthesis_en,
            "final_synthesis_i18n": finals_by_lang,
            "validation_complete": True,
            "filenames": ["bbc_articles", "cnn_articles"] if company_name.lower() in VALID_COMPANIES else None,
            "workflow_error": analysis_result.get("error"),
            "detected_language": detected_language,
            "overrided_language": overrided_language or "en",
        }

        # --- Store in-memory for quick fetch ---
        analysis_results_by_session[session_id] = result
        print(f"[INFO] metrics.engine: {metrics_parsed.get('engine')}")
        print(f"[INFO] Analysis results stored for session {session_id}")

        # --- Save session (persist) ---
        session_data = {
            "company_name": company_name,
            "analysis_results": result,
            "agent_executor": True,
            "vector_store_path": str(persist_path),
            "created_at": datetime.now().timestamp()
        }
        print(f"[DEBUG] Saving session data with keys: {list(session_data.keys())}")
        save_session(session_id, session_data, db)
        print(f"[INFO] Session {session_id} saved to persistent storage")

        # --- Register agent executor ---
        print(f"[AGENT DEBUG] Creating agent for session: {session_id}")
        from app.core.esg_analysis import create_esg_agent
        agent = create_esg_agent(session_id, vector_store, company_name)
        agent_executors[session_id] = agent
        print(f"[AGENT DEBUG] Agent created and registered for session: {session_id}")
        print(f"[AGENT DEBUG] Current active agents: {list(agent_executors.keys())}")

        return result

    except Exception as e:
        # Cleanup on failure
        file_path.unlink(missing_ok=True)
        # Clean up agent if created
        try:
            if session_id in agent_executors:
                print(f"[AGENT DEBUG] Cleaning up agent for failed session: {session_id}")
                del agent_executors[session_id]
        except NameError:
            pass
        db.rollback()

        error_detail = str(e)
        if "invalid pdf header" in error_detail.lower():
            error_detail = "Invalid PDF file format, please ensure you upload a valid PDF document"
        elif "eof marker not found" in error_detail.lower():
            error_detail = "PDF file is corrupted or incomplete, please re-upload"
        elif "language detection failed" in error_detail.lower():
            error_detail = "Unable to detect document language, please check document content"

        print(f"[ERROR] Upload processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {error_detail}")

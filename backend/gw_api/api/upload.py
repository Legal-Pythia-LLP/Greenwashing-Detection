from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from typing import Annotated, Dict, Any, Optional
from pathlib import Path
import json
from collections import defaultdict
from gw_api.core.store import session_store, save_session
from gw_api.core.esg_analysis import agent_executors
from gw_api.core.utils import hash_file, translate_text
from gw_api.core.document import process_pdf_document, process_ocr_text
from gw_api.core.vector_store import embedding_model
from gw_api.config import UPLOAD_DIR, REPORT_DIR, VALID_UPLOAD_TYPES, VALID_COMPANIES
from gw_api.core.llm import llm
from gw_api.core.company import extract_company_info
from gw_api.models import ChatBaseMessage
from gw_api.core.esg_analysis import comprehensive_esg_analysis, document_stores
from gw_api.models.report import Report, ReportFile
from gw_api.db import get_db
from sqlalchemy.orm import Session
from langchain.schema import HumanMessage
import uuid
from PyPDF2 import PdfReader
from langdetect import detect, DetectorFactory
from PIL import Image
import io
from gw_api.core.ocr_service import ocr_service
from langchain_community.vectorstores import Chroma

IMAGE_UPLOAD_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
    "image/bmp",
}

analysis_results_by_session = defaultdict(dict)

def _get_main_risk_type(analysis_results: Dict[str, Any]) -> str:
    """Extract main risk type from analysis results"""
    breakdown = analysis_results.get("metrics", {}).get("breakdown", [])
    if not breakdown:
        return "Unknown type"

    # Find the highest scoring type
    max_score = 0
    main_type = "Unknown type"
    for item in breakdown:
        score = item.get("value", 0)
        if isinstance(score, str):
            try:
                score = float(score)
            except:
                score = 0
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
    force_new: Optional[bool] = Form(False),  # New flag to force re-analysis
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    DetectorFactory.seed = 0  # Ensure consistent language detection results

    # ✅ If no session_id provided, generate a new one
    if not session_id:
        session_id = f"s_{uuid.uuid4().hex[:16]}"
        print(f"[SESSION DEBUG] Generated new session ID: {session_id}")

    # --- Content-Type whitelist (PDF or images only) ---
    if (file.content_type not in VALID_UPLOAD_TYPES) and (
        file.content_type not in IMAGE_UPLOAD_TYPES
    ):
        # DEBUG: print the received content-type to locate mismatches
        print(f"[DEBUG] Rejected content-type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Invalid content type")

    # --- Read the file ONCE and reuse the buffer everywhere ---
    # NOTE: UploadFile has no `.size` attribute by default; always read and check length.
    file_b = await file.read()
    if len(file_b) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=400, detail="File too large. Maximum size is 50MB"
        )

    # --- Filename / extension guards ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    lower_name = file.filename.lower()
    is_pdf = lower_name.endswith(".pdf")
    is_image = lower_name.endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")
    )
    if not (is_pdf or is_image):
        raise HTTPException(
            status_code=400, detail="Invalid filename. Must be a PDF or image file"
        )

    # Save PDF file to reports directory in {original_name}_{timestamp} format
    # file_b = await file.read()
    file_hash = hash_file(file_b)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate safe filename (format: original_name_analysis_time)
    from datetime import datetime
    import re

    original_name = Path(file.filename).stem  # Get filename without extension
    safe_name = re.sub(r"[^\w\-_]", "_", original_name)  # Replace special chars
    analysis_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    # original image path (only used when the upload is an image)
    suffix = Path(file.filename).suffix.lower()
    file_path = REPORT_DIR / f"{safe_name}_{analysis_time}{suffix}"

    # --- Build vector store (OCR for image, chunking for PDF) ---
    # 1) Save original file
    with file_path.open("wb") as f:
        f.write(file_b)

    if is_image:
        # 2) OCR MUST run on the image path (NOT a PDF)
        ocr_out = ocr_service.read(str(file_path), mode="smart")
        ocr_text = (
            ocr_out.get("cleaned_text") or ocr_out.get("full_text") or ""
        ).strip()
        if not ocr_text:
            raise HTTPException(
                status_code=400,
                detail="The uploaded image contains no recognizable text for analysis.",
            )

    # Ensure report_file exists
    report_file = db.query(ReportFile).filter_by(file_hash=file_hash).first()
    if not report_file:
        report_file = ReportFile(
            file_hash=file_hash,
            file_path=str(file_path),
            original_filename=f"{safe_name}_{analysis_time}.pdf",
        )
        db.add(report_file)
        db.commit()
        db.refresh(report_file)
    elif force_new:
        # Update file info when forcing re-analysis
        report_file.file_path = str(file_path)
        report_file.original_filename = file.filename
        db.commit()
        db.refresh(report_file)

    # Check for existing analysis results (unless forcing re-analysis)
    if not force_new:
        latest_report = (
            db.query(Report)
            .filter_by(file_id=report_file.id)
            .order_by(Report.analysis_time.desc())
            .first()
        )
        if latest_report:
            # Delete newly uploaded file when viewing old report
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
                    "metrics": json.loads(latest_report.metrics),
                },
            }

    # 🔍 Detect PDF language
    try:
        sample_text = ""
        if is_pdf:
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    sample_text += text
                if len(sample_text) > 1000:
                    break
        else:
            sample_text = ocr_text
            print("sample_text", sample_text)
        detected_language = (
            detect(sample_text[:2000]) if sample_text.strip() else "unknown"
        )
    except Exception as e:
        print(f"[Warning] Language detection failed: {e}")
        detected_language = "unknown"

    try:
        print(f"[INFO] Starting document processing for session {session_id}")

        # Parse and split document
        print(f"[INFO] Processing PDF document...")
        chunks = 0
        if is_pdf:
            chunks = await process_pdf_document(str(file_path))
        else:
            chunks = await process_ocr_text(ocr_text)
        print(f"[INFO] Document processed, created {len(chunks)} chunks")

        # Create and persist vector index
        from langchain_community.vectorstores import Chroma
        from gw_api.config import VECTOR_STORE_DIR

        persist_path = VECTOR_STORE_DIR / session_id
        vector_store = Chroma.from_documents(
            chunks, embedding_model, persist_directory=str(persist_path)
        )
        from gw_api.core.store import save_vector_store

        save_vector_store(session_id, vector_store)
        document_stores[session_id] = vector_store  # Keep in memory for current session

        # Extract company name
        company_query = "What is the name of the company that published this report?"
        company_docs = vector_store.similarity_search(company_query, k=3)
        company_context = "\n".join([doc.page_content for doc in company_docs])
        company_prompt = f"""
        Extract the company name from this context:
        {company_context}
        
        Return only the company name, nothing else.
        """
        company_response = llm.invoke([HumanMessage(content=company_prompt)])
        company_name = company_response.content.strip()

        # Perform ESG analysis
        print(f"[INFO] Starting ESG analysis for company: {company_name}")

        analysis_result = await comprehensive_esg_analysis(
            session_id, vector_store, company_name, "en"
        )
        if analysis_result.get("error"):
            raise Exception(analysis_result["error"])

        final_synthesis_en = analysis_result.get("final_synthesis", "")
        metrics_ref = analysis_result.get("metrics", {}) or {}

        final_synthesis_de = await translate_text(final_synthesis_en, "German")
        final_synthesis_it = await translate_text(final_synthesis_en, "Italian")

        finals_by_lang = {
            "en": final_synthesis_en,
            "de": final_synthesis_de,
            "it": final_synthesis_it,
        }

        report = Report(
            session_id=session_id,
            company_name=company_name,
            overall_score=(metrics_ref.get("overall_greenwashing_score", {}) or {}).get(
                "score", 0
            )
            * 10,
            risk_type=_get_main_risk_type(
                {
                    "metrics": {
                        "breakdown": [
                            {"type": k, "value": (v or {}).get("score", 0) * 10}
                            for k, v in (
                                metrics_ref.items()
                                if isinstance(metrics_ref, dict)
                                else []
                            )
                            if k != "overall_greenwashing_score"
                        ]
                    }
                }
            ),
            metrics=json.dumps(metrics_ref),
            analysis_summary=final_synthesis_en,
            analysis_summary_i18n=json.dumps(finals_by_lang),
            file_id=report_file.id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        result = {
            "filename": file_path.name,
            "company_name": company_name,
            "session_id": session_id,
            "response": final_synthesis_en,
            "graphdata": metrics_ref,
            "metrics": metrics_ref,
            "final_synthesis": final_synthesis_en,
            "final_synthesis_i18n": finals_by_lang,
            "validation_complete": True,
        }

        # Store in memory for /report/{session_id} queries
        analysis_results_by_session[session_id] = result
        print(f"[INFO] Stored data keys: {list(result.keys())}")
        print(f"[DEBUG] Analysis results stored for session: {session_id}")

        # Save session with vector store and analysis results
        session_data = {
            "company_name": company_name,
            "analysis_results": result,
            "agent_executor": True,  # Mark that agent was initialized
            "vector_store_path": str(persist_path),
            "created_at": datetime.now().timestamp(),
        }
        print(f"[DEBUG] Saving session data with keys: {list(session_data.keys())}")
        save_session(session_id, session_data, db)
        print(f"[INFO] Session {session_id} saved to persistent storage")

        # Register agent executor
        print(f"[AGENT DEBUG] Creating agent for session: {session_id}")
        from gw_api.core.esg_analysis import create_esg_agent

        agent = create_esg_agent(session_id, vector_store, company_name)
        agent_executors[session_id] = agent
        print(f"[AGENT DEBUG] Agent created and registered for session: {session_id}")
        print(f"[AGENT DEBUG] Current active agents: {list(agent_executors.keys())}")

        return result

    except Exception as e:
        # Delete saved files if analysis fails
        file_path.unlink(missing_ok=True)
        # Clean up agent if created
        try:
            if session_id in agent_executors:
                print(
                    f"[AGENT DEBUG] Cleaning up agent for failed session: {session_id}"
                )
                del agent_executors[session_id]
        except NameError:
            pass  # agent_executors not imported/available
        # Rollback database operations
        db.rollback()

        error_detail = str(e)

        if "invalid pdf header" in error_detail.lower():
            error_detail = (
                "Invalid PDF file format, please ensure you upload a valid PDF document"
            )
        elif "eof marker not found" in error_detail.lower():
            error_detail = "PDF file is corrupted or incomplete, please re-upload"
        elif "language detection failed" in error_detail.lower():
            error_detail = (
                "Unable to detect document language, please check document content"
            )

        print(f"[ERROR] Upload processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {error_detail}")

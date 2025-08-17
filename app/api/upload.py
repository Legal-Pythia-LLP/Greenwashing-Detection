from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from typing import Annotated, Dict, Any, Optional
from pathlib import Path
import json
from collections import defaultdict

    # Global dictionary to store analysis results
analysis_results_by_session = defaultdict(dict)
from app.core.utils import hash_file
from app.core.document import process_pdf_document
from app.core.vector_store import embedding_model
from app.config import UPLOAD_DIR, REPORT_DIR, VALID_UPLOAD_TYPES, VALID_COMPANIES
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

IMAGE_UPLOAD_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff", "image/bmp"
}

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
    force_new: Optional[bool] = Form(False),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:

    DetectorFactory.seed = 0
    vector_store = None  # IMPORTANT: avoid UnboundLocalError later

    if not session_id:
        session_id = f"s_{uuid.uuid4().hex[:16]}"

    # --- Content-Type whitelist (PDF or images only) ---
    if (file.content_type not in VALID_UPLOAD_TYPES) and (file.content_type not in IMAGE_UPLOAD_TYPES):
        # DEBUG: print the received content-type to locate mismatches
        print(f"[DEBUG] Rejected content-type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Invalid content type")

    # --- Read the file ONCE and reuse the buffer everywhere ---
    # NOTE: UploadFile has no `.size` attribute by default; always read and check length.
    file_b = await file.read()
    if len(file_b) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")

    # --- Filename / extension guards ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    lower_name = file.filename.lower()
    is_pdf = lower_name.endswith(".pdf")
    is_image = lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"))
    if not (is_pdf or is_image):
        raise HTTPException(status_code=400, detail="Invalid filename. Must be a PDF or image file")

    # --- Prepare paths / names ---
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    import re

    original_name = Path(file.filename).stem
    safe_name = re.sub(r"[^\w\-_]", "_", original_name)
    analysis_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    # archive PDF (we always keep a PDF copy on disk for consistency)
    archive_pdf_path = REPORT_DIR / f"{safe_name}_{analysis_time}.pdf"
    # original image path (only used when the upload is an image)
    img_suffix = Path(file.filename).suffix.lower()
    img_path = REPORT_DIR / f"{safe_name}_{analysis_time}{img_suffix}"

    # --- Build vector store (OCR for image, chunking for PDF) ---
    try:
        if is_image:
            # 1) Save original image file
            with img_path.open("wb") as f:
                f.write(file_b)

            # 2) OCR MUST run on the image path (NOT a PDF)
            ocr_out = ocr_service.read(str(img_path), mode="smart")
            ocr_text = (ocr_out.get("cleaned_text") or ocr_out.get("full_text") or "").strip()
            if not ocr_text:
                raise HTTPException(status_code=400, detail="The uploaded image contains no recognizable text for analysis.")

            try:
                detected_language = detect(ocr_text[:2000]) if ocr_text else "unknown"
            except Exception:
                detected_language = "unknown"

            # 3) Create vector store from OCR text
            vector_store = Chroma.from_texts(
                [ocr_text],
                embedding=embedding_model,
                metadatas=[{"source": "image_ocr"}],
                collection_name=f"img_{session_id[:8]}"
            )

            # 4) (Optional) also archive the image as PDF for consistency
            try:
                img = Image.open(io.BytesIO(file_b))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(str(archive_pdf_path), "PDF", resolution=300.0)
            except Exception as e:
                # Choose to fail or warn; here we fail with a clear message
                raise HTTPException(status_code=400, detail=f"Image to PDF archiving failed: {e}")

        else:
            # PDF branch: write the buffer once and process
            with archive_pdf_path.open("wb") as f:
                f.write(file_b)

            # Small sample for language detection (best effort)
            reader = PdfReader(str(archive_pdf_path))
            sample_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    sample_text += text
                if len(sample_text) > 1000:
                    break
            detected_language = detect(sample_text[:2000]) if sample_text.strip() else "unknown"

            # Parse and split PDF, then build vector index
            chunks = await process_pdf_document(str(archive_pdf_path))
            vector_store = Chroma.from_documents(chunks, embedding=embedding_model)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Warning] Vector store stage failed: {e}")
        # If vector_store was never created, bail out with a clear message
        if vector_store is None:
            raise HTTPException(status_code=500, detail=f"Vector store creation failed: {e}")
        detected_language = "unknown"

    # --- DB bookkeeping (hash must use the SAME buffer we read above) ---
    file_hash = hash_file(file_b)
    report_file = db.query(ReportFile).filter_by(file_hash=file_hash).first()
    if not report_file:
        report_file = ReportFile(
            file_hash=file_hash,
            file_path=str(archive_pdf_path),              # store archived PDF path
            original_filename=archive_pdf_path.name       # stored filename
        )
        db.add(report_file)
        db.commit()
        db.refresh(report_file)
    elif force_new:
        report_file.file_path = str(archive_pdf_path)
        report_file.original_filename = archive_pdf_path.name
        db.commit()
        db.refresh(report_file)

    # Check duplicates (unless forcing re-analysis)
    if not force_new:
        latest_report = db.query(Report).filter_by(file_id=report_file.id).order_by(Report.analysis_time.desc()).first()
        if latest_report:
            # Delete newly uploaded archive when pointing to old report
            Path(archive_pdf_path).unlink(missing_ok=True)
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

    # Register the vector store for this session
    document_stores[session_id] = vector_store

    try:
        # Extract company name via retrieval
        company_query = "What is the name of the company that published this report?"
        company_docs = vector_store.similarity_search(company_query, k=3)
        company_context = "\n".join([doc.page_content for doc in company_docs])
        company_prompt = f"Extract the company name from this context:\n{company_context}\n\nReturn only the company name, nothing else."
        company_response = llm.invoke([HumanMessage(content=company_prompt)])
        company_name = (company_response.content or "").strip() or "Unknown Company"

        # ESG analysis
        print(f"[INFO] Starting ESG analysis for company: {company_name}")
        analysis_results = await comprehensive_esg_analysis(
            session_id=session_id,
            vector_store=vector_store,
            company_name=company_name,
            output_language=overrided_language or "en"
        )
        print(f"[INFO] ESG analysis completed successfully")

        if analysis_results.get("error"):
            raise Exception(analysis_results["error"])

        report = Report(
            session_id=session_id,
            company_name=company_name,
            overall_score=analysis_results["metrics"].get("overall_greenwashing_score", {}).get("score", 0) * 10,
            risk_type=_get_main_risk_type(analysis_results),
            metrics=json.dumps(analysis_results["metrics"]),
            analysis_summary=analysis_results["final_synthesis"],
            file_id=report_file.id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        result = {
            "filename": archive_pdf_path.name,           # use archived filename
            "company_name": company_name,
            "session_id": session_id,
            "response": analysis_results["final_synthesis"],
            "initial_analysis": analysis_results["initial_analysis"],
            "document_analysis": analysis_results["document_analysis"],
            "news_validation": analysis_results["news_validation"],
            "wikirate_validation": analysis_results["wikirate_validation"],
            "graphdata": analysis_results["metrics"],
            "metrics": analysis_results.get("metrics"),
            "comprehensive_analysis": analysis_results["comprehensive_analysis"],
            "tool_plan": analysis_results.get("tool_plan"),
            "validations": analysis_results.get("validations"),
            "quotations": analysis_results.get("quotations"),
            "final_synthesis": analysis_results.get("final_synthesis"),
            "validation_complete": True,
            "filenames": ["bbc_articles", "cnn_articles"] if company_name.lower() in VALID_COMPANIES else None,
            "workflow_error": analysis_results.get("error"),
            "detected_language": detected_language,
            "overrided_language": overrided_language or "en",
        }

        analysis_results_by_session[session_id] = result
        print(f"[INFO] Analysis results stored for session {session_id}")
        return result

    except Exception as e:
        # Cleanup on failure
        Path(archive_pdf_path).unlink(missing_ok=True)
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

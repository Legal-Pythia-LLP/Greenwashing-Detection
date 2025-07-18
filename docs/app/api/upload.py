from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from typing import Annotated, Dict, Any
from app.utils.hashing import hash_file
from app.utils.pdf_processing import process_pdf_document_multilingual
from app.config import SUPPORTED_LANGUAGES
from app.models.pydantic_models import ESGAnalysisResult
from app.services.esg_analysis import comprehensive_esg_analysis_multilingual, extract_company_info_multilingual, embedding_model
from langchain_community.vectorstores import Chroma
from pathlib import Path
import os

router = APIRouter()

UPLOAD_DIR = Path(os.path.dirname(__file__)).parent.parent / "uploads"
VALID_UPLOAD_TYPES = ["application/pdf"]

@router.post("/upload")
async def upload_document_multilingual(
    file: Annotated[UploadFile, File()],
    session_id: Annotated[str, Form()]
) -> Dict[str, Any]:
    if file.content_type not in VALID_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type")
    file_b = await file.read()
    file_hash = hash_file(file_b)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{file_hash}.pdf"
    with file_path.open("wb") as f:
        f.write(file_b)
    try:
        chunks, detected_language = await process_pdf_document_multilingual(str(file_path))
        vector_store = Chroma.from_documents(chunks, embedding_model)
        company_query_templates = {
            'en': "What is the name of the company that published this report?",
            'de': "Wie heißt das Unternehmen, das diesen Bericht veröffentlicht hat?",
            'it': "Qual è il nome dell'azienda che ha pubblicato questo rapporto?"
        }
        company_query = company_query_templates.get(detected_language, company_query_templates['en'])
        company_name = extract_company_info_multilingual(company_query, vector_store, detected_language)
        analysis_results = await comprehensive_esg_analysis_multilingual(
            session_id, vector_store, company_name, detected_language
        )
        file_path.unlink(missing_ok=True)
        return {
            "filename": file_path.name,
            "company_name": company_name,
            "detected_language": detected_language,
            "language_name": SUPPORTED_LANGUAGES[detected_language],
            "session_id": session_id,
            "response": analysis_results["final_synthesis"],
            "initial_analysis": analysis_results["initial_analysis"],
            "document_analysis": analysis_results["document_analysis"],
            "news_validation": analysis_results["news_validation"],
            "graphdata": analysis_results["metrics"],
            "comprehensive_analysis": analysis_results["comprehensive_analysis"],
            "validation_complete": True,
            "filenames": ["bbc_articles", "cnn_articles"] if company_name else None,
            "workflow_error": analysis_results.get("error"),
            "supported_languages": SUPPORTED_LANGUAGES
        }
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}") 
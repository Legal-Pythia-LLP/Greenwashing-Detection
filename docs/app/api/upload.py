from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Annotated, Dict, Any
from app.utils.hashing import hash_file
from app.utils.pdf_processing import process_pdf_document_multilingual
from app.config import UPLOAD_DIR, SUPPORTED_LANGUAGES
from app.services.memory import set_document_store
from app.services.esg_analysis import comprehensive_esg_analysis_multilingual
import os

router = APIRouter()

@router.post("/upload")
async def upload_document_multilingual(
    file: Annotated[UploadFile, File()],
    session_id: Annotated[str, Form()],
    llm: Any = None  # 需在主入口依赖注入
) -> Dict[str, Any]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid content type")
    file_b = await file.read()
    file_hash = hash_file(file_b)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{file_hash}.pdf"
    with open(file_path, "wb") as f:
        f.write(file_b)
    try:
        chunks, detected_language = process_pdf_document_multilingual(str(file_path))
        from langchain_community.vectorstores import Chroma
        from app.services.llm import embedding_model  # 需在主入口初始化
        vector_store = Chroma.from_documents(chunks, embedding_model)
        set_document_store(session_id, vector_store)
        # 公司名抽取（可选，简化处理）
        company_name = "unknown"
        # 综合分析
        analysis_results = comprehensive_esg_analysis_multilingual(
            session_id, vector_store, company_name, detected_language, llm
        )
        os.remove(file_path)
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
            "workflow_error": analysis_results.get("error"),
            "supported_languages": SUPPORTED_LANGUAGES
        }
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}") 
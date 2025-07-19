from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Annotated
from app.utils.hashing import hash_file
from app.utils.pdf_processing import process_pdf_document_multilingual
from app.config import UPLOAD_DIR, SUPPORTED_LANGUAGES
from app.services.memory import set_document_store
from app.services.esg_analysis import comprehensive_esg_analysis_multilingual, extract_company_info_multilingual
import os

router = APIRouter()

@router.post("/upload")
async def upload_document_multilingual(
    file: Annotated[UploadFile, File()],
    session_id: Annotated[str, Form()],
    llm = None
) -> dict:
    """
    PDF 上传与多语言 ESG 分析接口。
    1. 校验并保存上传的 PDF 文件
    2. 自动检测语言、分块、向量化
    3. 自动抽取公司名
    4. 调用综合分析主流程，返回分析结果
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid content type")
    file_b = await file.read()
    file_hash = hash_file(file_b)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{file_hash}.pdf"
    with open(file_path, "wb") as f:
        f.write(file_b)
    try:
        # 处理PDF，自动检测语言并分块
        chunks, detected_language = process_pdf_document_multilingual(str(file_path))
        from langchain_community.vectorstores import Chroma
        from app.services.llm import embedding_model, llm as global_llm
        # 构建向量库
        vector_store = Chroma.from_documents(chunks, embedding_model)
        set_document_store(session_id, vector_store)
        # 自动公司名识别
        company_query_templates = {
            'en': "What is the name of the company that published this report?",
            'de': "Wie heißt das Unternehmen, das diesen Bericht veröffentlicht hat?",
            'it': "Qual è il nome dell'azienda che ha pubblicato questo rapporto?"
        }
        company_query = company_query_templates.get(detected_language, company_query_templates['en'])
        company_name = extract_company_info_multilingual(company_query, vector_store, detected_language)
        # 综合分析
        analysis_results = comprehensive_esg_analysis_multilingual(
            session_id, vector_store, company_name, detected_language, llm or global_llm
        )
        # 检查分析结果完整性
        required_keys = ["final_synthesis", "initial_analysis", "document_analysis", "news_validation", "metrics", "comprehensive_analysis"]
        for key in required_keys:
            if key not in analysis_results:
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=500, detail=f"Processing error: {analysis_results.get('error', 'Unknown error')}")
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
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}") 
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from typing import Annotated, Dict, Any
from app.core.utils import hash_file
from app.core.document import process_pdf_document
from app.core.vector_store import embedding_model
from app.config import UPLOAD_DIR, VALID_UPLOAD_TYPES, VALID_COMPANIES
from app.core.llm import llm
from app.core.company import extract_company_info
from app.models import ChatBaseMessage
from app.core.esg_analysis import comprehensive_esg_analysis, document_stores
from langchain.schema import HumanMessage
import os
from PyPDF2 import PdfReader
from langdetect import detect, DetectorFactory

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: Annotated[UploadFile, File()],
    session_id: Annotated[str, Form()],
    overrided_language: Annotated[str | None, Form()] = None
) -> Dict[str, Any]:

    DetectorFactory.seed = 0  # 保证语言检测结果一致

    if file.content_type not in VALID_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type")

    # 保存 PDF 文件
    file_b = await file.read()
    file_hash = hash_file(file_b)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{file_hash}.pdf"
    with file_path.open("wb") as f:
        f.write(file_b)

    # 🔍 检测 PDF 语言
    try:
        reader = PdfReader(str(file_path))
        sample_text = ''
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

    try:
        # 解析并切分文档
        chunks = await process_pdf_document(str(file_path))

        # 创建向量索引
        from langchain_community.vectorstores import Chroma
        vector_store = Chroma.from_documents(chunks, embedding_model)
        document_stores[session_id] = vector_store

        # 提取公司名称
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

        # 执行 ESG 分析
        analysis_results = await comprehensive_esg_analysis(session_id, vector_store, company_name,overrided_language or "en")

        # 删除临时文件
        file_path.unlink(missing_ok=True)

        return {
            "filename": file_path.name,
            "company_name": company_name,
            "session_id": session_id,
            "response": analysis_results["final_synthesis"],
            "initial_analysis": analysis_results["initial_analysis"],
            "document_analysis": analysis_results["document_analysis"],
            "news_validation": analysis_results["news_validation"],
            "wikirate_validation": analysis_results["wikirate_validation"],
            "graphdata": analysis_results["metrics"],
            "comprehensive_analysis": analysis_results["comprehensive_analysis"],
            "tool_plan": analysis_results.get("tool_plan"),  # ✅ 添加这行
            "validation_complete": True,
            "filenames": ["bbc_articles", "cnn_articles"] if company_name.lower() in VALID_COMPANIES else None,
            "workflow_error": analysis_results.get("error"),
            "detected_language": detected_language,
            "overrided_language": overrided_language or "en"
        }

    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

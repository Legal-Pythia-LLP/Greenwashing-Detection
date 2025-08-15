from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from typing import Annotated, Dict, Any, Optional
from pathlib import Path
import json
from collections import defaultdict

# 存储分析结果的全局字典
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

def _get_main_risk_type(analysis_results: Dict[str, Any]) -> str:
    """从分析结果中提取主要风险类型"""
    breakdown = analysis_results.get("metrics", {}).get("breakdown", [])
    if not breakdown:
        return "未知类型"
    
    # 找到评分最高的类型
    max_score = 0
    main_type = "未知类型"
    for item in breakdown:
        score = item.get("value", 0)
        if isinstance(score, str):
            try:
                score = float(score)
            except:
                score = 0
        if score > max_score:
            max_score = score
            main_type = item.get("type", "未知类型")
    
    return main_type

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    session_id: Optional[str] = Form(None),
    overrided_language: Optional[str] = Form(None),
    force_new: Optional[bool] = Form(False),  # 新增强制重新分析标志
    db: Session = Depends(get_db)
) -> Dict[str, Any]:

    DetectorFactory.seed = 0  # 保证语言检测结果一致

    # ✅ 如果没传 session_id，则生成一个新的
    if not session_id:
        session_id = f"s_{uuid.uuid4().hex[:16]}"

    # 验证文件类型
    if file.content_type not in VALID_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type")
    
    # 验证文件大小（限制为 50MB）
    if file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")
    
    # 验证文件名
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid filename. Must be a PDF file")

    # 保存 PDF 文件到reports目录，使用{原文件名}_{时间戳}格式
    file_b = await file.read()
    file_hash = hash_file(file_b)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成安全的文件名(格式:原文件名_分析时间)
    from datetime import datetime
    import re
    
    original_name = Path(file.filename).stem  # 获取不带扩展名的文件名
    safe_name = re.sub(r'[^\w\-_]', '_', original_name)  # 替换特殊字符
    analysis_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = REPORT_DIR / f"{safe_name}_{analysis_time}.pdf"
    
    with file_path.open("wb") as f:
        f.write(file_b)

    # 确保report_file存在
    report_file = db.query(ReportFile).filter_by(file_hash=file_hash).first()
    if not report_file:
        report_file = ReportFile(
            file_hash=file_hash,
            file_path=str(file_path),
            original_filename=f"{safe_name}_{analysis_time}.pdf"
        )
        db.add(report_file)
        db.commit()
        db.refresh(report_file)
    elif force_new:
        # 强制重新分析时更新文件信息
        report_file.file_path = str(file_path)
        report_file.original_filename = file.filename
        db.commit()
        db.refresh(report_file)
    
    # 检查是否有现有分析结果(除非强制重新分析)
    if not force_new:
        latest_report = db.query(Report).filter_by(file_id=report_file.id).order_by(Report.analysis_time.desc()).first()
        if latest_report:
            # 查看旧报告时删除新上传的文件
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
        print(f"[INFO] Starting document processing for session {session_id}")
        
        # 解析并切分文档
        print(f"[INFO] Processing PDF document...")
        chunks = await process_pdf_document(str(file_path))
        print(f"[INFO] Document processed, created {len(chunks)} chunks")

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
        print(f"[INFO] Starting ESG analysis for company: {company_name}")
        analysis_results = await comprehensive_esg_analysis(session_id, vector_store, company_name, overrided_language or "en")
        print(f"[INFO] ESG analysis completed successfully")

        # 检查分析结果是否有错误
        if analysis_results.get("error"):
            raise Exception(analysis_results["error"])

        print("=== METRICS JSON ===")
        print(analysis_results["metrics"])

        # 创建Report记录
        report = Report(
            session_id=session_id,
            company_name=company_name,
            overall_score = analysis_results["metrics"].get("overall_greenwashing_score", {}).get("score", 0) * 10,
            risk_type=_get_main_risk_type(analysis_results),
            metrics=json.dumps(analysis_results["metrics"]),
            analysis_summary=analysis_results["final_synthesis"],
            file_id=report_file.id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        result = {
            "filename": file_path.name,
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

        # 存入内存，供 /report/{session_id} 查询
        analysis_results_by_session[session_id] = result
        print(f"[INFO] Analysis results stored for session {session_id}")
        print(f"[INFO] Stored data keys: {list(result.keys())}")

        return result

    except Exception as e:
        # 分析失败时删除已保存的文件
        file_path.unlink(missing_ok=True)
        # 回滚数据库操作
        db.rollback()
        
        error_detail = str(e)
        
        if "invalid pdf header" in error_detail.lower():
            error_detail = "无效的 PDF 文件格式，请确保上传的是有效的 PDF 文档"
        elif "eof marker not found" in error_detail.lower():
            error_detail = "PDF 文件损坏或不完整，请重新上传"
        elif "language detection failed" in error_detail.lower():
            error_detail = "无法检测文档语言，请检查文档内容"
        
        print(f"[ERROR] Upload processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {error_detail}")

from fastapi import APIRouter, UploadFile, File
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from app.core.ocr_service import ocr_service
from app.core.vector_store import embedding_model
from app.core.esg_analysis import comprehensive_esg_analysis
from langchain_community.vectorstores import Chroma   


router = APIRouter(prefix="/ocr", tags=["ocr"])

@router.post("/judge")
async def ocr_judge(
    file: UploadFile = File(...),
    mode: str = "smart",
    company_name: str | None = None,
    output_language: str = "en"
):
    suffix = Path(file.filename or "").suffix or ".png"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # Step 1: OCR
        ocr_out = ocr_service.read(tmp_path, mode=mode)
        text = ocr_out.get("cleaned_text") or ocr_out.get("full_text") or ""

        if not text.strip():
            return {
                "error": "Empty OCR result",
                "text": "",
                "final_synthesis": "",
                "highlights": []
            }

        # Step 2: 构建临时向量库
        doc_id = str(uuid4())
        vector_store = Chroma.from_texts(
            [text],
            embedding=embedding_model,
            metadatas=[{"source": "ocr"}],
            collection_name=f"ocr_{doc_id[:8]}"
        )

        # Step 3: 调用综合 ESG 分析
        session_id = str(uuid4())[:8]
        result = await comprehensive_esg_analysis(
            session_id=session_id,
            vector_store=vector_store,
            company_name=company_name or "",
            output_language=output_language
        )

        # Step 4: 额外提取 highlights
        highlights = []
        try:
            # 1) 从 document_analysis 抽 quotation
            if isinstance(result.get("document_analysis"), list):
                for item in result["document_analysis"]:
                    q = item.get("quotation")
                    if q and isinstance(q, str):
                        highlights.append(q.strip()[:80])
            # 2) 从 validations 抽 quotation
            for v in result.get("validations", []):
                q = v.get("quotation")
                if q and isinstance(q, str):
                    highlights.append(q.strip()[:80])
        except Exception:
            pass

        # 3) 如果完全没有，fallback：简单关键词匹配
        if not highlights:
            candidates = ["carbon neutral", "net zero", "recyclable",
                          "offset", "sustainable", "plastic neutral",
                          "green", "renewable"]
            text_lower = text.lower()
            for c in candidates:
                if c in text_lower:
                    highlights.append(c)

        # 去重 + 限长
        seen = set()
        final_highlights = []
        for h in highlights:
            if h not in seen:
                seen.add(h)
                final_highlights.append(h)
            if len(final_highlights) >= 10:
                break

        # Step 5: 返回结果，附带 highlights
        return {
            "text": text,
            "highlights": final_highlights,
            **result
        }

    finally:
        Path(tmp_path).unlink(missing_ok=True)

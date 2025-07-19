from fastapi import APIRouter, Form, HTTPException
from typing import Annotated
from app.config import SUPPORTED_LANGUAGES
from app.utils.translation import translate_text

router = APIRouter()

@router.get("/languages")
async def get_supported_languages() -> dict:
    """
    获取支持的多语言列表。
    """
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "default_language": "en"
    }

@router.post("/translate")
async def translate_analysis(
    text: Annotated[str, Form()],
    target_language: Annotated[str, Form()],
    source_language: Annotated[str, Form()] = "auto"
) -> dict:
    """
    分析结果多语言翻译接口。
    """
    if target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target language. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    try:
        translated_text = translate_text(text, target_language, source_language)
        return {
            "original_text": text,
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": target_language,
            "target_language_name": SUPPORTED_LANGUAGES[target_language]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}") 
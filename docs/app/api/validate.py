from fastapi import APIRouter, Form, HTTPException
from typing import Annotated
from app.config import SUPPORTED_LANGUAGES
from app.utils.language import analyze_language_specific_greenwashing, extract_multilingual_entities
from app.services.memory import document_stores

router = APIRouter()

@router.post("/validate_language")
async def validate_language_specific_claims(
    text: Annotated[str, Form()],
    language: Annotated[str, Form()],
    session_id: Annotated[str, Form()]
):
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    try:
        greenwashing_analysis = analyze_language_specific_greenwashing(text, language)
        entities = extract_multilingual_entities(text, language)
        vector_store = document_stores.get(session_id)
        additional_context = ""
        if vector_store:
            related_docs = vector_store.similarity_search(text[:500], k=3)
            additional_context = "\n".join([doc.page_content for doc in related_docs])
        return {
            "input_text": text,
            "language": language,
            "language_name": SUPPORTED_LANGUAGES[language],
            "greenwashing_analysis": greenwashing_analysis,
            "extracted_entities": entities,
            "additional_context_found": bool(additional_context),
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}") 
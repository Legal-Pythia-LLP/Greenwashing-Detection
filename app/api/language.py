from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class LanguageRequest(BaseModel):
    language: str

# Store user language preferences (in production, use a database)
user_language_preferences = {}

@router.post("/set-language")
async def set_language(request: LanguageRequest):
    """Set user's preferred language for AI responses"""
    # In production, store this with user session/ID
    user_language_preferences['current'] = request.language
    return {"status": "success", "language": request.language}

@router.get("/get-language")
async def get_language():
    """Get current language preference"""
    return {"language": user_language_preferences.get('current', 'en')}
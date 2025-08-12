from .upload import router as upload_router
from .chat import router as chat_router
from .ocr_router import router as ocr_router
from .wikirateAPItest import router as wikirate_router

from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(upload_router)
api_router.include_router(chat_router)
api_router.include_router(ocr_router)
api_router.include_router(wikirate_router)

__all__ = ["api_router"]

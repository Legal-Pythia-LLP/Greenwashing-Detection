# backend/gw_api/api/__init__.py
from fastapi import APIRouter

from .upload import router as upload_router
from .chat import router as chat_router
from .wikirateAPItest import router as wikirate_router
from .report import router as report_router
from .dashboard import router as dashboard_router
from .city_analysis import router as city_router  # ✅ keep this one
from .deep_research_city_rankings import router as city_rankings_router


router = APIRouter()

router.include_router(upload_router)
router.include_router(chat_router)
router.include_router(wikirate_router)
router.include_router(report_router)
router.include_router(dashboard_router)
router.include_router(city_router)  # exposes /v2/city-rankings/analyze

__all__ = ["router"]

# backend/gw_api/api/city_analysis.py
from fastapi import APIRouter
from pydantic import BaseModel
from gw_api.core.esg_city_service import analyze_city_to_payload

router = APIRouter(prefix="/v2/city-rankings", tags=["City Rankings"])

class CityAnalyzeRequest(BaseModel):
    city: str
    top_n: int = 10

@router.post("/analyze")
async def analyze_city(req: CityAnalyzeRequest):
    """
    Always return a JSON payload that the frontend can render.
    Never raise HTTP errors for 'no companies' — just return status: 'no_companies'.
    """
    payload = await analyze_city_to_payload(req.city, req.top_n)
    # payload schema: {status: "ok"|"no_companies", discovery_html, report_html, table}
    return payload

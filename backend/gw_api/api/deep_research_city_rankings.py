# backend/gw_api/api/deep_research_city_rankings.py
"""
City Rankings API for Deep Research ESG Analysis
FastAPI router for city-based company sustainability rankings
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Use your analyzer that performs discovery + analysis
from gw_api.core.deep_research_city_analyzer import CityCompanyAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# All routes will live under /v2/city-rankings/*
router = APIRouter(prefix="/v2/city-rankings", tags=["City Rankings"])

# ==================== Schemas ====================

class CityAnalysisRequest(BaseModel):
    city: str = Field(..., description="City name to analyze companies in", example="San Francisco")
    top_n: int = Field(default=10, ge=3, le=20, description="Number of companies to analyze")
    # Keep language optional – only use if your analyzer actually supports it
    language: Optional[str] = Field(default=None, description="Optional language hint (if supported)")

class CompanyDiscoveryResponse(BaseModel):
    status: str  # "ok" | "no_companies"
    companies: List[Dict[str, Any]]
    discovery_html: str
    total_found: int
    city: str
    timestamp: str

class SustainabilityDataResponse(BaseModel):
    company_name: str
    sustainability_score: float
    environmental_score: float
    social_score: float
    governance_score: float
    esg_rating: str
    location: Optional[str] = None
    industry: Optional[str] = None
    key_strengths: List[str] = []
    key_risks: List[str] = []
    recommendations: List[str] = []
    summary: str = ""
    data_quality: Optional[Dict[str, Any]] = None
    scoring_explanations: Optional[Dict[str, Any]] = None
    last_updated: str

class CityRankingsResponse(BaseModel):
    status: str  # "ok" | "no_companies"
    city: str
    companies: List[SustainabilityDataResponse]
    discovery_html: str
    analysis_summary: Dict[str, Any]
    timestamp: str
    total_analyzed: int

# ==================== Endpoints ====================

@router.post("/discover", response_model=CompanyDiscoveryResponse)
async def discover_companies_in_city(request: CityAnalysisRequest):
    """
    Discover companies in a specified city without running full ESG analysis.
    Always returns 200 with status "ok" or "no_companies".
    """
    logger.info(f"[discover] city={request.city} top_n={request.top_n}")
    analyzer = CityCompanyAnalyzer()

    try:
        # IMPORTANT: match your analyzer's signature (city, top_n)
        companies_data, discovery_html = await analyzer.find_companies_in_city_fast(
            request.city, request.top_n
        )
    except HTTPException as e:
        # Let FastAPI handle explicit HTTP errors
        raise e
    except Exception as e:
        logger.exception("Discovery failed")
        # Surface as a 500 only for genuine unexpected failures
        raise HTTPException(status_code=500, detail=f"Discovery failed: {e}")

    if not companies_data:
        return CompanyDiscoveryResponse(
            status="no_companies",
            companies=[],
            discovery_html=discovery_html or f"<div>No companies found in {request.city}.</div>",
            total_found=0,
            city=request.city,
            timestamp=datetime.now().isoformat(),
        )

    return CompanyDiscoveryResponse(
        status="ok",
        companies=companies_data,
        discovery_html=discovery_html or "",
        total_found=len(companies_data),
        city=request.city,
        timestamp=datetime.now().isoformat(),
    )


@router.post("/analyze", response_model=CityRankingsResponse)
async def analyze_city_companies(request: CityAnalysisRequest):
    """
    Full city ESG analysis:
      1) Discover companies
      2) Analyze each company
    Always returns 200 with status "ok" or "no_companies".
    """
    logger.info(f"[analyze] city={request.city} top_n={request.top_n}")
    analyzer = CityCompanyAnalyzer()

    # Step 1: discovery
    try:
        companies_data, discovery_html = await analyzer.find_companies_in_city_fast(
            request.city, request.top_n
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Discovery step failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed during discovery: {e}")

    if not companies_data:
        return CityRankingsResponse(
            status="no_companies",
            city=request.city,
            companies=[],
            discovery_html=discovery_html or f"<div>No companies found in {request.city}.</div>",
            analysis_summary={"message": "No companies discovered; nothing to analyze."},
            timestamp=datetime.now().isoformat(),
            total_analyzed=0,
        )

    # Step 2: analysis
    try:
        # IMPORTANT: match your analyzer's signature:
        # analyze_discovered_companies(companies_data, city, progress_callback=None)
        results = await analyzer.analyze_discovered_companies(
            companies_data, request.city
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Analysis step failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed during scoring: {e}")

    # Convert to response objects
    company_responses: List[SustainabilityDataResponse] = []
    for r in results:
        company_responses.append(
            SustainabilityDataResponse(
                company_name=r.company_name,
                sustainability_score=r.sustainability_score,
                environmental_score=r.environmental_score,
                social_score=r.social_score,
                governance_score=r.governance_score,
                esg_rating=r.esg_rating,
                location=r.location,
                industry=r.industry,
                key_strengths=r.key_strengths or [],
                key_risks=r.key_risks or [],
                recommendations=r.recommendations or [],
                summary=r.summary or "",
                data_quality=r.data_quality or None,
                scoring_explanations=r.scoring_explanations or None,
                last_updated=r.last_updated,
            )
        )

    # Summary
    analysis_summary: Dict[str, Any]
    if company_responses:
        avg_score = sum(c.sustainability_score for c in company_responses) / len(company_responses)
        top = max(company_responses, key=lambda c: c.sustainability_score)
        analysis_summary = {
            "average_sustainability_score": round(avg_score, 1),
            "top_performer": top.company_name,
            "top_score": top.sustainability_score,
            "companies_with_good_scores": sum(1 for c in company_responses if c.sustainability_score >= 65),
            "companies_with_poor_scores": sum(1 for c in company_responses if c.sustainability_score < 50),
        }
    else:
        analysis_summary = {"message": "No companies produced valid analysis results."}

    return CityRankingsResponse(
        status="ok",
        city=request.city,
        companies=company_responses,
        discovery_html=discovery_html or "",
        analysis_summary=analysis_summary,
        timestamp=datetime.now().isoformat(),
        total_analyzed=len(company_responses),
    )


@router.get("/health")
async def health_check():
    """Simple health check for the city rankings service."""
    try:
        analyzer = CityCompanyAnalyzer()
        ok = getattr(getattr(analyzer, "deep_search", None), "client", None) is not None
        return {
            "status": "healthy",
            "service": "city-rankings",
            "timestamp": datetime.now().isoformat(),
            "google_api_available": ok,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

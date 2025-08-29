"""
City Rankings API for Deep Research ESG Analysis
FastAPI router for city-based company sustainability rankings
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio
import json
from datetime import datetime
import logging

from app.core.deep_research_city_analyzer import CityCompanyAnalyzer
from app.models.city_rankings import SustainabilityData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class CityAnalysisRequest(BaseModel):
    city: str = Field(..., description="City name to analyze companies in", example="San Francisco")
    top_n: int = Field(default=10, ge=3, le=20, description="Number of companies to analyze")
    language: str = Field(default="en", pattern="^(en|de|it)$", description="Language for analysis output (en, de, it)")

class CompanyDiscoveryResponse(BaseModel):
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
    location: Optional[str]
    industry: Optional[str]
    key_strengths: List[str]
    key_risks: List[str]
    recommendations: List[str]
    summary: str
    data_quality: Optional[Dict[str, Any]]
    scoring_explanations: Optional[Dict[str, Any]]
    last_updated: str

class CityRankingsResponse(BaseModel):
    city: str
    companies: List[SustainabilityDataResponse]
    discovery_html: str
    analysis_summary: Dict[str, Any]
    timestamp: str
    total_analyzed: int

class AnalysisProgressResponse(BaseModel):
    status: str
    progress_percentage: float
    current_step: str
    companies_analyzed: int
    total_companies: int
    estimated_completion: Optional[str]

# Global storage for tracking analysis progress
analysis_progress = {}

@router.post("/city-rankings/discover", response_model=CompanyDiscoveryResponse)
async def discover_companies_in_city(request: CityAnalysisRequest):
    """
    Discover companies in a specified city
    
    This endpoint performs fast company discovery without full ESG analysis.
    Use this to see which companies were found before running the full analysis.
    """
    try:
        logger.info(f"Starting company discovery for {request.city}")
        
        analyzer = CityCompanyAnalyzer()
        companies_data, discovery_html = await analyzer.find_companies_in_city_fast(
            request.city, request.top_n, request.language
        )
        
        if not companies_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No companies found in {request.city}"
            )
        
        response = CompanyDiscoveryResponse(
            companies=companies_data,
            discovery_html=discovery_html,
            total_found=len(companies_data),
            city=request.city,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully discovered {len(companies_data)} companies in {request.city}")
        return response
        
    except Exception as e:
        logger.error(f"Error discovering companies in {request.city}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

@router.post("/city-rankings/analyze", response_model=CityRankingsResponse)
async def analyze_city_companies(request: CityAnalysisRequest, background_tasks: BackgroundTasks):
    """
    Perform complete ESG analysis of companies in a city
    
    This endpoint runs the full two-step process:
    1. Discover companies in the city
    2. Analyze each company's ESG performance with explainable AI
    
    Returns comprehensive rankings with detailed explanations.
    """
    analysis_id = f"{request.city}_{datetime.now().timestamp()}"
    
    try:
        logger.info(f"Starting full city analysis for {request.city} with {request.top_n} companies")
        
        # Initialize progress tracking
        analysis_progress[analysis_id] = {
            "status": "starting",
            "progress": 0.0,
            "current_step": "Initializing analysis",
            "companies_analyzed": 0,
            "total_companies": request.top_n,
            "start_time": datetime.now().isoformat()
        }
        
        analyzer = CityCompanyAnalyzer()
        
        # Step 1: Discover companies
        analysis_progress[analysis_id].update({
            "status": "discovering",
            "progress": 0.2,
            "current_step": f"Discovering companies in {request.city}"
        })
        
        companies_data, discovery_html = await analyzer.find_companies_in_city_fast(
            request.city, request.top_n, request.language
        )
        
        if not companies_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No companies found in {request.city}"
            )
        
        analysis_progress[analysis_id].update({
            "total_companies": len(companies_data),
            "progress": 0.3,
            "current_step": f"Found {len(companies_data)} companies, starting analysis"
        })
        
        # Step 2: Analyze companies with progress tracking
        def update_progress(percent, message):
            analysis_progress[analysis_id].update({
                "status": "analyzing",
                "progress": 0.3 + (0.6 * percent),  # 30% to 90%
                "current_step": message,
                "companies_analyzed": int(len(companies_data) * percent)
            })
        
        results = await analyzer.analyze_discovered_companies(
            companies_data, request.city, request.language, update_progress
        )
        
        # Step 3: Format results
        analysis_progress[analysis_id].update({
            "status": "finalizing",
            "progress": 0.95,
            "current_step": "Generating final rankings"
        })
        
        # Convert SustainabilityData to response format
        company_responses = []
        for result in results:
            company_response = SustainabilityDataResponse(
                company_name=result.company_name,
                sustainability_score=result.sustainability_score,
                environmental_score=result.environmental_score,
                social_score=result.social_score,
                governance_score=result.governance_score,
                esg_rating=result.esg_rating,
                location=result.location,
                industry=result.industry,
                key_strengths=result.key_strengths,
                key_risks=result.key_risks,
                recommendations=result.recommendations,
                summary=result.summary,
                data_quality=result.data_quality,
                scoring_explanations=result.scoring_explanations,
                last_updated=result.last_updated
            )
            company_responses.append(company_response)
        
        # Generate analysis summary
        if results:
            avg_score = sum(c.sustainability_score for c in results) / len(results)
            top_performer = results[0]
            analysis_summary = {
                "average_sustainability_score": round(avg_score, 1),
                "top_performer": top_performer.company_name,
                "top_score": top_performer.sustainability_score,
                "companies_with_good_scores": len([c for c in results if c.sustainability_score >= 65]),
                "companies_with_poor_scores": len([c for c in results if c.sustainability_score < 50]),
                "most_common_industry": max(set([c.industry for c in results if c.industry]), 
                                          key=[c.industry for c in results if c.industry].count) if results else "Unknown"
            }
        else:
            analysis_summary = {"error": "No companies successfully analyzed"}
        
        # Final response
        response = CityRankingsResponse(
            city=request.city,
            companies=company_responses,
            discovery_html=discovery_html,
            analysis_summary=analysis_summary,
            timestamp=datetime.now().isoformat(),
            total_analyzed=len(results)
        )
        
        # Update progress to complete
        analysis_progress[analysis_id].update({
            "status": "complete",
            "progress": 1.0,
            "current_step": f"Analysis complete! Ranked {len(results)} companies",
            "companies_analyzed": len(results),
            "completion_time": datetime.now().isoformat()
        })
        
        logger.info(f"Successfully completed city analysis for {request.city}: {len(results)} companies ranked")
        return response
        
    except Exception as e:
        # Update progress with error
        analysis_progress[analysis_id].update({
            "status": "error",
            "current_step": f"Error: {str(e)}",
            "error_time": datetime.now().isoformat()
        })
        
        logger.error(f"Error analyzing {request.city}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/city-rankings/progress/{analysis_id}", response_model=AnalysisProgressResponse)
async def get_analysis_progress(analysis_id: str):
    """
    Get the progress of an ongoing city analysis
    
    Use this endpoint to track the progress of a long-running analysis.
    """
    if analysis_id not in analysis_progress:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    progress_data = analysis_progress[analysis_id]
    
    # Calculate estimated completion
    estimated_completion = None
    if progress_data.get("start_time") and progress_data["progress"] > 0:
        try:
            start_time = datetime.fromisoformat(progress_data["start_time"])
            elapsed = (datetime.now() - start_time).total_seconds()
            if progress_data["progress"] > 0.1:  # Only estimate after some progress
                total_estimated = elapsed / progress_data["progress"]
                remaining = total_estimated - elapsed
                estimated_completion = (datetime.now().timestamp() + remaining)
        except:
            pass
    
    return AnalysisProgressResponse(
        status=progress_data["status"],
        progress_percentage=progress_data["progress"] * 100,
        current_step=progress_data["current_step"],
        companies_analyzed=progress_data["companies_analyzed"],
        total_companies=progress_data["total_companies"],
        estimated_completion=estimated_completion
    )

@router.get("/city-rankings/health")
async def health_check():
    """Health check endpoint for the city rankings service"""
    try:
        # Test basic functionality
        analyzer = CityCompanyAnalyzer()
        return {
            "status": "healthy",
            "service": "city-rankings",
            "timestamp": datetime.now().isoformat(),
            "google_api_available": hasattr(analyzer.deep_search, 'client') and analyzer.deep_search.client is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Cleanup endpoint to remove old progress data
@router.delete("/city-rankings/cleanup")
async def cleanup_old_progress():
    """Clean up old progress tracking data"""
    global analysis_progress
    
    # Remove progress data older than 1 hour
    current_time = datetime.now().timestamp()
    to_remove = []
    
    for analysis_id, data in analysis_progress.items():
        try:
            if "start_time" in data:
                start_time = datetime.fromisoformat(data["start_time"]).timestamp()
                if current_time - start_time > 3600:  # 1 hour
                    to_remove.append(analysis_id)
        except:
            to_remove.append(analysis_id)  # Remove invalid entries
    
    for analysis_id in to_remove:
        del analysis_progress[analysis_id]
    
    return {
        "cleaned_up": len(to_remove),
        "remaining": len(analysis_progress),
        "timestamp": datetime.now().isoformat()
    }

from fastapi import APIRouter, Depends
from typing import Dict, Any, List
import time
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models.report import Report
from app.core.store import risk_trends, get_all_companies

router = APIRouter()

@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get dashboard statistics"""
    # Query number of high-risk companies (score >= 70)
    high_risk_count = db.query(Report).filter(
        Report.overall_score >= 70
    ).count()
    
    # Query total number of reports
    total_reports = db.query(Report).count()
    
    return {
        "high_risk_companies": high_risk_count,
        "pending_reports": total_reports, 
        "high_priority_reports": min(9, high_risk_count // 3),
        "last_updated": int(time.time())
    }

@router.get("/dashboard/trends")
async def get_risk_trends() -> List[Dict[str, Any]]:
    """Get risk trend data"""
    return risk_trends

@router.get("/dashboard/companies")
async def get_companies_list(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get company list and risk ranking"""
    return get_all_companies(db)

from typing import Dict, Any, List
import time
import json
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.report import Report
from app.config import Base
from fastapi import Depends

# Database dependencies
def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# Dashboard global variables
dashboard_stats = {
    "high_risk_companies": 0,
    "pending_reports": 0,
    "high_priority_reports": 0,
    "last_updated": 0
}

# Analysis result storage
analysis_results_by_session = {}
company_reports_index = {}

# Risk trend data
risk_trends = [
    {"date": "2025-01-01", "risks": 5, "new_risks": 2},
    {"date": "2025-01-08", "risks": 7, "new_risks": 3},
    {"date": "2025-01-15", "risks": 6, "new_risks": 1},
    {"date": "2025-01-22", "risks": 9, "new_risks": 4},
    {"date": "2025-01-29", "risks": 12, "new_risks": 5},
    {"date": "2025-02-05", "risks": 15, "new_risks": 6},
]

# Get all company report list
def get_all_companies(db: Session = Depends(get_db_session)) -> List[Dict[str, Any]]:
    """Get all companies and their latest analysis reports"""
    # Query latest report for each company
    subquery = db.query(
        Report.company_name,
        Report.session_id,
        Report.overall_score,
        Report.risk_type,
        Report.analysis_time,
        Report.file_id
    ).order_by(
        Report.company_name,
        Report.analysis_time.desc()
    ).subquery()

    result = db.query(subquery).distinct(
        subquery.c.company_name
    ).all()

    companies = []
    for row in result:
        companies.append({
            "id": row.session_id,
            "name": row.company_name,
            "score": int(row.overall_score),
            "type": row.risk_type,
            "date": _format_date(row.analysis_time.timestamp()) if row.analysis_time else "2025-01-01",
            "session_count": db.query(Report).filter(
                Report.company_name == row.company_name
            ).count()
        })
    
    # Sort by risk score
    return sorted(companies, key=lambda x: x["score"], reverse=True)

def _get_main_risk_type(report: Dict[str, Any]) -> str:
    """Extract main risk type from report"""
    breakdown = report.get("breakdown", [])
    if not breakdown:
        return "Unknown type"
    
    # Find the highest scoring type
    max_score = 0
    main_type = "Unknown type"
    for item in breakdown:
        score = item.get("value", 0)
        if isinstance(score, str):
            try:
                score = float(score)
            except:
                score = 0
        if score > max_score:
            max_score = score
            main_type = item.get("type", "Unknown type")
    
    return main_type

def _format_date(timestamp: float) -> str:
    """Format timestamp to date string"""
    try:
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d")
    except:
        return "2025-01-01"

def update_dashboard_stats():
    """Update dashboard statistics"""
    global dashboard_stats
    
    # Calculate high-risk company count (score >= 70)
    high_risk_count = 0
    pending_count = len(analysis_results_by_session)
    
    for session_data in analysis_results_by_session.values():
        score = session_data.get("overall_score", 0)
        if isinstance(score, str):
            try:
                score = float(score)
            except:
                score = 0
        if score >= 70:
            high_risk_count += 1
    
    dashboard_stats.update({
        "high_risk_companies": high_risk_count,
        "pending_reports": pending_count,
        "high_priority_reports": max(9, high_risk_count // 3),
        "last_updated": time.time()
    })

from app.models.chat import ChatMessage, Conversation
from datetime import datetime

def store_analysis_result(session_id: str, company_name: str, data: Dict[str, Any]):
    """Store analysis results and update index"""
    # Add timestamp
    data["created_at"] = time.time()
    data["company_name"] = company_name
    
    # Store analysis results
    analysis_results_by_session[session_id] = data
    
    # Update company index
    if company_name not in company_reports_index:
        company_reports_index[company_name] = []
    if session_id not in company_reports_index[company_name]:
        company_reports_index[company_name].append(session_id)
    
    # Update dashboard statistics
    update_dashboard_stats()

def save_conversation(db: Session, conversation_id: str, user_id: str, messages: List[ChatMessage]):
    """Save conversation context to database"""
    try:
        # Convert message list to JSON storable format
        messages_data = [msg.dict() for msg in messages]
        
        # Create or update conversation record
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if conversation:
            # Update existing conversation
            conversation.messages = json.dumps(messages_data)
            conversation.updated_at = datetime.utcnow()
        else:
            # Create new conversation
            conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=json.dumps(messages_data),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(conversation)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Failed to save conversation: {str(e)}")
        return False

def get_conversation(db: Session, conversation_id: str) -> List[ChatMessage]:
    """Get conversation context from database"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            return []
            
        messages_data = json.loads(conversation.messages)
        return [ChatMessage(**msg) for msg in messages_data]
    except Exception as e:
        print(f"Failed to get conversation: {str(e)}")
        return []

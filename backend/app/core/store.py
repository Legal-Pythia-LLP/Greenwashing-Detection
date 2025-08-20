from typing import Dict, Any, List, Optional
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

# Vector store persistence
import os
from app.config import VECTOR_STORE_DIR
from app.core.vector_store import embedding_model

VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

def save_vector_store(session_id: str, vector_store):
    """Save vector store reference (Chroma auto-persists since 0.4.x)"""
    return vector_store
    
def load_vector_store(session_id: str):
    """Load persisted vector store from disk"""
    persist_path = VECTOR_STORE_DIR / session_id
    if not persist_path.exists():
        return None
    from langchain_community.vectorstores import Chroma
    return Chroma(
        persist_directory=str(persist_path),
        embedding_function=embedding_model
    )

# Session storage with TTL (24 hours)
from datetime import datetime, timedelta
session_store = {}  # {session_id: {"vector_store_path": str, "expires_at": datetime}}

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

def save_session(session_id: str, session_data: Dict, db: Session):
    """Save session with vector store and analysis results to database"""
    print(f"[SESSION DEBUG] Saving session {session_id} with data: {json.dumps(session_data, indent=2)}")
    
    # Validate required fields
    required_fields = ["vector_store_path", "company_name", "agent_config"]
    for field in required_fields:
        if field not in session_data:
            print(f"[SESSION WARNING] Missing required field: {field} in session data")
            print(f"[SESSION DEBUG] Full session data: {json.dumps(session_data, indent=2)}")
            return False

    try:
        # Include agent configuration in session data
        from app.core.esg_analysis import agent_executors
        if session_id in agent_executors:
            agent = agent_executors[session_id]
            session_data["agent_config"] = {
                "company_name": agent.tools[1].company_name,
                "tools": [tool.name for tool in agent.tools],
                "vector_store_path": session_data.get("vector_store_path", ""),
                "session_id": session_id
            }
            # Ensure required fields are present
            session_data["company_name"] = agent.tools[1].company_name  # add company_name
            if "vector_store_path" not in session_data:
                session_data["vector_store_path"] = f"data/vector_stores/{session_id}"
        
        # Convert session data to proper message format
        from app.models.chat import ChatMessage
        from datetime import datetime
        message = ChatMessage(
            content=json.dumps(session_data),
            sender="system",
            timestamp=datetime.utcnow()
        )
        messages_data = [message.dict()]
        session_json = json.dumps(messages_data)
        
        # Check if session exists
        existing = db.query(Conversation).filter(
            Conversation.conversation_id == session_id
        ).first()
        
        if existing:
            # Update existing session
            existing.messages = session_json
            existing.updated_at = datetime.utcnow()
        else:
            # Create new session
            new_session = Conversation(
                conversation_id=session_id,
                user_id="system",
                messages=session_json,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_session)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"[SESSION ERROR] Failed to save session: {str(e)}")
        return False

def get_session(session_id: str, db: Session = Depends(get_db_session)) -> Optional[Dict]:
    """Get session data from database if exists"""
    try:
        print(f"[SESSION DEBUG] Looking up session {session_id}")
        print(f"[SESSION DEBUG] DB connection active: {db.is_active}")
        
        session = db.query(Conversation).filter(
            Conversation.conversation_id == session_id
        ).first()
        
        if not session:
            print(f"[SESSION DEBUG] No session found for {session_id}")
            print(f"[SESSION DEBUG] Available sessions: {db.query(Conversation.conversation_id).all()}")
            return None
            
        print(f"[SESSION DEBUG] Found session with {len(session.messages)} bytes of data")
        print(f"[SESSION DEBUG] Session created at: {session.created_at}, updated at: {session.updated_at}")
        
        try:
            messages_data = json.loads(session.messages)
            
            # Handle both old (direct session_data) and new (ChatMessage list) formats
            if isinstance(messages_data, list) and len(messages_data) > 0:
                # New format - extract session_data from first message content
                session_data = json.loads(messages_data[0].get("content", "{}"))
            else:
                # Old format - use messages_data directly
                session_data = messages_data
                
            print(f"[SESSION DEBUG] Successfully parsed session data for {session_id}")
            print(f"[SESSION DEBUG] Session data type: {type(session_data)}")
        except Exception as e:
            print(f"[SESSION ERROR] Failed to parse session messages: {str(e)}")
            print(f"[SESSION DEBUG] Raw messages (first 200 chars): {session.messages[:200]}")
            return None
        
        # Rebuild agent if config exists
        if "agent_config" in session_data:
            print(f"[AGENT DEBUG] Found agent config in session data")
            print(f"[AGENT DEBUG] Agent config: {json.dumps(session_data['agent_config'], indent=2)}")
            
            from app.core.esg_analysis import create_esg_agent, agent_executors
            from app.core.vector_store import load_vector_store
            
            if session_id not in agent_executors:
                print(f"[AGENT DEBUG] Need to rebuild agent for session {session_id}")
                vector_store = load_vector_store(session_id)
                
                if vector_store:
                    print(f"[AGENT DEBUG] Vector store loaded successfully for {session_id}")
                    try:
                        agent = create_esg_agent(
                            session_id,
                            vector_store,
                            session_data["agent_config"]["company_name"]
                        )
                        agent_executors[session_id] = agent
                        print(f"[AGENT REBUILD] Successfully rebuilt agent for session {session_id}")
                        print(f"[AGENT DEBUG] Agent tools: {[tool.name for tool in agent.tools]}")
                    except Exception as e:
                        print(f"[AGENT ERROR] Failed to rebuild agent: {str(e)}")
                        return session_data
                else:
                    print(f"[AGENT WARNING] No vector store found for {session_id}")
            else:
                print(f"[AGENT DEBUG] Agent already exists for session {session_id}")
        
        return session_data
    except Exception as e:
        print(f"[SESSION ERROR] Failed to get session {session_id}: {str(e)}")
        print(f"[SESSION DEBUG] Current DB state: {db.is_active}")
        return None

def save_conversation(db: Session, conversation_id: str, user_id: str, messages: List[ChatMessage]):
    """Save conversation context to database"""
    print(f"\n===== DB SAVE START =====\n"
          f"Conversation: {conversation_id}\n"
          f"User: {user_id}\n"
          f"Message count: {len(messages)}\n"
          f"=========================")
    try:
        # Convert message list to JSON storable format
        print("[DB] Converting messages to JSON format")
        messages_data = [msg.dict() for msg in messages]
        
        # Create or update conversation record
        print(f"[DB] Querying conversation: {conversation_id}")
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
        print("[DB] Conversation saved successfully")
        print("===== DB SAVE END =====")
        return True
    except Exception as e:
        db.rollback()
        print(f"[DB ERROR] Failed to save conversation: {str(e)}")
        print("===== DB SAVE END WITH ERROR =====")
        return False

def get_conversation(db: Session, conversation_id: str) -> List[ChatMessage]:
    """Get conversation context from database"""
    try:
        print(f"\n[CONVERSATION DEBUG] Loading conversation {conversation_id}")
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            print(f"[CONVERSATION DEBUG] No conversation record found for {conversation_id}")
            return []
            
        if not conversation.messages:
            print(f"[CONVERSATION DEBUG] Empty messages for conversation {conversation_id}")
            return []
            
        try:
            print(f"[CONVERSATION DEBUG] Raw messages length: {len(conversation.messages)}")
            messages_data = json.loads(conversation.messages)
            
            if not isinstance(messages_data, list):
                print(f"[CONVERSATION DEBUG] Messages data is not a list: {type(messages_data)}")
                return []
                
            print(f"[CONVERSATION DEBUG] Parsed {len(messages_data)} messages")
            
            messages = []
            for idx, msg in enumerate(messages_data):
                try:
                    messages.append(ChatMessage.from_dict(msg))
                    print(f"[CONVERSATION DEBUG] Successfully parsed message {idx + 1}")
                except Exception as e:
                    print(f"[CONVERSATION ERROR] Failed to parse message {idx + 1}: {str(e)}")
                    print(f"[CONVERSATION DEBUG] Problematic message: {msg}")
                    
            print(f"[CONVERSATION DEBUG] Returning {len(messages)} valid messages")
            return messages
            
        except json.JSONDecodeError as e:
            print(f"[CONVERSATION ERROR] JSON decode failed: {str(e)}")
            print(f"[CONVERSATION DEBUG] Raw messages: {conversation.messages[:200]}...")
            return []
    except Exception as e:
        print(f"Failed to get conversation: {str(e)}")
        return []

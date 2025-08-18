from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import StreamingResponse, JSONResponse
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import ChatBaseMessage, ChatMessage
from app.core.esg_analysis import agent_executors
from app.core.store import save_conversation, get_conversation, get_session, load_vector_store
from app.db import get_db

router = APIRouter()

@router.get("/get_conversation/{session_id}")
async def get_full_conversation(
    session_id: str,
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Get full conversation history for a session.
    - Filter out system messages
    - If no user/assistant messages, automatically add a welcome assistant message
    """
    print(f"\n===== GET CONVERSATION REQUEST =====\nSession: {session_id}\n=============================")
    
    conversation = get_conversation(db, session_id)
    print(f"[DB] Loaded {len(conversation)} total messages")
    
    # Keep only user and assistant messages
    messages = [
        {
            "sender": msg.sender,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in conversation if msg.sender in ("user", "assistant")
    ]
    
    # Get company name from session if available
    session_data = get_session(session_id, db)
    company_name = session_data.get("company_name") if session_data else "the company"
    
    # If there are no messages, add an assistant welcome message
    if not messages:
        welcome_msg = {
            "sender": "assistant",
            "content": f"Hello, I am the ESG smart assistant for {company_name}. I can help you analyze ESG risks and greenwashing issues.",
            "timestamp": datetime.utcnow().isoformat()
        }
        messages.append(welcome_msg)
        print("[DB] Added assistant welcome message for empty session")
    
    return JSONResponse({
        "session_id": session_id,
        "messages": messages
    })


@router.post("/chat")
async def chat_with_agent(
    json_data: ChatBaseMessage,
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """Chat with the ESG analysis agent with context support"""
    print(f"\n===== CHAT REQUEST START =====\n"
          f"Session: {json_data.session_id}\n"
          f"User: {json_data.user_id or 'anonymous'}\n"
          f"Message: {json_data.message[:100]}...\n"
          f"=============================")
          
    user_message = json_data.message
    session_id = json_data.session_id
    conversation_id = json_data.conversation_id or session_id
    user_id = json_data.user_id or "anonymous"
    
    # Get conversation history
    print(f"[DB] Loading conversation: {conversation_id}")
    conversation = get_conversation(db, conversation_id)
    print(f"[DB] Loaded {len(conversation)} history messages")
    
    # Add user message to history
    conversation.append(ChatMessage(
        content=user_message,
        sender="user",
        timestamp=datetime.now()
    ))

    # Get agent and session
    print(f"[AGENT] Looking up agent for session: {session_id}")
    session = get_session(session_id, db)
    agent = agent_executors.get(session_id)
    
    print(f"[AGENT DEBUG] Session lookup result: {'found' if session else 'not found'}")
    print(f"[AGENT DEBUG] Agent lookup result: {'found' if agent else 'not found'}")
    print(f"[AGENT DEBUG] Current active sessions: {list(agent_executors.keys())}")
    
    # Recreate agent if session exists but agent is missing
    if session and not agent and isinstance(session, dict):
        print(f"[AGENT] Attempting to recreate agent for session: {session_id}")
        print(f"[AGENT DEBUG] Session data keys: {session.keys()}")
        
        required_fields = ["vector_store_path", "company_name"]
        missing_fields = [field for field in required_fields if field not in session]
        
        if missing_fields:
            print(f"[AGENT ERROR] Missing required fields to recreate agent: {missing_fields}")
        else:
            vector_store = load_vector_store(session_id)
            print(f"[VECTOR STORE DEBUG] Vector store {'found' if vector_store else 'not found'}")
            
            if vector_store:
                try:
                    from app.core.esg_analysis import create_esg_agent
                    agent = create_esg_agent(
                        session_id,
                        vector_store,
                        session["company_name"]
                    )
                    agent_executors[session_id] = agent
                    print(f"[AGENT DEBUG] Agent successfully recreated for session: {session_id}")
                except Exception as e:
                    print(f"[AGENT ERROR] Failed to recreate agent: {str(e)}")
            else:
                print("[AGENT ERROR] Vector store not found - cannot recreate agent")
    
    if not agent or not session:
        print(f"[AGENT ERROR] No valid session found for: {session_id}")
        print(f"[AGENT DEBUG] Current active sessions: {list(agent_executors.keys())}")
        raise HTTPException(
            status_code=400, 
            detail="No active analysis session found. Please upload a document first."
        )
    
    vector_store = load_vector_store(session_id)
    if not vector_store:
        print(f"[VECTOR STORE ERROR] No vector store found for session: {session_id}")
        raise HTTPException(
            status_code=400,
            detail="No vector store found for this session. Please upload a document first."
        )
    print(f"[AGENT] Found active agent for session")

    async def generate_response():
        try:
            print(f"[RESPONSE] Generating response with {len(conversation)} context messages")
            context = "\n".join([f"{msg.sender}: {msg.content}" for msg in conversation[-6:]])
            full_prompt = (
                "You are an ESG analysis assistant. Provide detailed, specific answers based on the conversation history.\n\n"
                f"Conversation History:\n{context}\n\n"
                f"User Question: {user_message}\n\n"
                "Assistant Response:"
            )
            enhanced_prompt = (
                f"{full_prompt}\n\n"
                f"Document Context: Use the vector store with session ID {session_id} for document retrieval and analysis."
            )
            response = agent.run(enhanced_prompt)
            
            if not response or len(response) < 10:
                response = (
                    "I can provide detailed analysis on:\n"
                    "- Specific company ESG reports\n"
                    "- Greenwashing risk indicators\n"
                    "- Industry benchmarks\n"
                    "- Report analysis requests\n\n"
                    "Could you clarify or provide more details about your request?"
                )
            
            assistant_msg = ChatMessage(
                content=response,
                sender="assistant",
                timestamp=datetime.now()
            )
            conversation.append(assistant_msg)
            save_conversation(db, conversation_id, user_id, conversation)
            
            for chunk in response.split():
                yield chunk + " "
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate_response(), media_type="text/plain")

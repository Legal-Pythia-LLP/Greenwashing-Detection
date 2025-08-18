from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import StreamingResponse
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import ChatBaseMessage, ChatMessage
from app.core.esg_analysis import agent_executors
from app.core.store import save_conversation, get_conversation
from app.db import get_db

router = APIRouter()

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

    # Get agent
    print(f"[AGENT] Looking up agent for session: {session_id}")
    agent = agent_executors.get(session_id)
    if not agent:
        print(f"[AGENT ERROR] No agent found for session: {session_id}")
        print(f"[AGENT DEBUG] Current active sessions: {list(agent_executors.keys())}")
        raise HTTPException(status_code=400, detail="No analysis session found")
    print(f"[AGENT] Found active agent for session")

    async def generate_response():
        try:
            print(f"[RESPONSE] Generating response with {len(conversation)} context messages")
            # Include conversation history with more context
            context = "\n".join([
                f"{msg.sender}: {msg.content}" 
                for msg in conversation[-6:]  # Last 3 exchanges
            ])
            print(f"[RESPONSE] Context:\n{context[:200]}...")
            
            full_prompt = (
                "You are an ESG analysis assistant. Provide detailed, specific answers based on the conversation history. "
                "When asked about companies, check if we have analysis data. For general questions, provide thorough explanations.\n\n"
                f"Conversation History:\n{context}\n\n"
                f"User Question: {user_message}\n\n"
                "Assistant Response:"
            )
            
            print(f"[AGENT] Running prompt (truncated):\n{full_prompt[:200]}...")
            response = agent.run(full_prompt)
            print(f"[AGENT] Raw response (truncated):\n{response[:200]}...")
            
            if not response or len(response) < 10:  # Fallback if response is too short
                print("[AGENT WARNING] Response too short, using fallback")
                response = (
                    "I can provide detailed analysis on:\n"
                    "- Specific company ESG reports\n"
                    "- Greenwashing risk indicators\n"
                    "- Industry benchmarks\n"
                    "- Report analysis requests\n\n"
                    "Could you clarify or provide more details about your request?"
                )
            
            # Add assistant response to history
            assistant_msg = ChatMessage(
                content=response,
                sender="assistant",
                timestamp=datetime.now()
            )
            conversation.append(assistant_msg)
            print(f"[DB] Saving conversation with {len(conversation)} messages")
            try:
                save_conversation(db, conversation_id, user_id, conversation)
                print("[DB] Conversation saved successfully")
            except Exception as e:
                print(f"[DB ERROR] Failed to save conversation: {str(e)}")
                raise
            
            for chunk in response.split():
                yield chunk + " "
        except Exception as e:
            yield f"Error: {str(e)}"

    print("[RESPONSE] Returning streaming response")
    try:
        return StreamingResponse(
            generate_response(),
            media_type="text/plain"
        )
    except Exception as e:
        print(f"[RESPONSE ERROR] Streaming failed: {str(e)}")
        raise
    finally:
        print("===== CHAT REQUEST END =====")

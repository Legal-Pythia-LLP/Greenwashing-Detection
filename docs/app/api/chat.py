from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse
from app.models import ChatBaseMessage
from app.core.esg_analysis import agent_executors

router = APIRouter()

@router.post("/chat")
async def chat_with_agent(json_data: ChatBaseMessage) -> StreamingResponse:
    """Chat with the ESG analysis agent"""
    user_message = json_data.message
    session_id = json_data.session_id
    # Get agent
    agent = agent_executors.get(session_id)
    if not agent:
        raise HTTPException(status_code=400, detail="No analysis session found")
    # Create streaming response
    async def generate_response():
        try:
            # Use agent to respond
            response = agent.run(user_message)
            # Stream the response
            for chunk in response.split():
                yield f"data: {chunk} \n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    ) 
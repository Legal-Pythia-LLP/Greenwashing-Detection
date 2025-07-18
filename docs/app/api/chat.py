from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse
from app.models.pydantic_models import ChatBaseMessage
from app.utils.language import detect_language
from app.services.agent import create_multilingual_esg_agent
from app.services.memory import document_stores, agent_executors
import asyncio

router = APIRouter()

@router.post("/chat")
async def chat_with_agent_multilingual(json_data: ChatBaseMessage) -> StreamingResponse:
    user_message = json_data.message
    session_id = json_data.session_id
    vector_store = document_stores.get(session_id)
    if not vector_store:
        raise HTTPException(status_code=400, detail="No analysis session found")
    message_language = detect_language(user_message)
    agent = agent_executors.get(session_id)
    if not agent:
        agent = create_multilingual_esg_agent(session_id, vector_store, message_language)
        agent_executors[session_id] = agent
    async def generate_response():
        try:
            contextualized_message = f"""
            User language: {message_language}
            Please respond in {message_language}.
            User message: {user_message}
            """
            response = agent.run(contextualized_message)
            words = response.split()
            for i, word in enumerate(words):
                yield f"data: {word}"
                if i < len(words) - 1:
                    yield f" "
                await asyncio.sleep(0.01)
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    ) 
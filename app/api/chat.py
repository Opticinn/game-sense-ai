# app/api/chat.py
from fastapi  import APIRouter
from app.schemas          import ChatRequest, ChatResponse
from app.services.rag_chat import rag_chat_engine

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask(payload: ChatRequest):
    """
    Endpoint utama chat — diproses oleh LangChain Agent + Qwen2.5 7B.
    Agent otomatis pilih tools yang tepat berdasarkan query.
    """
    result = rag_chat_engine.ask(
        query   = payload.query,
        user_id = payload.user_id,
    )

    return ChatResponse(
        answer     = result["answer"],
        sources    = result["sources"],
        is_personal= result["is_personal"],
    )
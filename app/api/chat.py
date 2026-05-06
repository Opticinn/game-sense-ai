# app/api/chat.py
from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask(payload: ChatRequest):
    """
    Endpoint utama chat — diterima oleh LangChain Agent.
    Agent akan otomatis pilih tools yang tepat berdasarkan query.
    Untuk sekarang return placeholder — akan diisi saat Phase RAG + Agent.
    """
    # Deteksi apakah pertanyaan tentang mod
    mod_keywords = ["mod", "modding", "workshop", "nexus"]
    is_mod_query = any(kw in payload.query.lower() for kw in mod_keywords)

    if is_mod_query:
        answer = (
            "Saya akan carikan game terbaik untuk dimainkan dengan mod! "
            "Fitur agent sedang dalam pengembangan — akan segera hadir di Phase 5."
        )
    else:
        answer = (
            f"Kamu bertanya: '{payload.query}'. "
            "Agent GameSense AI sedang dalam pengembangan — akan segera hadir di Phase 5."
        )

    return ChatResponse(
        answer=answer,
        sources=[],
        is_personal=payload.user_id is not None,
    )
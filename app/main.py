# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import games, trending, chat

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="GameSense AI",
    description="Intelligent Game Recommendation Platform",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(games.router,    prefix="/games",    tags=["Games"])
app.include_router(trending.router, prefix="/trending", tags=["Trending"])
app.include_router(chat.router,     prefix="/chat",     tags=["Chat"])


@app.get("/")
def root():
    return {"message": "GameSense AI is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
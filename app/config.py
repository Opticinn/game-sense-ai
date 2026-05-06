from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ───────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://gamesense:gamesense@localhost:5438/gamesense"

    # ── Redis ──────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Steam API ──────────────────────────────────────────
    STEAM_API_KEY: str = ""

    # ── YouTube ────────────────────────────────────────────
    YOUTUBE_API_KEY: str = ""

    # ── Reddit ─────────────────────────────────────────────
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "GameSenseAI/1.0"

    # ── LLM: Qwen2.5 7B via Ollama ────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:7b"

    # ── ChromaDB ───────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # ── MLflow ─────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # ── Telegram ───────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── JWT Auth ───────────────────────────────────────────
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"          # baca dari file .env
        env_file_encoding = "utf-8"
        extra = "ignore"           # abaikan variable .env yang tidak terdaftar


@lru_cache
def get_settings() -> Settings:
    """
    Dibuat sekali, disimpan di memori, dipakai berkali-kali.
    Seperti buku yang sudah dibuka — tidak perlu dibuka lagi dari awal.
    """
    return Settings()


# Shortcut — tinggal import 'settings' dari mana saja
settings = get_settings()
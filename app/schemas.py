# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── BASE SCHEMAS ───────────────────────────────────────────────────────────────
# "Base" = field yang dipakai bersama oleh Create dan Response

class GameBase(BaseModel):
    title:              str                 = Field(..., min_length=1, max_length=255)
    description:        Optional[str]       = None
    short_desc:         Optional[str]       = Field(None, max_length=500)
    developer:          Optional[str]       = None
    publisher:          Optional[str]       = None
    genres:             List[str]           = []
    tags:               List[str]           = []
    price_usd:          Optional[float]     = Field(None, ge=0)  # ge=0 artinya >= 0, tidak boleh minus
    price_idr:          Optional[int]       = None
    is_free:            bool                = False
    has_mod_support:    bool                = False
    header_image:       Optional[str]       = None
    trailer_url:        Optional[str]       = None
    steam_id:           Optional[str]       = None
    epic_id:            Optional[str]       = None


# ── CREATE SCHEMA ──────────────────────────────────────────────────────────────
# Dipakai saat user POST /games — data yang DIKIRIM user
class GameCreate(GameBase):
    pass  # sama persis dengan GameBase untuk sekarang


# ── UPDATE SCHEMA ──────────────────────────────────────────────────────────────
# Dipakai saat user PUT /games/{id} — semua field OPSIONAL
# Karena user mungkin hanya mau update sebagian field saja
class GameUpdate(BaseModel):
    title:           Optional[str]   = None
    description:     Optional[str]   = None
    price_usd:       Optional[float] = Field(None, ge=0)
    price_idr:       Optional[int]   = None
    genres:          Optional[List[str]] = None
    tags:            Optional[List[str]] = None
    has_mod_support: Optional[bool]  = None
    sentiment_score: Optional[float] = Field(None, ge=0, le=1)  # 0.0 - 1.0
    trending_score:  Optional[float] = Field(None, ge=0, le=1)


# ── RESPONSE SCHEMA ────────────────────────────────────────────────────────────
# Dipakai saat API MENJAWAB — data yang DIKIRIM balik ke user
# Lebih lengkap dari GameCreate karena sudah ada id, timestamps, dll
class GameResponse(GameBase):
    id:              int
    sentiment_score: Optional[float] = None
    trending_score:  Optional[float] = None
    steam_review_score: Optional[float] = None
    steam_review_count: Optional[int]   = None
    created_at:      datetime
    updated_at:      datetime

    # model_config = memberitahu Pydantic untuk baca data dari SQLAlchemy object
    # Tanpa ini, Pydantic tidak bisa baca object Game dari database
    model_config = {"from_attributes": True}


# ── LIST RESPONSE ──────────────────────────────────────────────────────────────
# Dipakai saat API mengembalikan BANYAK game sekaligus
# Disertai info pagination (halaman berapa, total berapa)
class GameListResponse(BaseModel):
    total: int
    page:  int
    limit: int
    games: List[GameResponse]


# ── HEALTH CHECK ───────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status:   str
    database: str
    version:  str
    
    
    
# ── TRENDING ───────────────────────────────────────────────────────────────────
class TrendingGame(BaseModel):
    id:              int
    title:           str
    genres:          List[str]       = []
    tags:            List[str]       = []
    price_usd:       Optional[float] = None
    price_idr:       Optional[int]   = None
    is_free:         bool            = False
    has_mod_support: bool            = False
    header_image:    Optional[str]   = None
    sentiment_score: Optional[float] = None
    trending_score:  Optional[float] = None
    steam_review_score:    Optional[float] = None
    steam_concurrent_peak: Optional[int]   = None

    model_config = {"from_attributes": True}


class TrendingResponse(BaseModel):
    games: List[TrendingGame]
    total: int


# ── CHAT ───────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query:   str  = Field(..., min_length=1, max_length=1000)
    user_id: Optional[str] = None  # None = user tidak login


class ChatResponse(BaseModel):
    answer:    str
    sources:   List[str] = []   # game apa saja yang dijadikan referensi
    is_personal: bool    = False # True kalau rekomendasi personal (user login)
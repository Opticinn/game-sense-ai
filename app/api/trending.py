# app/api/trending.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models   import Game
from app.schemas  import TrendingResponse, TrendingGame

router = APIRouter()


@router.get("/", response_model=TrendingResponse)
async def get_trending(
    limit:           int           = Query(20, ge=1, le=50),
    genre:           Optional[str] = Query(None),
    has_mod_support: Optional[bool] = Query(None),
    is_free:         Optional[bool] = Query(None),
    db:              AsyncSession  = Depends(get_db),
):
    """
    Ambil game yang sedang trending.
    Diurutkan berdasarkan trending_score tertinggi.
    """
    query = select(Game)

    # Filter opsional
    if genre:
        query = query.where(Game.genres.contains([genre]))
    if has_mod_support is not None:
        query = query.where(Game.has_mod_support == has_mod_support)
    if is_free is not None:
        query = query.where(Game.is_free == is_free)

    # Urutkan: trending_score tertinggi dulu
    # nullslast = game yang belum punya trending_score ditaruh paling bawah
    query  = query.order_by(
        Game.trending_score.desc().nullslast(),
        Game.steam_review_score.desc().nullslast(),
    ).limit(limit)

    result = await db.execute(query)
    games  = result.scalars().all()

    return TrendingResponse(games=games, total=len(games))


@router.get("/mod", response_model=TrendingResponse)
async def get_trending_mod_games(
    limit: int          = Query(10, ge=1, le=50),
    db:    AsyncSession = Depends(get_db),
):
    """
    Khusus: game trending yang punya mod support aktif.
    Dipakai agent saat user tanya 'game seru dengan mod?'
    """
    query = select(Game).where(
        Game.has_mod_support == True
    ).order_by(
        Game.trending_score.desc().nullslast(),
        Game.sentiment_score.desc().nullslast(),
    ).limit(limit)

    result = await db.execute(query)
    games  = result.scalars().all()

    return TrendingResponse(games=games, total=len(games))
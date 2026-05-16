# app/api/games.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, cast, String
from typing import Optional

from app.database import get_db
from app.models   import Game
from app.schemas  import GameCreate, GameUpdate, GameResponse, GameListResponse
from app.services.cache import cache_get, cache_set, cache_delete, make_cache_key

router = APIRouter()

# TTL (detik)
TTL_LIST    = 300   # 5 menit — list game
TTL_SEARCH  = 300   # 5 menit — hasil search
TTL_SIMILAR = 600   # 10 menit — similar games (NCF mahal)


# ── GET /games ────────────────────────────────────────────────────────────────
@router.get("/", response_model=GameListResponse)
async def get_games(
    page:            int            = Query(1, ge=1),
    limit:           int            = Query(20, ge=1, le=100),
    genre:           Optional[str]  = Query(None),
    has_mod_support: Optional[bool] = Query(None),
    is_free:         Optional[bool] = Query(None),
    db:              AsyncSession   = Depends(get_db),
):
    # Cek cache dulu
    cache_key = make_cache_key(
        "games:list",
        page=page, limit=limit,
        genre=genre, has_mod=has_mod_support, free=is_free
    )
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Query database
    query = select(Game)
    if genre:
        query = query.where(Game.genres.contains([genre]))
    if has_mod_support is not None:
        query = query.where(Game.has_mod_support == has_mod_support)
    if is_free is not None:
        query = query.where(Game.is_free == is_free)

    count_query  = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total        = total_result.scalar()

    offset = (page - 1) * limit
    query  = query.offset(offset).limit(limit).order_by(Game.trending_score.desc().nullslast())
    result = await db.execute(query)
    games  = result.scalars().all()

    response = GameListResponse(total=total, page=page, limit=limit, games=games)

    # Simpan ke cache
    await cache_set(cache_key, response.model_dump(), ttl=TTL_LIST)

    return response


# ── GET /games/search ─────────────────────────────────────────────────────────
@router.get("/search", response_model=GameListResponse)
async def search_games(
    q:     str          = Query(..., min_length=1),
    limit: int          = Query(10, ge=1, le=50),
    db:    AsyncSession = Depends(get_db),
):
    # Cek cache
    cache_key = make_cache_key("games:search", q=q.lower(), limit=limit)
    cached = await cache_get(cache_key)
    if cached:
        return cached

    combined_query = select(Game).where(
        or_(
            Game.title.ilike(f"%{q}%"),
            cast(Game.genres, String).ilike(f"%{q}%"),
            cast(Game.tags,   String).ilike(f"%{q}%"),
        )
    ).limit(limit)

    result = await db.execute(combined_query)
    games  = result.scalars().all()
    response = GameListResponse(total=len(games), page=1, limit=limit, games=games)

    # Simpan ke cache
    await cache_set(cache_key, response.model_dump(), ttl=TTL_SEARCH)

    return response


# ── GET /games/youtube/{game_id} ──────────────────────────────────────────────
@router.get("/youtube/{game_id}")
async def get_game_videos(
    game_id: int,
    db:      AsyncSession = Depends(get_db),
):
    from app.services.scrapers.youtube_scraper import youtube_scraper

    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game tidak ditemukan")

    videos = await youtube_scraper.search_videos(
        game_name  = game.title,
        video_type = "gameplay",
        max_results= 3,
    )
    return {"videos": videos, "total": len(videos)}


# ── GET /games/similar/{game_id} ──────────────────────────────────────────────
@router.get("/similar/{game_id}")
async def get_similar_games(
    game_id: int,
    limit:   int          = Query(6, ge=1, le=20),
    db:      AsyncSession = Depends(get_db),
):
    import random
    from app.services.ncf_recommender import ncf_recommender

    # Cek cache
    cache_key = make_cache_key("games:similar", game_id=game_id, limit=limit)
    cached = await cache_get(cache_key)
    if cached:
        return cached

    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game tidak ditemukan")

    results = await ncf_recommender.get_similar_games(game, db, limit=limit * 3)
    random.shuffle(results)
    response = {"games": results[:limit], "total": limit}

    # Simpan ke cache
    await cache_set(cache_key, response, ttl=TTL_SIMILAR)

    return response


# ── GET /games/{id} ───────────────────────────────────────────────────────────
@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: int,
    db:      AsyncSession = Depends(get_db),
):
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game dengan id {game_id} tidak ditemukan")
    return game


# ── POST /games ───────────────────────────────────────────────────────────────
@router.post("/", response_model=GameResponse, status_code=201)
async def create_game(
    payload: GameCreate,
    db:      AsyncSession = Depends(get_db),
):
    game = Game(**payload.model_dump())
    db.add(game)
    await db.flush()
    await db.refresh(game)
    # Invalidate list cache
    await cache_delete("games:list:*")
    return game


# ── PUT /games/{id} ───────────────────────────────────────────────────────────
@router.put("/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: int,
    payload: GameUpdate,
    db:      AsyncSession = Depends(get_db),
):
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game dengan id {game_id} tidak ditemukan")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(game, field, value)

    await db.flush()
    await db.refresh(game)
    # Invalidate semua cache yang berkaitan
    await cache_delete("games:list:*")
    await cache_delete(f"games:similar:*")
    return game


# ── DELETE /games/{id} ────────────────────────────────────────────────────────
@router.delete("/{game_id}", status_code=204)
async def delete_game(
    game_id: int,
    db:      AsyncSession = Depends(get_db),
):
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game dengan id {game_id} tidak ditemukan")
    await db.delete(game)
    await cache_delete("games:list:*")
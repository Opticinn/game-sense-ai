# app/api/games.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models   import Game
from app.schemas  import GameCreate, GameUpdate, GameResponse, GameListResponse

# APIRouter = kumpulan endpoint yang dikelompokkan
# Seperti satu meja resepsionis khusus urusan "games"
router = APIRouter()


# ── GET /games ─────────────────────────────────────────────────────────────────
@router.get("/", response_model=GameListResponse)
async def get_games(
    page:            int            = Query(1, ge=1),
    limit:           int            = Query(20, ge=1, le=100),
    genre:           Optional[str]  = Query(None),
    has_mod_support: Optional[bool] = Query(None),
    is_free:         Optional[bool] = Query(None),
    db:              AsyncSession   = Depends(get_db),
):
    """
    Ambil daftar game dengan filter opsional.
    Contoh: GET /games?genre=RPG&has_mod_support=true&page=1&limit=20
    """
    # Mulai query — seperti "SELECT * FROM games"
    query = select(Game)

    # Tambah filter kalau ada
    # JSON column pakai operator 'contains' untuk cek isi list
    if genre:
        query = query.where(Game.genres.contains([genre]))
    if has_mod_support is not None:
        query = query.where(Game.has_mod_support == has_mod_support)
    if is_free is not None:
        query = query.where(Game.is_free == is_free)

    # Hitung total data (untuk info pagination)
    count_query  = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total        = total_result.scalar()

    # Ambil data dengan pagination
    # offset = lewati berapa baris (halaman 2 = lewati 20 baris pertama)
    offset = (page - 1) * limit
    query  = query.offset(offset).limit(limit).order_by(Game.trending_score.desc().nullslast())
    result = await db.execute(query)
    games  = result.scalars().all()

    return GameListResponse(total=total, page=page, limit=limit, games=games)


# ── GET /games/search ──────────────────────────────────────────────────────────
@router.get("/search", response_model=GameListResponse)
async def search_games(
    q:     str         = Query(..., min_length=1),
    limit: int         = Query(10, ge=1, le=50),
    db:    AsyncSession = Depends(get_db),
):
    """Cari game berdasarkan judul, genre, atau tags."""
    # Cari di judul
    title_query = select(Game).where(
        Game.title.ilike(f"%{q}%")
    )

    # Cari di genres dan tags (JSON contains)
    genre_query = select(Game).where(
        Game.genres.cast(db.bind.dialect.name and __import__('sqlalchemy').String).ilike(f"%{q}%")
    )

    result = await db.execute(title_query.limit(limit))
    games  = result.scalars().all()

    # Kalau hasil title kurang dari limit, tambah dari genre/tag search
    if len(games) < limit:
        from sqlalchemy import or_, cast, String
        combined_query = select(Game).where(
            or_(
                Game.title.ilike(f"%{q}%"),
                cast(Game.genres, String).ilike(f"%{q}%"),
                cast(Game.tags,   String).ilike(f"%{q}%"),
            )
        ).limit(limit)

        result = await db.execute(combined_query)
        games  = result.scalars().all()

    return GameListResponse(total=len(games), page=1, limit=limit, games=games)


# ── GET /games/similar/{game_id} ───────────────────────────────────────────────
@router.get("/similar/{game_id}", response_model=GameListResponse)
async def get_similar_games(
    game_id: int,
    limit:   int          = Query(5, ge=1, le=20),
    db:      AsyncSession = Depends(get_db),
):
    """Cari game yang mirip berdasarkan genre."""
    from sqlalchemy import text, func

    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game tidak ditemukan")

    if not game.genres:
        similar_query = select(Game).where(
            Game.id != game_id
        ).order_by(
            Game.steam_review_score.desc().nullslast()
        ).limit(limit)
    else:
        # Pakai semua genre — lebih spesifik
        genre_conditions = " AND ".join([
            f"genres::jsonb @> '[\"{ g }\"]'::jsonb"
            for g in (game.genres or [])[:2]  # pakai 2 genre pertama
        ])

        if len(game.genres) >= 2:
            # Cari yang match 2 genre sekaligus — lebih relevan
            similar_query = select(Game).where(
                Game.id != game_id
            ).filter(
                text(f"genres::jsonb @> '[\"{ game.genres[0] }\"]'::jsonb"),
                text(f"genres::jsonb @> '[\"{ game.genres[1] }\"]'::jsonb"),
            ).order_by(
                Game.steam_review_score.desc().nullslast()
            ).limit(limit * 3)  # ambil lebih banyak untuk diacak
        else:
            similar_query = select(Game).where(
                Game.id != game_id
            ).filter(
                text(f"genres::jsonb @> '[\"{ game.genres[0] }\"]'::jsonb"),
            ).order_by(
                Game.steam_review_score.desc().nullslast()
            ).limit(limit * 3)

    result = await db.execute(similar_query)
    games  = result.scalars().all()

    # Acak hasilnya supaya tidak selalu sama
    import random
    random.shuffle(games)

    return GameListResponse(total=len(games[:limit]), page=1, limit=limit, games=games[:limit])

# ── POST /games ────────────────────────────────────────────────────────────────
@router.post("/", response_model=GameResponse, status_code=201)
async def create_game(
    payload: GameCreate,
    db:      AsyncSession = Depends(get_db),
):
    """Tambah game baru ke database."""
    game = Game(**payload.model_dump())
    db.add(game)
    await db.flush()   # kirim ke database tapi belum commit
    await db.refresh(game)  # ambil data terbaru (termasuk id yang baru dibuat)
    return game


# ── PUT /games/{id} ────────────────────────────────────────────────────────────
@router.put("/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: int,
    payload: GameUpdate,
    db:      AsyncSession = Depends(get_db),
):
    """Update data game yang sudah ada."""
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game dengan id {game_id} tidak ditemukan")

    # Hanya update field yang dikirim (tidak None)
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(game, field, value)

    await db.flush()
    await db.refresh(game)
    return game


# ── DELETE /games/{id} ─────────────────────────────────────────────────────────
@router.delete("/{game_id}", status_code=204)
async def delete_game(
    game_id: int,
    db:      AsyncSession = Depends(get_db),
):
    """Hapus game dari database."""
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game dengan id {game_id} tidak ditemukan")
    await db.delete(game)
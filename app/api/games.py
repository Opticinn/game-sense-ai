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


# ── GET /games/{id} ────────────────────────────────────────────────────────────
@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: int,
    db:      AsyncSession = Depends(get_db),
):
    """Ambil detail satu game berdasarkan ID."""
    game = await db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail=f"Game dengan id {game_id} tidak ditemukan")
    return game


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
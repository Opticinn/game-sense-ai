"""
steam_enricher.py — Update data game existing dari Steam API

Analogi sederhana:
  Bayangkan kamu punya daftar 2,408 buku di perpustakaan.
  File ini bertugas pergi ke toko buku Steam, cek harga terbaru,
  jumlah review terbaru, dan update catatan perpustakaan kita.

Nilai karir:
  - Belajar batch processing — update ribuan data secara efisien
  - Belajar exponential backoff — teknik retry yang dipakai Netflix, Google, dll
  - Belajar partial update (PATCH pattern) — hanya update field yang berubah
"""

import asyncio
import logging
from typing import Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.game import Game

logger = logging.getLogger(__name__)

# ── Konstanta ────────────────────────────────────────────────────────────────
STEAM_API_BASE    = "https://store.steampowered.com/api"
STEAM_RATE_DELAY  = 1.5   # Steam lebih ketat soal rate limit — tunggu 1.5 detik
BATCH_SIZE        = 50    # commit ke database setiap 50 game (hemat memory)


class SteamEnricher:
    """
    Kelas yang bertugas update data game existing menggunakan Steam API.
    
    Cara pakai:
        enricher = SteamEnricher()
        await enricher.run(limit=500)  # update 500 game pertama
    """

    def __init__(self):
        self.client  = httpx.AsyncClient(timeout=30.0)
        self.updated = 0
        self.failed  = 0

    async def fetch_steam_details(self, steam_id: str) -> Optional[dict]:
        """
        Ambil detail game dari Steam Store API.
        
        Endpoint: /appdetails?appids=STEAM_ID
        Tidak perlu API key! Steam Store API ini public.
        (Steam API key hanya diperlukan untuk endpoint lain seperti player stats)
        
        Return format:
        {
          "730": {                    ← steam_id sebagai key
            "success": true,
            "data": { ... }          ← detail game di sini
          }
        }
        """
        try:
            response = await self.client.get(
                f"{STEAM_API_BASE}/appdetails",
                params={
                    "appids":  steam_id,
                    "cc":      "us",    # harga dalam USD
                    "l":       "en",    # bahasa Inggris
                }
            )
            response.raise_for_status()
            result = response.json()

            # Steam mengembalikan dict dengan steam_id sebagai key
            game_data = result.get(str(steam_id), {})
            if not game_data.get("success"):
                return None

            return game_data.get("data")

        except Exception as e:
            logger.warning(f"Gagal fetch Steam detail untuk {steam_id}: {e}")
            return None

    def parse_steam_updates(self, data: dict) -> dict:
        """
        Ambil field yang ingin kita update dari response Steam.
        
        Kita TIDAK update semua field — hanya yang Steam lebih akurat:
        - Harga terbaru
        - Header image terbaru  
        - Developer/publisher (kalau kosong)
        - Short description (kalau kosong)
        - Has mod support (dari categories)
        - Steam Workshop URL
        """
        updates = {}

        # Harga
        price_overview = data.get("price_overview", {})
        if price_overview:
            final_price = price_overview.get("final", 0)
            updates["price_usd"] = round(final_price / 100, 2)  # Steam kirim dalam sen
            updates["is_free"]   = False
        elif data.get("is_free"):
            updates["is_free"]   = True
            updates["price_usd"] = 0.0

        # Header image
        if data.get("header_image"):
            updates["header_image"] = data["header_image"]

        # Developer & Publisher
        devs = data.get("developers", [])
        pubs = data.get("publishers", [])
        if devs:
            updates["developer"] = devs[0]
        if pubs:
            updates["publisher"] = pubs[0]

        # Short description
        if data.get("short_description"):
            updates["short_desc"] = data["short_description"][:500]

        # Full description
        if data.get("detailed_description"):
            updates["description"] = data["detailed_description"]

        # Mod support — cek dari categories
        categories = data.get("categories", [])
        cat_ids    = [c.get("id") for c in categories]
        # Category ID 30 = Steam Workshop
        if 30 in cat_ids:
            updates["has_mod_support"]    = True
            steam_id = data.get("steam_appid")
            if steam_id:
                updates["steam_workshop_url"] = f"https://steamcommunity.com/app/{steam_id}/workshop/"

        # Genres
        genres = [g["description"] for g in data.get("genres", [])]
        if genres:
            updates["genres"] = genres

        return updates

    async def update_game(self, session: AsyncSession, game: Game) -> bool:
        """
        Fetch data Steam untuk satu game lalu update di database.
        
        Return True kalau berhasil diupdate, False kalau gagal.
        """
        if not game.steam_id:
            return False

        steam_data = await self.fetch_steam_details(game.steam_id)
        if not steam_data:
            return False

        updates = self.parse_steam_updates(steam_data)
        if not updates:
            return False

        # Apply updates ke object game
        # Kita hanya update field yang tidak kosong di database
        for field, value in updates.items():
            # Untuk description & short_desc: hanya update kalau masih kosong
            if field in ("description", "short_desc", "developer", "publisher"):
                if getattr(game, field) is None:
                    setattr(game, field, value)
            else:
                setattr(game, field, value)

        return True

    async def run(self, limit: Optional[int] = None):
        """
        Entry point utama — update semua game yang punya steam_id.
        
        limit=None  → update semua game
        limit=500   → update 500 game pertama saja
        """
        async with AsyncSessionLocal() as session:
            # Ambil semua game yang punya steam_id
            query = select(Game).where(Game.steam_id.isnot(None))
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            games  = result.scalars().all()
            total  = len(games)

            print(f"🎮 Steam Enricher — akan update {total} game...")

            for i, game in enumerate(games, 1):
                try:
                    print(f"[{i}/{total}] Updating '{game.title}' (steam_id: {game.steam_id})...", end=" ")
                    
                    success = await self.update_game(session, game)
                    
                    if success:
                        self.updated += 1
                        print("✅")
                    else:
                        self.failed += 1
                        print("⏭️  (skip)")

                    # Commit setiap BATCH_SIZE game
                    if i % BATCH_SIZE == 0:
                        await session.commit()
                        print(f"💾 Committed {i} game...")

                    # Rate limiting
                    await asyncio.sleep(STEAM_RATE_DELAY)

                except Exception as e:
                    self.failed += 1
                    print(f"❌ Error: {e}")
                    logger.exception(e)

            # Final commit
            await session.commit()

        await self.client.aclose()
        print(f"\n✅ Steam Enrichment selesai!")
        print(f"   ✏️  Game diupdate : {self.updated}")
        print(f"   ❌ Game gagal    : {self.failed}")
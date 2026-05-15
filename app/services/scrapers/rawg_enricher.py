"""
rawg_enricher.py — Fetch game baru dari RAWG API

Analogi sederhana:
  RAWG itu seperti ensiklopedia game terbesar di dunia (899,000+ game!).
  File ini bertugas membuka ensiklopedia itu, mencari game PC yang belum
  ada di database kita, lalu menambahkannya.

Nilai karir:
  - Belajar async HTTP client (httpx) — standar industri 2024
  - Belajar rate limiting & pagination — skill wajib saat kerja dengan API publik
  - Belajar upsert pattern — teknik database yang dipakai di semua perusahaan tech
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
RAWG_BASE_URL = "https://api.rawg.io/api"
MIN_RATINGS   = 100    # minimum ratings di RAWG (berbeda dengan Steam reviews)
PAGE_SIZE     = 40     # maksimal per request RAWG
RATE_LIMIT_DELAY = 0.5 # detik jeda antar request (jaga agar tidak kena ban)


class RAWGEnricher:
    """
    Kelas yang bertugas fetch game dari RAWG dan simpan ke database.
    
    Cara pakai:
        enricher = RAWGEnricher()
        await enricher.run(max_pages=10)
    """

    def __init__(self):
        # httpx.AsyncClient = versi async dari requests library
        # Seperti browser yang bisa buka banyak tab sekaligus tanpa nunggu
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = settings.RAWG_API_KEY
        self.added   = 0   # counter game baru yang berhasil ditambahkan
        self.skipped = 0   # counter game yang sudah ada / tidak memenuhi syarat

    async def fetch_games_page(self, page: int) -> dict:
        """
        Ambil satu halaman daftar game dari RAWG.
        
        RAWG API — endpoint /games:
          - platforms=4    → PC saja (platform id 4 = PC)
          - ordering=-added → urutkan dari yang paling banyak ditambahkan user
          - page_size=40   → 40 game per halaman
        """
        params = {
            "key":            self.api_key,
            "platforms":      4,        # platform id 4 = PC (Windows)
            "parent_platforms": 1,      # parent platform 1 = PC
            "ordering":       "-added",
            "page_size":      PAGE_SIZE,
            "page":           page,
        }

        response = await self.client.get(f"{RAWG_BASE_URL}/games", params=params)
        response.raise_for_status()  # lempar error kalau status bukan 200
        return response.json()

    async def fetch_game_detail(self, rawg_slug: str) -> Optional[dict]:
        """
        Ambil detail lengkap satu game dari RAWG.
        
        Kenapa perlu detail terpisah?
        Karena endpoint list hanya kasih info ringkas.
        Detail memberikan: deskripsi panjang, metacritic score, website, dll.
        """
        try:
            response = await self.client.get(
                f"{RAWG_BASE_URL}/games/{rawg_slug}",
                params={"key": self.api_key}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Gagal fetch detail {rawg_slug}: {e}")
            return None

    def parse_game_data(self, raw: dict, detail: Optional[dict] = None) -> Optional[dict]:
        """
        Ubah data mentah dari RAWG menjadi format yang cocok dengan model Game kita.
        
        Analogi: seperti menerjemahkan buku dari bahasa Inggris ke Indonesia —
        strukturnya sama tapi formatnya disesuaikan.
        """
        # Ambil nama game
        title = raw.get("name", "").strip()
        if not title:
            return None

        # Validasi: harus ada platform PC (id=4)
        platforms = raw.get("platforms") or []
        platform_ids = [p.get("platform", {}).get("id") for p in platforms]
        if 4 not in platform_ids:
            return None  # skip game non-PC

        # RAWG tidak punya steam_id langsung, tapi ada di stores
        steam_id = None
        stores = raw.get("stores") or []
        for store in stores:
            store_info = store.get("store", {})
            if store_info.get("slug") == "steam":
                # URL Steam store biasanya: https://store.steampowered.com/app/1234/
                url = store.get("url", "")
                parts = [p for p in url.split("/") if p.isdigit()]
                if parts:
                    steam_id = parts[0]
                break

        # Genres dari RAWG → list of string
        genres = [g["name"] for g in (raw.get("genres") or [])]
        
        # Tags dari RAWG
        tags = [t["name"] for t in (raw.get("tags") or []) if t.get("language") == "eng"][:20]

        # Header image
        header_image = raw.get("background_image")

        # Rating RAWG (skala 0-5) → konversi ke 0-100 agar konsisten dengan Steam
        rawg_rating = raw.get("rating", 0)
        steam_review_score = round(rawg_rating * 20, 1) if rawg_rating else None

        # Jumlah ratings sebagai proxy review_count
        ratings_count = raw.get("ratings_count", 0)

        # Data dari detail (kalau berhasil difetch)
        description = None
        metacritic  = None
        website     = None
        if detail:
            description = detail.get("description_raw") or detail.get("description")
            metacritic  = detail.get("metacritic")
            website     = detail.get("website")

        return {
            "title":              title,
            "steam_id":           steam_id,
            "description":        description,
            "genres":             genres,
            "tags":               tags,
            "header_image":       header_image,
            "steam_review_score": steam_review_score,
            "steam_review_count": ratings_count,
            "is_free":            raw.get("tba", False),  # TBA = belum rilis
        }

    async def save_game(self, session: AsyncSession, game_data: dict) -> bool:
        """
        Simpan game ke database kalau belum ada.
        
        Pattern ini namanya "upsert check":
        1. Cek dulu apakah sudah ada (by title atau steam_id)
        2. Kalau belum ada → INSERT
        3. Kalau sudah ada → SKIP (kita tidak overwrite data Steam yang lebih akurat)
        
        Kenapa tidak update? Karena data Steam lebih akurat dari RAWG untuk game Steam.
        RAWG berguna untuk game baru yang belum ada di dataset kita.
        """
        title    = game_data.get("title")
        steam_id = game_data.get("steam_id")

        # Cek by steam_id dulu (lebih akurat)
        if steam_id:
            result = await session.execute(
                select(Game).where(Game.steam_id == steam_id)
            )
            if result.scalars().first():
                return False  # sudah ada

        # Cek by title (fallback)
        result = await session.execute(
            select(Game).where(Game.title == title)
        )
        if result.scalars().first():
            return False  # sudah ada

        # Buat object Game baru
        game = Game(**game_data)
        session.add(game)
        return True

    async def run(self, max_pages: int = 20):
        """
        Entry point utama — jalankan proses enrichment.
        
        max_pages=20 artinya kita fetch 20 x 40 = 800 game dari RAWG.
        Sesuaikan angkanya tergantung kebutuhan.
        """
        logger.info(f"🚀 Mulai RAWG enrichment — max {max_pages} halaman...")
        print(f"🚀 Mulai RAWG enrichment — max {max_pages} halaman ({max_pages * PAGE_SIZE} game)...")

        async with AsyncSessionLocal() as session:
            for page in range(1, max_pages + 1):
                try:
                    print(f"📄 Fetching halaman {page}/{max_pages}...", end=" ")
                    
                    # Ambil daftar game halaman ini
                    data  = await self.fetch_games_page(page)
                    games = data.get("results", [])

                    if not games:
                        print("Tidak ada data, berhenti.")
                        break

                    page_added = 0
                    for raw_game in games:
                        # Skip kalau ratings terlalu sedikit
                        if raw_game.get("ratings_count", 0) < MIN_RATINGS:
                            self.skipped += 1
                            continue

                        # Fetch detail (opsional, lebih lambat tapi lebih lengkap)
                        # Kita skip detail untuk kecepatan, bisa diaktifkan nanti
                        game_data = self.parse_game_data(raw_game, detail=None)
                        
                        if not game_data:
                            self.skipped += 1
                            continue

                        saved = await self.save_game(session, game_data)
                        if saved:
                            self.added += 1
                            page_added += 1
                        else:
                            self.skipped += 1

                    # Commit per halaman (lebih aman dari commit di akhir)
                    await session.commit()
                    print(f"✅ +{page_added} game baru (total: {self.added})")

                    # Rate limiting — jangan terlalu cepat request ke RAWG
                    await asyncio.sleep(RATE_LIMIT_DELAY)

                except httpx.HTTPStatusError as e:
                    print(f"❌ HTTP Error halaman {page}: {e}")
                    if e.response.status_code == 429:
                        print("⏳ Rate limited! Tunggu 10 detik...")
                        await asyncio.sleep(10)
                except Exception as e:
                    print(f"❌ Error halaman {page}: {e}")
                    logger.exception(e)

        await self.client.aclose()
        print(f"\n✅ RAWG Enrichment selesai!")
        print(f"   ➕ Game baru ditambahkan : {self.added}")
        print(f"   ⏭️  Game dilewati         : {self.skipped}")
"""
trending_score.py — Hitung dan update trending score untuk semua game

Analogi sederhana:
  Trending score itu seperti "termometer kepopuleran" game.
  Makin banyak orang main sekarang + makin banyak review positif
  = makin panas = makin trending!

Nilai karir:
  - Score normalization (Min-Max scaling) — teknik ML dasar yang dipakai di semua model
  - Weighted scoring system — dipakai di Google Search ranking, Netflix recommendation
  - Batch async processing — standar di data pipeline perusahaan besar
"""

import asyncio
import logging
import math
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.game import Game

logger = logging.getLogger(__name__)

# ── Bobot Formula ────────────────────────────────────────────────────────────
W_PLAYERS    = 0.40   # current players (real-time)
W_POSITIVITY = 0.35   # review positivity ratio
W_POPULARITY = 0.25   # total review count (popularitas keseluruhan)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
RATE_DELAY   = 1.2    # detik antar request (SteamSpy cukup ketat)
BATCH_SIZE   = 50     # commit setiap 50 game


class TrendingScoreEngine:
    """
    Engine yang fetch data real-time dari Steam + SteamSpy,
    lalu hitung trending score untuk setiap game.
    """

    def __init__(self):
        self.client  = httpx.AsyncClient(timeout=20.0)
        self.updated = 0
        self.failed  = 0

        # Kumpulkan semua scores dulu untuk normalisasi
        self._player_scores     = {}
        self._positivity_scores = {}
        self._popularity_scores = {}

    async def fetch_current_players(self, steam_id: str) -> Optional[int]:
        """
        Ambil jumlah pemain aktif sekarang dari Steam API.
        Tidak butuh API key — public endpoint!
        """
        try:
            r = await self.client.get(
                "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/",
                params={"appid": steam_id}
            )
            r.raise_for_status()
            data = r.json()
            return data.get("response", {}).get("player_count", 0)
        except Exception:
            return None

    async def fetch_steamspy_data(self, steam_id: str) -> Optional[dict]:
        """
        Ambil data review dari SteamSpy.
        SteamSpy = layanan gratis yang agregat data Steam.
        """
        try:
            r = await self.client.get(
                "https://steamspy.com/api.php",
                params={"request": "appdetails", "appid": steam_id}
            )
            r.raise_for_status()
            data = r.json()

            positive = data.get("positive", 0) or 0
            negative = data.get("negative", 0) or 0

            return {
                "positive": positive,
                "negative": negative,
                "total":    positive + negative,
            }
        except Exception:
            return None

    def log_scale(self, value: float, base: int = 10) -> float:
        """
        Transformasi logaritmik — untuk data yang range-nya sangat besar.

        Analogi: tanpa log, CS2 (1 juta pemain) akan selalu menang telak
        dari game indie bagus (10,000 pemain). Dengan log:
          log(1,000,000) = 6.0
          log(10,000)    = 4.0
        Selisihnya tidak terlalu jauh — game indie tetap bisa trending!

        Ini teknik yang sama dipakai Spotify untuk ranking lagu.
        """
        return math.log(max(value, 1), base)

    def normalize(self, values: list[float]) -> list[float]:
        """
        Min-Max normalization — ubah semua nilai ke skala 0-1.

        Rumus: (x - min) / (max - min)

        Contoh: [100, 500, 1000] → [0.0, 0.44, 1.0]

        Kenapa penting? Supaya player count (jutaan) dan
        positivity ratio (0-1) bisa digabungkan secara adil.

        Ini adalah teknik ML paling fundamental — dipakai di hampir
        semua model machine learning.
        """
        if not values:
            return []
        min_v = min(values)
        max_v = max(values)
        if max_v == min_v:
            return [0.5] * len(values)
        return [(v - min_v) / (max_v - min_v) for v in values]

    async def collect_data(self, games: list) -> dict:
        """
        Phase 1: Kumpulkan semua data mentah dari Steam + SteamSpy.
        Dikumpulkan dulu semua, baru dinormalisasi bersama-sama.

        Kenapa tidak langsung hitung? Karena normalisasi butuh
        tahu nilai MIN dan MAX dari SEMUA game — tidak bisa per game.
        """
        raw_data = {}
        total    = len(games)

        print(f"📡 Phase 1: Fetch data dari Steam + SteamSpy...")
        print(f"   Estimasi waktu: ~{total * RATE_DELAY / 60:.0f} menit\n")

        for i, game in enumerate(games, 1):
            print(f"[{i}/{total}] {game.title!r}...", end=" ", flush=True)

            players  = await self.fetch_current_players(game.steam_id)
            spy_data = await self.fetch_steamspy_data(game.steam_id)

            if players is None and spy_data is None:
                print("❌ skip")
                self.failed += 1
                continue

            players   = players or 0
            positive  = spy_data["positive"] if spy_data else 0
            negative  = spy_data["negative"] if spy_data else 0
            total_rev = spy_data["total"]    if spy_data else 0

            # Positivity ratio (0.0 - 1.0)
            positivity = positive / max(total_rev, 1)

            raw_data[game.steam_id] = {
                "game_id":    game.id,
                "players":    self.log_scale(players),
                "positivity": positivity,
                "popularity": self.log_scale(total_rev),
                # Simpan juga untuk update database
                "review_count": total_rev,
                "player_count": players,
            }

            print(f"✅ players:{players:,} positive:{positive:,}")
            await asyncio.sleep(RATE_DELAY)

        return raw_data

    def compute_scores(self, raw_data: dict) -> dict:
        """
        Phase 2: Normalisasi + hitung trending score final.
        """
        print(f"\n📊 Phase 2: Normalisasi + hitung trending score...")

        steam_ids = list(raw_data.keys())

        # Ekstrak nilai per dimensi
        player_vals     = [raw_data[sid]["players"]    for sid in steam_ids]
        positivity_vals = [raw_data[sid]["positivity"] for sid in steam_ids]
        popularity_vals = [raw_data[sid]["popularity"] for sid in steam_ids]

        # Normalisasi per dimensi (Min-Max)
        norm_players     = self.normalize(player_vals)
        norm_positivity  = self.normalize(positivity_vals)
        norm_popularity  = self.normalize(popularity_vals)

        # Hitung weighted score
        scores = {}
        for i, sid in enumerate(steam_ids):
            score = (
                W_PLAYERS    * norm_players[i]     +
                W_POSITIVITY * norm_positivity[i]  +
                W_POPULARITY * norm_popularity[i]
            )
            # Skala ke 0-100
            scores[sid] = {
                **raw_data[sid],
                "trending_score": round(score * 100, 2),
            }

        return scores

    async def save_scores(self, session: AsyncSession, scores: dict):
        """
        Phase 3: Update trending_score + steam_review_count + steam_concurrent_peak
        ke database untuk semua game.
        """
        print(f"\n💾 Phase 3: Simpan ke database...")

        game_ids = {v["game_id"]: sid for sid, v in scores.items()}

        result = await session.execute(
            select(Game).where(Game.id.in_(list(game_ids.keys())))
        )
        games = result.scalars().all()

        for i, game in enumerate(games, 1):
            sid  = game_ids[game.id]
            data = scores[sid]

            game.trending_score        = data["trending_score"]
            game.steam_review_count    = data["review_count"]
            game.steam_concurrent_peak = data["player_count"]

            if i % BATCH_SIZE == 0:
                await session.commit()
                print(f"   💾 Committed {i}/{len(games)}...")

        await session.commit()
        self.updated = len(games)
        print(f"   ✅ {self.updated} game diupdate!")

    async def run(self, limit: Optional[int] = None):
        """Entry point utama."""
        async with AsyncSessionLocal() as session:
            query = select(Game).where(Game.steam_id.isnot(None))
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            games  = result.scalars().all()
            total  = len(games)

            print(f"🔥 Trending Score Engine")
            print(f"   Total game: {total}")
            print(f"   Formula: Players({W_PLAYERS*100:.0f}%) + Positivity({W_POSITIVITY*100:.0f}%) + Popularity({W_POPULARITY*100:.0f}%)")
            print("=" * 55)

            # Phase 1: Collect
            raw_data = await self.collect_data(games)

            # Phase 2: Compute
            scores = self.compute_scores(raw_data)

            # Phase 3: Save
            await self.save_scores(session, scores)

        await self.client.aclose()

        print()
        print("=" * 55)
        print(f"🏁 Selesai!")
        print(f"   ✅ Game diupdate  : {self.updated}")
        print(f"   ❌ Game gagal     : {self.failed}")
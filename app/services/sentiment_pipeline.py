"""
sentiment_pipeline.py — Fetch Steam reviews + analisis sentiment

Alur kerja:
  1. Ambil semua game dari database
  2. Fetch 20 review terbaru per game dari Steam API
  3. Analisis sentiment tiap review dengan DistilBERT
  4. Simpan reviews ke tabel reviews
  5. Update sentiment_score di tabel games

Analogi:
  Seperti surveyor yang pergi ke setiap toko (Steam),
  wawancara 20 pelanggan, catat pendapatnya,
  lalu buat laporan "toko ini disukai 85% pelanggan".

Nilai karir:
  - NLP pipeline end-to-end — skill yang sangat dicari di industri
  - Batch inference dengan transformers — dipakai di semua perusahaan AI
  - Data ingestion pipeline — skill wajib Data Engineer
"""

import asyncio
import logging
from typing import Optional

import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.game import Game
from app.models.review import Review, Platform, SentimentLabel
from app.services.sentiment_engine import sentiment_engine

logger = logging.getLogger(__name__)

# ── Konstanta ─────────────────────────────────────────────────────────────────
STEAM_REVIEW_URL = "https://store.steampowered.com/appreviews"
REVIEWS_PER_GAME = 20     # ambil 20 review per game
RATE_DELAY       = 1.5    # detik antar request
BATCH_SIZE       = 20     # commit setiap 20 game


class SentimentPipeline:
    """
    Pipeline lengkap: fetch reviews → sentiment → update database.
    """

    def __init__(self):
        self.client    = httpx.AsyncClient(timeout=20.0)
        self.processed = 0
        self.failed    = 0

    async def fetch_steam_reviews(self, steam_id: str) -> list[dict]:
        """
        Fetch reviews dari Steam Store API.

        Parameter penting:
          filter=recent   → review terbaru
          language=english → hanya bahasa Inggris (DistilBERT)
          num_per_page=20  → 20 review per request
          review_type=all  → semua review (positive + negative)
        """
        try:
            r = await self.client.get(
                f"{STEAM_REVIEW_URL}/{steam_id}",
                params={
                    "json":         1,
                    "filter":       "recent",
                    "language":     "english",
                    "num_per_page": REVIEWS_PER_GAME,
                    "review_type":  "all",
                    "purchase_type": "all",
                }
            )
            r.raise_for_status()
            data = r.json()

            if not data.get("success"):
                return []

            return data.get("reviews", [])

        except Exception as e:
            logger.warning(f"Gagal fetch reviews {steam_id}: {e}")
            return []

    def parse_review(self, raw: dict, game_id: int) -> Optional[dict]:
        """
        Parse satu review Steam ke format database kita.

        Field penting dari Steam review:
          recommendationid → ID unik review
          author.steamid   → ID user
          review           → teks review
          voted_up         → True=positive, False=negative
          votes_up         → berapa orang setuju review ini helpful
        """
        content = raw.get("review", "").strip()
        if not content or len(content) < 10:
            return None

        voted_up   = raw.get("voted_up", True)
        rating_raw = 1.0 if voted_up else 0.0

        return {
            "game_id":     game_id,
            "platform":    Platform.STEAM,
            "external_id": str(raw.get("recommendationid", "")),
            "author_name": str(raw.get("author", {}).get("steamid", ""))[:255],
            "content":     content[:2000],
            "rating_raw":  rating_raw,
            "rating_norm": rating_raw,
            "like_count":  raw.get("votes_up", 0),
        }

    async def process_game(self, session: AsyncSession, game: Game) -> bool:
        """
        Proses satu game: fetch reviews → sentiment → simpan.
        Return True kalau berhasil.
        """
        # Fetch reviews dari Steam
        raw_reviews = await self.fetch_steam_reviews(game.steam_id)
        if not raw_reviews:
            return False

        # Parse reviews
        parsed = []
        for raw in raw_reviews:
            p = self.parse_review(raw, game.id)
            if p:
                parsed.append(p)

        if not parsed:
            return False

        # Analisis sentiment semua review sekaligus (batch)
        texts          = [p["content"] for p in parsed]
        sentiment_results = sentiment_engine.analyze_batch(texts)

        # Hapus reviews lama untuk game ini (biar tidak duplikat)
        await session.execute(
            delete(Review).where(
                Review.game_id == game.id,
                Review.platform == Platform.STEAM
            )
        )

        # Simpan reviews baru
        for p, sent in zip(parsed, sentiment_results):
            review = Review(
                **p,
                sentiment_label = SentimentLabel(sent["label"]),
                sentiment_score = sent["norm"],
            )
            session.add(review)

        # Agregasi → update sentiment_score di tabel games
        aggregated           = sentiment_engine.aggregate_scores(sentiment_results)
        game.sentiment_score = aggregated["sentiment_score"]

        return True

    async def run(self, limit: Optional[int] = None):
        """Entry point utama."""
        print("🤖 Loading DistilBERT sentiment model...")
        sentiment_engine.load()
        print()

        async with AsyncSessionLocal() as session:
            query = select(Game).where(Game.steam_id.isnot(None))
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            games  = result.scalars().all()
            total  = len(games)

            print(f"🎮 Sentiment Pipeline")
            print(f"   Total game  : {total}")
            print(f"   Review/game : {REVIEWS_PER_GAME}")
            print(f"   Total review: ~{total * REVIEWS_PER_GAME:,}")
            print("=" * 55)

            for i, game in enumerate(games, 1):
                print(f"[{i}/{total}] {game.title!r}...", end=" ", flush=True)

                try:
                    success = await self.process_game(session, game)

                    if success:
                        self.processed += 1
                        print(f"✅ sentiment: {game.sentiment_score:.2f}")
                    else:
                        self.failed += 1
                        print("⏭️  skip (no reviews)")

                    # Commit setiap BATCH_SIZE game
                    if i % BATCH_SIZE == 0:
                        await session.commit()
                        print(f"💾 Committed {i}/{total}...")

                    await asyncio.sleep(RATE_DELAY)

                except Exception as e:
                    self.failed += 1
                    print(f"❌ Error: {e}")
                    logger.exception(e)

            await session.commit()

        await self.client.aclose()

        print()
        print("=" * 55)
        print(f"🏁 Sentiment Pipeline Selesai!")
        print(f"   ✅ Berhasil : {self.processed}")
        print(f"   ❌ Gagal    : {self.failed}")
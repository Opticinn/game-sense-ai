# app/services/hybrid_ranker.py
from typing import Optional
from app.models import Game


class HybridRanker:
    """
    Menggabungkan semua skor jadi satu skor rekomendasi akhir.

    Formula:
    final_score = (w1 * ncf_score) + (w2 * content_score) 
                + (w3 * sentiment_score) + (w4 * trending_score)

    Analoginya seperti juri kompetisi dengan 4 kriteria penilaian:
    - NCF score      = nilai dari juri "kecocokan personal"
    - Content score  = nilai dari juri "kualitas konten game"
    - Sentiment score = nilai dari juri "opini komunitas"
    - Trending score = nilai dari juri "popularitas sekarang"
    """

    # Bobot setiap komponen — total harus = 1.0
    # Bisa diubah sesuai kebutuhan
    W_NCF       = 0.40  # NCF paling penting — rekomendasi personal
    W_CONTENT   = 0.25  # kualitas konten game
    W_SENTIMENT = 0.20  # opini komunitas
    W_TRENDING  = 0.15  # seberapa ramai sekarang


    def score(
        self,
        game:            Game,
        ncf_score:       Optional[float] = None,
        user_genres:     list = [],
        user_tags:       list = [],
    ) -> dict:
        """
        Hitung hybrid score untuk satu game.

        Parameters:
        - game        : object Game dari database
        - ncf_score   : skor dari NCF (None = user belum login)
        - user_genres : genre favorit user (dari sidebar Streamlit)
        - user_tags   : tag favorit user (dari sidebar Streamlit)

        Return: dict berisi semua skor dan skor akhir
        """

        # ── 1. NCF Score ───────────────────────────────────────────────────────
        # Kalau user belum login → ncf_score = None → pakai nilai default 0.5
        final_ncf = ncf_score if ncf_score is not None else 0.5

        # ── 2. Content Score ───────────────────────────────────────────────────
        # Seberapa cocok game ini dengan preferensi genre & tag user
        content_score = self._calculate_content_score(game, user_genres, user_tags)

        # ── 3. Sentiment Score ─────────────────────────────────────────────────
        # Dari database — sudah dihitung oleh sentiment engine
        sentiment = game.sentiment_score or game.steam_review_score or 0.5

        # ── 4. Trending Score ──────────────────────────────────────────────────
        # Dari database — dihitung dari player count & review velocity
        trending = game.trending_score or 0.3

        # ── Final Score ────────────────────────────────────────────────────────
        final_score = (
            self.W_NCF       * final_ncf     +
            self.W_CONTENT   * content_score +
            self.W_SENTIMENT * sentiment     +
            self.W_TRENDING  * trending
        )

        return {
            "game_id"       : game.id,
            "title"         : game.title,
            "ncf_score"     : round(final_ncf,     4),
            "content_score" : round(content_score, 4),
            "sentiment_score": round(sentiment,    4),
            "trending_score" : round(trending,     4),
            "final_score"   : round(final_score,   4),
            "is_personal"   : ncf_score is not None,
        }


    def _calculate_content_score(
        self,
        game:        Game,
        user_genres: list,
        user_tags:   list,
    ) -> float:
        """
        Hitung seberapa cocok game dengan preferensi genre & tag user.

        Contoh:
        User suka: ["RPG", "Open World"]
        Game punya: ["RPG", "Action", "Open World"]
        → 2 dari 2 genre cocok → content_score tinggi
        """
        if not user_genres and not user_tags:
            # User tidak pilih preferensi → pakai steam review score
            return game.steam_review_score or 0.5

        game_genres = [g.lower() for g in (game.genres or [])]
        game_tags   = [t.lower() for t in (game.tags   or [])]

        # Hitung genre match
        genre_score = 0.0
        if user_genres:
            matched = sum(1 for g in user_genres if g.lower() in game_genres)
            genre_score = matched / len(user_genres)

        # Hitung tag match
        tag_score = 0.0
        if user_tags:
            matched = sum(1 for t in user_tags if t.lower() in game_tags)
            tag_score = matched / len(user_tags)

        # Kombinasikan genre dan tag score
        if user_genres and user_tags:
            return (genre_score * 0.6) + (tag_score * 0.4)
        elif user_genres:
            return genre_score
        else:
            return tag_score


    def rank_games(
        self,
        games:       list[Game],
        ncf_scores:  dict = {},    # {game_id: ncf_score}
        user_genres: list = [],
        user_tags:   list = [],
        limit:       int  = 20,
    ) -> list[dict]:
        """
        Rank banyak game sekaligus dan kembalikan yang terbaik.

        Parameters:
        - games      : list Game dari database
        - ncf_scores : dict {game_id: float} dari NCF model
        - user_genres: genre favorit user
        - user_tags  : tag favorit user
        - limit      : berapa game yang dikembalikan

        Return: list game yang sudah diurutkan dari skor tertinggi
        """
        scored = []

        for game in games:
            ncf_score = ncf_scores.get(game.id)
            result    = self.score(
                game        = game,
                ncf_score   = ncf_score,
                user_genres = user_genres,
                user_tags   = user_tags,
            )
            scored.append(result)

        # Urutkan dari skor tertinggi
        scored.sort(key=lambda x: x["final_score"], reverse=True)

        return scored[:limit]


# Singleton
hybrid_ranker = HybridRanker()
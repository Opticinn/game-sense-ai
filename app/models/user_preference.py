from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class UserPreference(Base):
    """
    Satu baris = satu user dan semua preferensi gaming-nya.
    Dibaca oleh NCF untuk menghasilkan rekomendasi personal.
    """
    __tablename__ = "user_preferences"

    # ── Primary Key ────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Identitas User ─────────────────────────────────────
    # user_id = ID unik tiap user di sistem kita
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,   # satu user hanya boleh punya SATU baris preferensi
        index=True,
    )

    # ── Preferensi Game (untuk NCF) ────────────────────────
    # Disimpan sebagai JSON list berisi game_id (angka)
    # Contoh: liked_game_ids = [1, 5, 23, 47]
    liked_game_ids:    Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    disliked_game_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # played_game_ids = game yang sudah pernah dimainkan (meski tidak di-like/dislike)
    # Penting untuk NCF — user yang sudah main tidak perlu direkomendasikan game yang sama
    played_game_ids:   Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # ── Preferensi Genre ───────────────────────────────────
    # Contoh: ["RPG", "Open World", "Survival"]
    favorite_genres:  Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    excluded_genres:  Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # ── Preferensi Tag ─────────────────────────────────────
    # Lebih spesifik dari genre
    # Contoh: ["Mod Support", "Co-op", "Controller Support"]
    favorite_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # ── Budget & Platform ──────────────────────────────────
    # max_price_usd = None artinya tidak ada batasan harga
    max_price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # platform_preference = "steam", "epic", atau "both"
    platform_preference: Mapped[str] = mapped_column(
        String(50), default="both", nullable=False
    )

    # ── Preferensi Gameplay ────────────────────────────────
    prefers_multiplayer: Mapped[bool] = mapped_column(Boolean, default=False)
    prefers_mod_support: Mapped[bool] = mapped_column(Boolean, default=False)
    prefers_free_games:  Mapped[bool] = mapped_column(Boolean, default=False)

    # ── NCF Embedding ──────────────────────────────────────
    # Setelah NCF dilatih, setiap user punya "sidik jari" berupa 64 angka
    # Sidik jari ini merepresentasikan selera user dalam bahasa yang dimengerti NCF
    # Disimpan sebagai JSON list: [0.23, -0.15, 0.87, ...]
    # None = user baru, belum punya embedding (cold start)
    ncf_embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # ── Timestamps ─────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<UserPreference user_id='{self.user_id}' liked={len(self.liked_game_ids)} games>"

    # ── Helper Methods ─────────────────────────────────────
    # Method = fungsi yang menempel pada sebuah object
    def is_cold_start(self) -> bool:
        """
        Cold start = user baru yang belum punya data preferensi.
        Kalau True, sistem skip NCF dan pakai content-based + LLM saja.
        """
        return len(self.liked_game_ids) == 0 and self.ncf_embedding is None

    def has_liked(self, game_id: int) -> bool:
        """Cek apakah user sudah pernah like game ini."""
        return game_id in self.liked_game_ids

    def has_played(self, game_id: int) -> bool:
        """Cek apakah user sudah pernah main game ini."""
        return game_id in self.played_game_ids
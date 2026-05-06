from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# ── ENUM: Platform ─────────────────────────────────────────────────────────────
# Enum = pilihan yang sudah ditentukan, tidak bisa diisi sembarangan
# Seperti pilihan gender di formulir: hanya "Laki" atau "Perempuan"
class Platform(str, enum.Enum):
    STEAM    = "steam"
    YOUTUBE  = "youtube"
    TIKTOK   = "tiktok"
    REDDIT   = "reddit"
    FACEBOOK = "facebook"


# ── ENUM: Sentiment Label ──────────────────────────────────────────────────────
class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL  = "neutral"
    NEGATIVE = "negative"


# ── MODEL: Review ──────────────────────────────────────────────────────────────
class Review(Base):
    """
    Satu baris = satu ulasan dari satu platform.
    Contoh: review Steam dari user A untuk game Elden Ring.
    """
    __tablename__ = "reviews"

    # ── Primary Key ────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign Key — penghubung ke tabel games ────────────
    # Seperti nomor meja di restoran — review ini milik game mana?
    # ondelete="CASCADE" = kalau game dihapus, semua reviewnya ikut terhapus otomatis
    game_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,   # sering dicari berdasarkan game_id, jadi perlu index
    )

    # ── Dari Platform Mana ─────────────────────────────────
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform),
        nullable=False,
        index=True,
    )

    # ── Identitas Pembuat Ulasan ───────────────────────────
    # external_id = ID asli dari platform (misal: Steam user ID, Reddit post ID)
    external_id:  Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_name:  Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Isi Ulasan ─────────────────────────────────────────
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Rating ─────────────────────────────────────────────
    # rating_raw = nilai mentah dari platform (Steam: 1/0, Reddit: upvote ratio, dll)
    rating_raw:    Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # rating_norm = nilai yang sudah disamakan skalanya: 0.0 sampai 1.0
    rating_norm:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Engagement (seberapa viral) ────────────────────────
    like_count:    Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    view_count:    Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Hasil Analisis Sentiment ───────────────────────────
    # Diisi SETELAH DistilBERT menganalisis kolom 'content'
    sentiment_label: Mapped[Optional[SentimentLabel]] = mapped_column(
        Enum(SentimentLabel), nullable=True
    )
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Timestamps ─────────────────────────────────────────
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scraped_at:   Mapped[datetime]           = mapped_column(DateTime, server_default=func.now())

    # ── Relationship ───────────────────────────────────────
    # Ini bukan kolom di database — hanya shortcut di Python
    # Contoh: review.game → langsung dapat object Game, tidak perlu query lagi
    game: Mapped["Game"] = relationship("Game", back_populates="reviews")  # type: ignore

    def __repr__(self) -> str:
        return f"<Review id={self.id} platform={self.platform} sentiment={self.sentiment_label}>"
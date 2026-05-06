from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Float, Integer, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Game(Base):
    """
    Tabel utama — menyimpan semua info game dari Steam & Epic.
    Setiap baris = satu game.
    """
    __tablename__ = "games"

    # ── Primary Key ────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Identitas Game ─────────────────────────────────────
    title: Mapped[str]           = mapped_column(String(255), nullable=False, index=True)
    steam_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    epic_id:  Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)

    # ── Deskripsi ──────────────────────────────────────────
    description:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_desc:     Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    developer:      Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publisher:      Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    release_date:   Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Kategori (disimpan sebagai JSON list) ──────────────
    # Contoh: genres = ["Action", "RPG"]
    #         tags   = ["Open World", "Multiplayer", "Mod Support"]
    genres: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    tags:   Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # ── Harga ──────────────────────────────────────────────
    price_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_free:   Mapped[bool]            = mapped_column(Boolean, default=False)

    # ── Skor dari Steam ────────────────────────────────────
    steam_review_score:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    steam_review_count:   Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    steam_concurrent_peak: Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)

    # ── Skor dari GameSense AI ─────────────────────────────
    # sentiment_score = hasil agregasi dari Steam + YouTube + TikTok + Reddit + Facebook
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # trending_score  = seberapa ramai game ini dibicarakan sekarang
    trending_score:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Media ──────────────────────────────────────────────
    header_image:  Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    trailer_url:   Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Mod Support ────────────────────────────────────────
    # True kalau game punya Steam Workshop atau komunitas mod aktif
    has_mod_support:    Mapped[bool] = mapped_column(Boolean, default=False)
    steam_workshop_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Timestamps ─────────────────────────────────────────
    # server_default = otomatis diisi database saat data baru dibuat
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────
    # Satu game punya BANYAK review — one-to-many
    # Seperti satu buku punya banyak komentar pembaca
    # ── Relationships ──────────────────────────────────────────────────────────────
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="game", cascade="all, delete-orphan"
    )
    video_contents: Mapped[List["VideoContent"]] = relationship(
        "VideoContent", back_populates="game", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Game id={self.id} title='{self.title}'>"
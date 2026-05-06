from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class VideoPlatform(str, enum.Enum):
    YOUTUBE  = "youtube"
    TIKTOK   = "tiktok"
    FACEBOOK = "facebook"


class VideoType(str, enum.Enum):
    GAMEPLAY  = "gameplay"
    REVIEW    = "review"
    MOD       = "mod"
    TUTORIAL  = "tutorial"
    OTHER     = "other"


class VideoContent(Base):
    __tablename__ = "video_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    game_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform: Mapped[VideoPlatform] = mapped_column(
        Enum(VideoPlatform),
        nullable=False,
        index=True,
    )

    video_id:     Mapped[str]           = mapped_column(String(255), nullable=False)
    title:        Mapped[str]           = mapped_column(String(500), nullable=False)
    channel_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description:  Mapped[Optional[str]] = mapped_column(Text,        nullable=True)

    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    embed_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    view_count:    Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    like_count:    Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    comment_count: Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    like_ratio:    Mapped[Optional[float]] = mapped_column(Float,   nullable=True)

    video_type: Mapped[VideoType] = mapped_column(
        Enum(VideoType),
        default=VideoType.OTHER,
        nullable=False,
    )
    is_mod_related: Mapped[bool] = mapped_column(Boolean, default=False)

    sentiment_label: Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float,      nullable=True)

    hashtags: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scraped_at:   Mapped[datetime]           = mapped_column(DateTime, server_default=func.now())

    game: Mapped["Game"] = relationship("Game", back_populates="video_contents")  # type: ignore

    def __repr__(self) -> str:
        return f"<VideoContent id={self.id} platform={self.platform} title='{self.title[:30]}'>"
# app/migrate.py
# Jalankan file ini SEKALI untuk membuat semua tabel di PostgreSQL
import asyncio
from app.database import engine, Base

# Import semua model supaya SQLAlchemy tahu tabel apa saja yang perlu dibuat
from app.models import Game, Review, VideoContent, UserPreference


async def migrate():
    print("🔄 Membuat tabel-tabel di PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Semua tabel berhasil dibuat!")
    print()
    print("Tabel yang dibuat:")
    print("  - games")
    print("  - reviews")
    print("  - video_content")
    print("  - user_preferences")


asyncio.run(migrate())
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── 1. ENGINE ──────────────────────────────────────────────────────────────────
# Engine = kunci untuk membuka pintu gudang (PostgreSQL)
# "async" artinya Python tidak perlu menunggu diam saat menunggu data dari database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,       # ganti ke True kalau mau lihat query SQL di terminal (debug)
    pool_size=10,     # maksimal 10 koneksi sekaligus (seperti 10 kasir)
    max_overflow=20,  # boleh tambah 20 lagi kalau sedang ramai
)


# ── 2. SESSION FACTORY ─────────────────────────────────────────────────────────
# Session = satu "sesi belanja" di gudang
# Setiap request dari user membuka sesi baru, lalu ditutup setelah selesai
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # data tetap bisa dibaca setelah di-commit
)


# ── 3. BASE MODEL ──────────────────────────────────────────────────────────────
# Semua tabel database akan "mewarisi" class ini
# Seperti template kosong yang diisi oleh tiap tabel
class Base(DeclarativeBase):
    pass


# ── 4. DEPENDENCY ──────────────────────────────────────────────────────────────
# Fungsi ini dipakai oleh FastAPI di setiap endpoint yang butuh database
# "yield" = beri dulu, nanti tutup sendiri setelah selesai dipakai
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session           # berikan session ke endpoint
            await session.commit()  # simpan perubahan ke database
        except Exception:
            await session.rollback()  # kalau ada error, batalkan semua perubahan
            raise
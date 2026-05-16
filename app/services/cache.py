"""
cache.py — Redis cache manager untuk GameSense AI

Analogi sederhana:
  Cache itu seperti sticky note di meja kerja.
  Daripada bolak-balik ke gudang (database) untuk info yang sama,
  tempel hasilnya di sticky note — ambil dari situ kalau butuh lagi.
  Sticky note dibuang setelah beberapa menit supaya tetap fresh.

Nilai karir:
  - Redis caching — skill wajib backend engineer di semua perusahaan
  - Cache invalidation strategy — salah satu problem tersulit di CS
  - Decorator pattern — teknik Python yang elegan dan reusable
"""

import json
import hashlib
import logging
from typing import Optional, Any
from functools import wraps

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── Redis Client ──────────────────────────────────────────────────────────────
# Dibuat sekali, dipakai berkali-kali (singleton pattern)
redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """
    Ambil koneksi Redis. Kalau belum ada, buat baru.
    Kalau Redis tidak tersedia, return None (graceful degradation).

    Graceful degradation = kalau Redis mati, app tetap jalan
    tapi tanpa cache. Lebih baik lambat daripada crash!
    """
    global redis_client

    if redis_client is not None:
        return redis_client

    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test koneksi
        await redis_client.ping()
        logger.info("✅ Redis connected!")
        return redis_client
    except Exception as e:
        logger.warning(f"⚠️ Redis tidak tersedia: {e} — berjalan tanpa cache")
        return None


async def cache_get(key: str) -> Optional[Any]:
    """
    Ambil data dari cache.
    Return None kalau tidak ada atau Redis mati.
    """
    redis = await get_redis()
    if not redis:
        return None

    try:
        data = await redis.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """
    Simpan data ke cache dengan TTL (time-to-live) dalam detik.

    ttl=300 = data expired setelah 5 menit
    Seperti sticky note yang otomatis hilang setelah 5 menit.
    """
    redis = await get_redis()
    if not redis:
        return False

    try:
        await redis.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning(f"Cache set error: {e}")
        return False


async def cache_delete(pattern: str) -> int:
    """
    Hapus semua cache key yang cocok dengan pattern.
    Dipakai saat data berubah (cache invalidation).

    Contoh: cache_delete("games:*") hapus semua cache games
    """
    redis = await get_redis()
    if not redis:
        return 0

    try:
        keys = await redis.keys(pattern)
        if keys:
            return await redis.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache delete error: {e}")
        return 0


def make_cache_key(prefix: str, **kwargs) -> str:
    """
    Buat cache key unik dari prefix + parameter.

    Analogi: seperti label di laci filing cabinet.
    "games:page=1:limit=20:genre=RPG" → laci khusus untuk query itu.

    Pakai MD5 hash supaya key tidak terlalu panjang.
    """
    params_str = json.dumps(kwargs, sort_keys=True, default=str)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    return f"{prefix}:{params_hash}"
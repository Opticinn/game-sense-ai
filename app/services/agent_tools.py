# app/services/agent_tools.py
import asyncio
from langchain.tools import tool
from sqlalchemy     import select

from app.database              import AsyncSessionLocal
from app.models                import Game
from app.services.vector_store import game_vector_store
from app.services.scrapers.steam_scraper   import steam_scraper
from app.services.scrapers.youtube_scraper import youtube_scraper


def run_async(coro):
    """Helper untuk jalankan async function dari dalam sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@tool
def search_game(query: str) -> str:
    """
    Cari game berdasarkan nama, genre, atau deskripsi.
    Gunakan tool ini saat user bertanya tentang game tertentu
    atau ingin rekomendasi game berdasarkan preferensi.

    Contoh query:
    - 'game RPG open world'
    - 'game mirip Dark Souls'
    - 'Elden Ring'
    """
    results = game_vector_store.search(query, k=5)
    if not results:
        return "Tidak ada game yang ditemukan."

    output = f"Hasil pencarian untuk '{query}':\n\n"
    for i, r in enumerate(results, 1):
        meta  = r["metadata"]

        # Harga
        if meta.get("is_free"):
            harga = "Gratis"
        elif meta.get("price_idr"):
            harga = f"Rp {meta.get('price_idr'):,}".replace(",", ".")
        else:
            harga = f"${meta.get('price_usd', 0):.2f}"

        review_count = meta.get("steam_review_count", 0)
        review_text  = f"{review_count:,}" if review_count else "Tidak ada data"

        # Fix rating bug
        score = meta.get("steam_review_score", 0) or 0
        if score > 1:
            score = score / 100

        output += (
            f"{i}. {meta['title']}\n"
            f"   Genre        : {meta.get('genres', '-')}\n"
            f"   Harga        : {harga}\n"
            f"   Rating       : {score:.0%}\n"
            f"   Jumlah Review: {review_text}\n"
        )

        # Hanya tampilkan mod support kalau tersedia
        if meta.get("has_mod_support"):
            output += f"   Mod Support  : ✅\n"

        output += "\n"

    return output


@tool
def get_mod_games(query: str) -> str:
    """
    Cari game yang punya mod support aktif.
    Gunakan tool ini saat user bertanya tentang game dengan mod,
    modding community, atau Steam Workshop.

    Contoh query:
    - 'game seru dengan mod'
    - 'game dengan banyak mod'
    - 'game modding terbaik'
    """
    results = game_vector_store.search_mod_games(query, k=5)
    if not results:
        return "Tidak ada game dengan mod support yang ditemukan."

    output = f"Game dengan mod support terbaik untuk '{query}':\n\n"
    for i, r in enumerate(results, 1):
        meta  = r["metadata"]
        harga = "Gratis" if meta.get("is_free") else f"${meta.get('price_usd', 0):.2f}"
        output += (
            f"{i}. {meta['title']}\n"
            f"   Genre  : {meta.get('genres', '-')}\n"
            f"   Harga  : {harga}\n"
            f"   Rating : {meta.get('steam_review_score', 0):.0%}\n"
            f"   Mod    : ✅ Supported\n\n"
        )
    return output


@tool
def get_game_price(game_name: str) -> str:
    """
    Ambil harga terkini sebuah game dari Steam secara real-time.
    Gunakan tool ini saat user bertanya tentang harga game,
    apakah game sedang diskon, atau worth it dibeli sekarang.

    Contoh: 'Elden Ring', 'Counter-Strike 2', 'Dota 2'
    """
    async def _fetch():
        # Cari steam_id dari database dulu
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Game).where(
                    Game.title.ilike(f"%{game_name}%")
                ).limit(1)
            )
            game = result.scalar_one_or_none()

        if not game or not game.steam_id:
            return f"Game '{game_name}' tidak ditemukan di database."

        # Ambil harga real-time dari Steam API
        details = await steam_scraper.get_game_details(game.steam_id)
        if not details:
            # Fallback ke harga di database
            price = "Gratis" if game.is_free else f"${game.price_usd:.2f}"
            return f"{game.title}: {price} (dari database, mungkin tidak terkini)"

        price = "Gratis" if details["is_free"] else f"${details['price_usd']:.2f}"
        return (
            f"{details['title']}\n"
            f"Harga   : {price}\n"
            f"Developer: {', '.join(details.get('developers', []))}\n"
        )

    return run_async(_fetch())


@tool
def get_gameplay_video(game_name: str) -> str:
    """
    Ambil link video gameplay dari YouTube untuk sebuah game.
    Gunakan tool ini saat user ingin melihat gameplay,
    atau ingin tahu tampilan game sebelum beli.

    Contoh: 'Elden Ring gameplay', 'Minecraft survival'
    """
    async def _fetch():
        videos = await youtube_scraper.search_videos(
            game_name  = game_name,
            video_type = "gameplay",
            max_results= 3,
        )

        if not videos:
            return f"Tidak ada video gameplay ditemukan untuk '{game_name}'."

        output = f"Video gameplay '{game_name}':\n\n"
        for v in videos:
            output += (
                f"📺 {v['title'][:60]}\n"
                f"   Channel : {v['channel_name']}\n"
                f"   Link    : {v['video_url']}\n"
                f"   Embed   : {v['embed_url']}\n\n"
            )
        return output

    return run_async(_fetch())


@tool
def get_mod_videos(game_name: str) -> str:
    """
    Ambil video tentang mod untuk sebuah game dari YouTube.
    Gunakan tool ini saat user bertanya tentang mod showcase,
    mod terpopuler, atau cara install mod.

    Contoh: 'Skyrim mods', 'Minecraft mod showcase'
    """
    async def _fetch():
        videos = await youtube_scraper.search_videos(
            game_name  = game_name,
            video_type = "mod",
            max_results= 3,
        )

        if not videos:
            return f"Tidak ada video mod ditemukan untuk '{game_name}'."

        output = f"Video mod '{game_name}':\n\n"
        for v in videos:
            output += (
                f"🎮 {v['title'][:60]}\n"
                f"   Channel : {v['channel_name']}\n"
                f"   Link    : {v['video_url']}\n\n"
            )
        return output

    return run_async(_fetch())


@tool
def get_current_players(game_name: str) -> str:
    """
    Ambil jumlah pemain yang sedang online sekarang dari Steam.
    Gunakan tool ini saat user bertanya apakah game masih aktif,
    berapa banyak yang main, atau apakah komunitas masih ramai.

    Contoh: 'Counter-Strike 2', 'Dota 2'
    """
    async def _fetch():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Game).where(
                    Game.title.ilike(f"%{game_name}%")
                ).limit(1)
            )
            game = result.scalar_one_or_none()

        if not game or not game.steam_id:
            return f"Game '{game_name}' tidak ditemukan."

        players = await steam_scraper.get_current_players(game.steam_id)
        if players is None:
            return f"Tidak bisa ambil data pemain untuk {game.title}."

        return (
            f"{game.title}\n"
            f"Pemain online sekarang: {players:,} orang\n"
            f"Peak concurrent      : {game.steam_concurrent_peak:,} orang\n"
        )

    return run_async(_fetch())


# Daftar semua tools yang tersedia untuk agent
ALL_TOOLS = [
    search_game,
    get_mod_games,
    get_game_price,
    get_gameplay_video,
    get_mod_videos,
    get_current_players,
]
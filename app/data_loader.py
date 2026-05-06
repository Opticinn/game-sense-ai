# app/data_loader.py
import asyncio
import json
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models   import Game

GAMES_JSON = r"C:\Users\Rafli\.cache\kagglehub\datasets\fronkongames\steam-games-dataset\versions\31\games.json"

# Genre dewasa yang akan difilter
ADULT_GENRES = {"sexual content", "nudity", "adult only", "hentai", "eroge"}


def has_mod_support(categories: list, tags: dict) -> bool:
    cat_text = " ".join(categories).lower()
    tag_text  = " ".join(tags.keys()).lower()
    text      = f"{cat_text} {tag_text}"
    return any(kw in text for kw in ["steam workshop", "mod support", "moddable", "modding"])


def calculate_review_score(positive: int, negative: int) -> float:
    total = positive + negative
    if total == 0:
        return 0.0
    return round(positive / total, 4)


def is_adult(genres: list, tags: dict) -> bool:
    all_text = " ".join(genres + list(tags.keys())).lower()
    return any(kw in all_text for kw in ADULT_GENRES)


def safe_str(value, max_len=255):
    if not value:
        return None
    return str(value).strip()[:max_len] or None


async def load_games(limit: int = 5000):
    print("📖 Membaca file JSON...")
    with open(GAMES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"✅ Total game di JSON: {len(data):,}")

    # Filter & urutkan berdasarkan review terbanyak
    games_list = []
    for app_id, game in data.items():
        positive = game.get("positive", 0) or 0
        negative = game.get("negative", 0) or 0
        total    = positive + negative

        # Filter: minimal 10 review
        if total < 10:
            continue

        # Filter: skip genre dewasa
        genres = game.get("genres", []) or []
        tags   = game.get("tags",   {}) or {}
        if is_adult(genres, tags):
            continue

        games_list.append((app_id, game, total))

    print(f"✅ Game setelah filter: {len(games_list):,}")

    # Urutkan berdasarkan total review terbanyak
    games_list.sort(key=lambda x: x[2], reverse=True)
    games_list = games_list[:limit]
    print(f"✅ Game yang akan diload: {len(games_list):,}")
    print("🚀 Mulai load ke database...")

    async with AsyncSessionLocal() as session:
        loaded  = 0
        skipped = 0

        # Ambil steam_id yang sudah ada
        existing_result = await session.execute(select(Game.steam_id))
        existing_ids    = set(existing_result.scalars().all())
        print(f"   Database sudah punya: {len(existing_ids):,} game")

        for app_id, game, total in games_list:
            steam_id = str(app_id)

            if steam_id in existing_ids:
                skipped += 1
                continue

            positive   = game.get("positive", 0) or 0
            negative   = game.get("negative", 0) or 0
            genres     = game.get("genres",      []) or []
            tags       = game.get("tags",        {}) or {}
            categories = game.get("categories",  []) or []
            developers = game.get("developers",  []) or []
            publishers = game.get("publishers",  []) or []
            price      = game.get("price",       0.0)

            # Tags dari dict {tag_name: vote_count} → ambil key-nya saja
            tag_list = list(tags.keys())

            game_obj = Game(
                title         = safe_str(game.get("name")),
                steam_id      = steam_id,
                description   = safe_str(game.get("about_the_game"),    max_len=5000),
                short_desc    = safe_str(game.get("short_description"),  max_len=500),
                developer     = safe_str(", ".join(developers)),
                publisher     = safe_str(", ".join(publishers)),
                genres        = genres,
                tags          = tag_list,
                price_usd     = float(price) if price else 0.0,
                is_free       = float(price or 0) == 0.0,
                header_image  = safe_str(game.get("header_image"), max_len=500),

                steam_review_score    = calculate_review_score(positive, negative),
                steam_review_count    = positive + negative,
                steam_concurrent_peak = game.get("peak_ccu"),

                has_mod_support = has_mod_support(categories, tags),
            )

            session.add(game_obj)
            existing_ids.add(steam_id)
            loaded += 1

            if loaded % 500 == 0:
                await session.commit()
                print(f"   💾 {loaded:,} game tersimpan...")

        await session.commit()

    print()
    print("✅ Selesai!")
    print(f"   Loaded  : {loaded:,} game")
    print(f"   Skipped : {skipped:,} game")


if __name__ == "__main__":
    asyncio.run(load_games(limit=5000))
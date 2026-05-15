import asyncio
import sys
import os
import unicodedata
import re

sys.path.insert(0, os.path.abspath('.'))

import httpx
from rapidfuzz import fuzz
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.game import Game

STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch"
RATE_DELAY       = 1.0
FUZZY_THRESHOLD  = 82


def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_variants(title):
    variants = [title]
    no_article = re.sub(r"^(The|A|An)\s+", "", title, flags=re.IGNORECASE).strip()
    if no_article != title:
        variants.append(no_article)
    no_subtitle = re.split(r"\s[-:]\s", title)[0].strip()
    if no_subtitle != title:
        variants.append(no_subtitle)
    words = title.split()
    if len(words) > 3:
        variants.append(" ".join(words[:3]))
    seen = set()
    result = []
    for v in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            result.append(v)
    return result


def find_best_match(title, results):
    norm_title = normalize(title)
    best_id    = None
    best_score = 0
    for item in results:
        steam_name = item.get("name", "")
        norm_steam = normalize(steam_name)
        steam_id   = str(item["id"])
        if norm_title == norm_steam:
            return steam_id, 100
        score = max(
            fuzz.token_sort_ratio(norm_title, norm_steam),
            fuzz.partial_ratio(norm_title, norm_steam)
        )
        if score > best_score:
            best_score = score
            best_id    = steam_id
    if best_score >= FUZZY_THRESHOLD:
        return best_id, best_score
    return None, best_score


async def search_steam(client, query):
    try:
        response = await client.get(
            STEAM_SEARCH_URL,
            params={"term": query, "cc": "us", "l": "en"}
        )
        response.raise_for_status()
        return response.json().get("items", [])
    except Exception:
        return []


async def run():
    found   = 0
    deleted = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Game).where(Game.steam_id.is_(None))
        )
        games = result.scalars().all()
        total = len(games)

        print(f"Mencari steam_id untuk {total} game...")
        print(f"Threshold: {FUZZY_THRESHOLD}/100")
        print()

        async with httpx.AsyncClient(timeout=15.0) as client:
            for i, game in enumerate(games, 1):
                print(f"[{i}/{total}] {game.title!r}...", end=" ", flush=True)
                matched    = False
                best_score = 0

                for variant in make_variants(game.title):
                    results = await search_steam(client, variant)
                    if not results:
                        continue
                    steam_id, score = find_best_match(game.title, results)
                    best_score = max(best_score, score)
                    if steam_id:
                        existing = await session.execute(
                            select(Game).where(
                                Game.steam_id == steam_id,
                                Game.id != game.id
                            )
                        )
                        if existing.scalars().first():
                            print(f"Duplicate -> dihapus")
                            await session.delete(game)
                            deleted += 1
                            matched = True
                            break
                        game.steam_id = steam_id
                        found += 1
                        matched = True
                        print(f"OK {steam_id} (score:{score})")
                        break
                    await asyncio.sleep(0.3)

                if not matched:
                    print(f"TIDAK DITEMUKAN (best:{best_score}) -> dihapus")
                    await session.delete(game)
                    deleted += 1

                if i % 20 == 0:
                    await session.commit()
                    print(f"--- Committed {i}/{total} ---")

                await asyncio.sleep(RATE_DELAY)

        await session.commit()

    print()
    print("=" * 40)
    print("Selesai!")
    print(f"  Ditemukan : {found}")
    print(f"  Dihapus   : {deleted}")


asyncio.run(run())
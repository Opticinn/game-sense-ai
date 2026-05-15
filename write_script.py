code = """\
import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.scrapers.rawg_enricher  import RAWGEnricher
from app.services.scrapers.steam_enricher import SteamEnricher
from app.services.trending_score          import TrendingScoreEngine


async def run_rawg(pages):
    print("=" * 50)
    print("RAWG Enricher - Tambah game baru")
    print("=" * 50)
    enricher = RAWGEnricher()
    await enricher.run(max_pages=pages)


async def run_steam(limit):
    print("=" * 50)
    print("Steam Enricher - Update data existing")
    print("=" * 50)
    enricher = SteamEnricher()
    await enricher.run(limit=limit if limit > 0 else None)


async def run_trending(limit):
    print("=" * 50)
    print("Trending Score Engine")
    print("=" * 50)
    engine = TrendingScoreEngine()
    await engine.run(limit=limit if limit > 0 else None)


async def run_all(pages, limit):
    await run_rawg(pages)
    print()
    await run_steam(limit)
    print()
    await run_trending(limit)


def main():
    parser = argparse.ArgumentParser(description="GameSense AI Data Pipeline")
    parser.add_argument(
        "--source",
        choices=["rawg", "steam", "trending", "all"],
        default="all",
        help="Sumber data (default: all)"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=10,
        help="Jumlah halaman RAWG (default: 10)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Batas game diproses, 0=semua (default: 0)"
    )

    args = parser.parse_args()

    print("GameSense AI Data Pipeline")
    print(f"  Source : {args.source}")
    if args.source in ("rawg", "all"):
        print(f"  Pages  : {args.pages} ({args.pages * 40} game)")
    if args.source in ("steam", "trending", "all"):
        print(f"  Limit  : {'semua' if args.limit == 0 else args.limit} game")
    print()

    if args.source == "rawg":
        asyncio.run(run_rawg(args.pages))
    elif args.source == "steam":
        asyncio.run(run_steam(args.limit))
    elif args.source == "trending":
        asyncio.run(run_trending(args.limit))
    else:
        asyncio.run(run_all(args.pages, args.limit))


main()
"""

with open("scripts/run_enrichment.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Berhasil!")
print(f"Baris: {len(code.splitlines())}")
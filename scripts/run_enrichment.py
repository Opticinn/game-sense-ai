"""
run_enrichment.py — CLI untuk menjalankan data pipeline

Cara pakai:
  python scripts/run_enrichment.py --source rawg --pages 10
  python scripts/run_enrichment.py --source steam --limit 100
  python scripts/run_enrichment.py --source all
"""

import asyncio
import argparse
import sys
import os

# Tambahkan root folder ke path supaya bisa import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.scrapers.rawg_enricher  import RAWGEnricher
from app.services.scrapers.steam_enricher import SteamEnricher


async def run_rawg(pages: int):
    print("=" * 50)
    print("🌐 RAWG Enricher — Tambah game baru")
    print("=" * 50)
    enricher = RAWGEnricher()
    await enricher.run(max_pages=pages)


async def run_steam(limit: int):
    print("=" * 50)
    print("🎮 Steam Enricher — Update data existing")
    print("=" * 50)
    enricher = SteamEnricher()
    await enricher.run(limit=limit if limit > 0 else None)


async def run_all(pages: int, limit: int):
    await run_rawg(pages)
    print()
    await run_steam(limit)


def main():
    parser = argparse.ArgumentParser(description="GameSense AI — Data Enrichment Pipeline")
    parser.add_argument(
        "--source",
        choices=["rawg", "steam", "all"],
        default="all",
        help="Sumber data yang akan dijalankan (default: all)"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=10,
        help="Jumlah halaman RAWG yang difetch, 1 halaman = 40 game (default: 10)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Batas game Steam yang diupdate, 0 = semua (default: 0)"
    )

    args = parser.parse_args()

    print(f"\n🚀 GameSense AI Data Pipeline")
    print(f"   Source : {args.source}")
    if args.source in ("rawg", "all"):
        print(f"   Pages  : {args.pages} ({args.pages * 40} game)")
    if args.source in ("steam", "all"):
        print(f"   Limit  : {'semua' if args.limit == 0 else args.limit} game")
    print()

    if args.source == "rawg":
        asyncio.run(run_rawg(args.pages))
    elif args.source == "steam":
        asyncio.run(run_steam(args.limit))
    else:
        asyncio.run(run_all(args.pages, args.limit))


if __name__ == "__main__":
    main()
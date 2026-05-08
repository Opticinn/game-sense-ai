# app/services/scrapers/steam_scraper.py
import httpx
import asyncio
from typing import Optional
from datetime import datetime

from app.config import settings


class SteamScraper:
    """
    Mengambil data real-time dari Steam API.
    
    Bayangkan seperti kurir yang pergi ke toko Steam,
    ambil info terbaru, dan bawa pulang ke database kita.
    """

    BASE_URL    = "https://store.steampowered.com/api"
    REVIEW_URL  = "https://store.steampowered.com/appreviews"

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "GameSenseAI/1.0"}
        )


    async def get_game_details(self, steam_id: str) -> Optional[dict]:
        """
        Ambil detail game dari Steam Store API.
        Dipakai untuk update harga, rating, player count secara real-time.
        """
        try:
            url    = f"{self.BASE_URL}/appdetails"
            params = {"appids": steam_id, "cc": "us", "l": "english"}

            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            game_data = data.get(steam_id, {})
            if not game_data.get("success"):
                return None

            info = game_data.get("data", {})

            # Ambil harga
            price_overview = info.get("price_overview", {})
            price_usd      = price_overview.get("final", 0) / 100  # Steam simpan dalam sen

            return {
                "title"       : info.get("name"),
                "description" : info.get("short_description"),
                "price_usd"   : price_usd,
                "is_free"     : info.get("is_free", False),
                "header_image": info.get("header_image"),
                "genres"      : [g["description"] for g in info.get("genres", [])],
                "categories"  : [c["description"] for c in info.get("categories", [])],
                "developers"  : info.get("developers", []),
                "publishers"  : info.get("publishers", []),
                "platforms"   : info.get("platforms", {}),
                "metacritic"  : info.get("metacritic", {}).get("score"),
                "release_date": info.get("release_date", {}).get("date"),
                "website"     : info.get("website"),
            }

        except Exception as e:
            print(f"❌ Error get_game_details({steam_id}): {e}")
            return None


    async def get_current_players(self, steam_id: str) -> Optional[int]:
        """
        Ambil jumlah pemain yang sedang online sekarang.
        Data ini berubah setiap menit — diambil real-time.
        """
        try:
            url    = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1"
            params = {"appid": steam_id}

            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            return data.get("response", {}).get("player_count")

        except Exception as e:
            print(f"❌ Error get_current_players({steam_id}): {e}")
            return None


    async def get_reviews(
        self,
        steam_id: str,
        num_reviews: int = 20,
        language: str    = "english",
    ) -> list[dict]:
        """
        Ambil review terbaru dari Steam untuk sebuah game.
        Dipakai untuk update sentiment score secara berkala.
        """
        try:
            url    = f"{self.REVIEW_URL}/{steam_id}"
            params = {
                "json"       : 1,
                "language"   : language,
                "num_per_page": num_reviews,
                "filter"     : "recent",   # ambil review terbaru
                "purchase_type": "all",
            }

            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            reviews = []
            for r in data.get("reviews", []):
                reviews.append({
                    "external_id"    : r.get("recommendationid"),
                    "author_name"    : str(r.get("author", {}).get("steamid", "")),
                    "content"        : r.get("review", ""),
                    "recommended"    : r.get("voted_up", False),
                    "rating_raw"     : 1.0 if r.get("voted_up") else 0.0,
                    "votes_helpful"  : r.get("votes_helpful", 0),
                    "playtime_hours" : round(r.get("author", {}).get("playtime_forever", 0) / 60, 1),
                    "published_at"   : datetime.fromtimestamp(r.get("timestamp_created", 0)),
                })

            return reviews

        except Exception as e:
            print(f"❌ Error get_reviews({steam_id}): {e}")
            return []


    async def close(self):
        await self.client.aclose()


# Singleton
steam_scraper = SteamScraper()
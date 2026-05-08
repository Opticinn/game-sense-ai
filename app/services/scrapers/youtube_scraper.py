# app/services/scrapers/youtube_scraper.py
import httpx
from typing import Optional
from datetime import datetime

from app.config import settings


class YouTubeScraper:
    """
    Mengambil video gameplay dan review game dari YouTube.
    Pakai YouTube Data API v3.

    Yang kita ambil:
    - Video gameplay (embed link untuk ditampilkan di portal)
    - Video review (untuk sentiment analysis)
    - Video mod (untuk fitur 'game seru dengan mod')
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        self.client  = httpx.AsyncClient(timeout=30.0)


    async def search_videos(
        self,
        game_name:   str,
        video_type:  str = "gameplay",  # gameplay, review, mod
        max_results: int = 5,
    ) -> list[dict]:
        """
        Cari video YouTube berdasarkan nama game dan tipe video.
        """
        if not self.api_key:
            print("⚠️ YOUTUBE_API_KEY tidak diset di .env")
            return []

        try:
            # Buat query berdasarkan tipe video
            query_map = {
                "gameplay" : f"{game_name} gameplay",
                "review"   : f"{game_name} review",
                "mod"      : f"{game_name} mods mod showcase",
                "tutorial" : f"{game_name} tutorial guide",
            }
            query = query_map.get(video_type, f"{game_name} {video_type}")

            params = {
                "key"        : self.api_key,
                "q"          : query,
                "part"       : "snippet",
                "type"       : "video",
                "maxResults" : max_results,
                "order"      : "relevance",
                "videoCategoryId": "20",  # kategori Gaming
            }

            resp = await self.client.get(f"{self.BASE_URL}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

            videos = []
            for item in data.get("items", []):
                video_id    = item["id"]["videoId"]
                snippet     = item["snippet"]
                title       = snippet.get("title", "")
                description = snippet.get("description", "")

                # Deteksi apakah video tentang mod
                is_mod = any(kw in title.lower() or kw in description.lower()
                            for kw in ["mod", "mods", "modding", "workshop"])

                videos.append({
                    "video_id"    : video_id,
                    "title"       : title[:500],
                    "channel_name": snippet.get("channelTitle", ""),
                    "description" : description[:1000],
                    "video_url"   : f"https://youtube.com/watch?v={video_id}",
                    # embed_url = link khusus untuk ditampilkan dalam aplikasi
                    "embed_url"   : f"https://www.youtube.com/embed/{video_id}",
                    "published_at": snippet.get("publishedAt"),
                    "video_type"  : video_type,
                    "is_mod_related": is_mod,
                    "platform"    : "youtube",
                })

            return videos

        except Exception as e:
            print(f"❌ Error search_videos({game_name}): {e}")
            return []


    async def get_video_stats(self, video_id: str) -> Optional[dict]:
        """
        Ambil statistik video — views, likes, comments.
        Dipakai untuk hitung like_ratio dan engagement score.
        """
        if not self.api_key:
            return None

        try:
            params = {
                "key"  : self.api_key,
                "id"   : video_id,
                "part" : "statistics",
            }

            resp = await self.client.get(f"{self.BASE_URL}/videos", params=params)
            resp.raise_for_status()
            data  = resp.json()
            items = data.get("items", [])

            if not items:
                return None

            stats      = items[0].get("statistics", {})
            view_count = int(stats.get("viewCount",    0))
            like_count = int(stats.get("likeCount",    0))
            comment_count = int(stats.get("commentCount", 0))

            # like_ratio = seberapa banyak yang like dibanding yang nonton
            like_ratio = like_count / view_count if view_count > 0 else 0.0

            return {
                "view_count"   : view_count,
                "like_count"   : like_count,
                "comment_count": comment_count,
                "like_ratio"   : round(like_ratio, 6),
            }

        except Exception as e:
            print(f"❌ Error get_video_stats({video_id}): {e}")
            return None


    async def close(self):
        await self.client.aclose()


# Singleton
youtube_scraper = YouTubeScraper()
# app/services/scrapers/reddit_scraper.py
import praw
import asyncio
from typing import Optional
from datetime import datetime

from app.config import settings


class RedditScraper:
    """
    Mengambil diskusi game dari Reddit.
    Reddit = tempat gamer paling jujur ngobrol tentang game.

    Subreddit yang kita target:
    - r/gaming         → diskusi umum
    - r/Steam          → diskusi Steam
    - r/patientgamers  → review jujur dari gamer yang sabar
    - r/games          → berita dan diskusi serius
    """

    SUBREDDITS = ["gaming", "Steam", "patientgamers", "games"]

    def __init__(self):
        self.reddit = None
        self.loaded = False


    def load(self):
        """Inisialisasi koneksi Reddit API."""
        if self.loaded:
            return

        if not settings.REDDIT_CLIENT_ID:
            print("⚠️ REDDIT_CLIENT_ID tidak diset di .env")
            return

        self.reddit = praw.Reddit(
            client_id     = settings.REDDIT_CLIENT_ID,
            client_secret = settings.REDDIT_CLIENT_SECRET,
            user_agent    = settings.REDDIT_USER_AGENT,
        )
        self.loaded = True
        print("✅ Reddit scraper loaded!")


    def search_posts(
        self,
        game_name:   str,
        max_results: int = 10,
        time_filter: str = "month",  # hour, day, week, month, year, all
    ) -> list[dict]:
        """
        Cari post Reddit tentang sebuah game.
        """
        self.load()
        if not self.reddit:
            return []

        posts = []
        try:
            # Gabungkan semua subreddit
            subreddit = self.reddit.subreddit("+".join(self.SUBREDDITS))
            results   = subreddit.search(
                query       = game_name,
                time_filter = time_filter,
                limit       = max_results,
                sort        = "relevance",
            )

            for post in results:
                # Hitung upvote ratio — ukuran kualitas post
                upvote_ratio = post.upvote_ratio  # 0.0 - 1.0

                posts.append({
                    "external_id"  : post.id,
                    "author_name"  : str(post.author) if post.author else "deleted",
                    "content"      : f"{post.title}. {post.selftext}"[:1000],
                    "rating_raw"   : upvote_ratio,
                    "rating_norm"  : upvote_ratio,
                    "like_count"   : post.score,
                    "comment_count": post.num_comments,
                    "published_at" : datetime.fromtimestamp(post.created_utc),
                    "platform"     : "reddit",
                })

        except Exception as e:
            print(f"❌ Error search_posts({game_name}): {e}")

        return posts


# Singleton
reddit_scraper = RedditScraper()
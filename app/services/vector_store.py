# app/services/vector_store.py
import asyncio
from langchain_chroma                 import Chroma
from langchain_huggingface            import HuggingFaceEmbeddings
from langchain_core.documents         import Document
from sqlalchemy                       import select

from app.config   import settings
from app.database import AsyncSessionLocal
from app.models   import Game


class GameVectorStore:
    """
    Menyimpan deskripsi game dalam bentuk vektor.
    Dipakai LLM untuk cari game yang relevan dengan query user.

    Analoginya: perpustakaan pintar yang bisa cari buku
    berdasarkan MAKNA, bukan hanya kata kunci.

    Contoh:
    Query: "game yang menantang seperti Dark Souls"
    → Vector store cari game dengan makna serupa
    → Temukan: Elden Ring, Sekiro, Hollow Knight
    → Meski tidak ada kata "Dark Souls" di deskripsinya!
    """

    def __init__(self):
        self.vectorstore = None
        self.embeddings  = None
        self.loaded      = False


    def _load_embeddings(self):
        """
        Load model embedding — mengubah teks jadi vektor angka.
        Pakai model ringan yang bisa jalan di CPU.
        """
        print("🔄 Loading embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name = "sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs = {"device": "cpu"},
        )
        print("✅ Embedding model loaded!")


    async def build(self, limit: int = 5000):
        """
        Bangun vector store dari data game di database.
        Jalankan SEKALI — hasilnya disimpan di folder chroma_db.
        """
        if not self.embeddings:
            self._load_embeddings()

        print("📖 Mengambil data game dari database...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Game).limit(limit)
            )
            games = result.scalars().all()

        print(f"✅ {len(games):,} game ditemukan")
        print("🔄 Membangun vector store...")

        # Ubah setiap game jadi Document
        # Document = satuan teks yang bisa dicari di vector store
        documents = []
        for game in games:
            # Gabungkan semua info game jadi satu teks
            # Ini yang akan di-embed dan dicari
            content = f"""
                Game: {game.title}
                Developer: {game.developer or 'Unknown'}
                Genres: {', '.join(game.genres or [])}
                Tags: {', '.join((game.tags or [])[:10])}
                Description: {game.short_desc or game.description or ''}
                Price: {'Free' if game.is_free else f'${game.price_usd}'}
                Mod Support: {'Yes' if game.has_mod_support else 'No'}
                Review Score: {game.steam_review_score or 0:.0%}
            """.strip()

            # Metadata = info tambahan yang tidak di-embed
            # tapi bisa diakses setelah dokumen ditemukan
            metadata = {
                "game_id"        : game.id,
                "title"          : game.title,
                "steam_id"       : game.steam_id or "",
                "price_usd"      : game.price_usd or 0,
                "is_free"        : game.is_free,
                "has_mod_support": game.has_mod_support,
                "genres"         : ", ".join(game.genres or []),
                "sentiment_score": game.sentiment_score or 0,
                "steam_review_score": game.steam_review_score or 0,
                "steam_review_count": game.steam_review_count or 0,
            }

            documents.append(Document(page_content=content, metadata=metadata))

        # Simpan ke ChromaDB
        self.vectorstore = Chroma.from_documents(
            documents        = documents,
            embedding        = self.embeddings,
            persist_directory= settings.CHROMA_PERSIST_DIR,
            collection_name  = "games",
        )

        self.loaded = True
        print(f"✅ Vector store berhasil dibangun!")
        print(f"   Total dokumen: {len(documents):,}")
        print(f"   Disimpan di  : {settings.CHROMA_PERSIST_DIR}")


    def load(self):
        """Load vector store yang sudah ada dari disk."""
        if self.loaded:
            return

        if not self.embeddings:
            self._load_embeddings()

        self.vectorstore = Chroma(
            persist_directory = settings.CHROMA_PERSIST_DIR,
            embedding_function= self.embeddings,
            collection_name   = "games",
        )
        self.loaded = True
        print("✅ Vector store loaded from disk!")


    def search(self, query: str, k: int = 5, filter_dict: dict = None) -> list:
        """
        Cari game yang relevan berdasarkan query.

        k           = berapa game yang dikembalikan
        filter_dict = filter tambahan (contoh: only mod games)

        Contoh:
        search("game RPG open world yang menantang", k=5)
        → [Elden Ring, Skyrim, Witcher 3, ...]
        """
        if not self.loaded:
            self.load()

        results = self.vectorstore.similarity_search(
            query  = query,
            k      = k,
            filter = filter_dict,
        )

        return [
            {
                "game_id" : doc.metadata.get("game_id"),
                "title"   : doc.metadata.get("title"),
                "content" : doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in results
        ]


    def search_mod_games(self, query: str, k: int = 5) -> list:
        """
        Khusus cari game yang punya mod support.
        Dipakai agent saat user tanya tentang mod.
        """
        if not self.loaded:
            self.load()

        # Filter hanya game yang punya mod support
        results = self.vectorstore.similarity_search(
            query  = query,
            k      = k,
            filter = {"has_mod_support": True},
        )

        return [
            {
                "game_id" : doc.metadata.get("game_id"),
                "title"   : doc.metadata.get("title"),
                "content" : doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in results
        ]


# Singleton
game_vector_store = GameVectorStore()


# ── Script untuk build vector store ───────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(game_vector_store.build(limit=5000))
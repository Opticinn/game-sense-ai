# portal/pages/home.py
import streamlit as st
import httpx

API_URL = "http://127.0.0.1:8000"


def render():
    st.title("🎮 GameSense AI")
    st.subheader("Platform Rekomendasi Game Cerdas")
    st.markdown("---")

    # ── Metrics ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    try:
        resp  = httpx.get(f"{API_URL}/games/?limit=1", timeout=5)
        total = resp.json().get("total", 0)
    except Exception:
        total = 5000

    col1.metric("🎮 Games Indexed",    f"{total:,}")
    col2.metric("⭐ Reviews Analyzed", "21M+")
    col3.metric("🌐 Platforms",        "Steam + YouTube + Reddit")
    col4.metric("🤖 AI Model",         "Qwen2.5 7B")

    st.markdown("---")

    # ── Feature Cards ─────────────────────────────────────────────────────────
    st.subheader("✨ Fitur Unggulan")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
**🔍 Smart Search**

Cari game berdasarkan genre,
tag, harga, atau deskripsi.
Powered by semantic search.
        """)

    with col2:
        st.success("""
**🤖 AI Chat**

Tanya apapun tentang game.
Agent akan carikan jawaban
terbaik dari database kami.
        """)

    with col3:
        st.warning("""
**📊 SHAP Explainability**

Setiap rekomendasi dijelaskan
kenapa game itu cocok
untuk kamu.
        """)

    st.markdown("---")

    # ── Notifikasi Login ───────────────────────────────────────────────────────
    if not st.session_state.get("user_id"):
        st.info("""
💡 **Belum login?**
Kamu tetap bisa pakai semua fitur!
Tapi dengan login, kamu akan mendapat **rekomendasi personal** 
berdasarkan riwayat game yang kamu suka.
        """)

    # ── Quick Search ───────────────────────────────────────────────────────────────
    st.subheader("🔍 Cari Game Sekarang")
    query = st.text_input(
        "Ketik nama game atau genre...",
        placeholder="contoh: RPG open world, Elden Ring, game gratis"
    )

    if query:
        with st.spinner("Mencari..."):
            try:
                resp  = httpx.get(
                    f"{API_URL}/games/search",
                    params={"q": query, "limit": 10},
                    timeout=10,
                )
                games = resp.json().get("games", [])

                if games:
                    st.markdown("**Hasil:**")
                    for game in games[:5]:
                        with st.expander(f"🎮 {game['title']}"):
                            col1, col2 = st.columns(2)
                            genres_text = ', '.join((game.get('genres') or [])[:3])
                            col1.write(f"**Genre:** {genres_text}")
                            harga = "Gratis" if game.get("is_free") else f"${game.get('price_usd', 0):.2f}"
                            col1.write(f"**Harga:** {harga}")
                            col2.write(f"**Rating:** {game.get('steam_review_score', 0):.0%}")
                            col2.write(f"**Mod Support:** {'✅' if game.get('has_mod_support') else '❌'}")
                else:
                    st.info(f"Game '{query}' tidak ditemukan. Coba di halaman **Search** untuk hasil lebih lengkap!")

            except Exception as e:
                st.error(f"Tidak bisa terhubung ke server: {e}")
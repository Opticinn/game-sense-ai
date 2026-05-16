# portal/components/home.py
import streamlit as st
import httpx
from portal.utils.currency import format_price

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
        total = 2605

    col1.metric("🎮 Games Indexed",    f"{total:,}")
    col2.metric("🤖 AI Model",         "NCF + SHAP")
    col3.metric("💬 LLM",              "Qwen2.5 7B")
    col4.metric("📊 Data Sources",     "Steam + RAWG")

    st.markdown("---")

    # ── Feature Cards ─────────────────────────────────────────────────────────
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

    # ── Notifikasi Login ──────────────────────────────────────────────────────
    if not st.session_state.get("user_id"):
        st.info("""
💡 **Belum login?**
Kamu tetap bisa pakai semua fitur!
Tapi dengan login, kamu akan mendapat **rekomendasi personal**
berdasarkan riwayat game yang kamu suka.
        """)

    # ── Quick Search ──────────────────────────────────────────────────────────
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
                    st.markdown(f"**Ditemukan {len(games)} game:**")
                    for game in games[:5]:
                        with st.expander(f"🎮 {game['title']}"):
                            col1, col2 = st.columns(2)

                            genres_text = ", ".join((game.get("genres") or [])[:3])
                            col1.write(f"**Genre:** {genres_text}")
                            col1.write(f"**Harga:** {format_price(game)}")

                            # Fix rating bug
                            score = game.get("steam_review_score") or 0
                            if score > 1:
                                score = score / 100
                            col2.write(f"**Rating:** {score:.0%}")
                            col2.write(f"**Mod Support:** {'✅' if game.get('has_mod_support') else '❌'}")

                            # Tombol detail
                            if st.button("🎮 Lihat Detail", key=f"home_{game['id']}"):
                                st.session_state["detail_game_id"] = game["id"]
                                st.session_state["previous_page"]  = "🏠 Home"
                                st.rerun()
                else:
                    st.info("Game tidak ditemukan. Coba kata kunci lain!")

            except Exception as e:
                st.error(f"Tidak bisa terhubung ke server: {e}")

    st.markdown("---")

    # ── Trending Sekarang ─────────────────────────────────────────────────────
    st.subheader("🔥 Trending Sekarang")

    try:
        resp  = httpx.get(f"{API_URL}/trending/", params={"limit": 6}, timeout=10)
        games = resp.json().get("games", [])

        if games:
            cols = st.columns(3)
            for i, game in enumerate(games[:6]):
                with cols[i % 3]:
                    if game.get("header_image"):
                        st.image(game["header_image"], use_container_width=True)
                    st.markdown(f"**{game['title']}**")
                    genres = ", ".join((game.get("genres") or [])[:2])
                    st.caption(f"🎮 {genres}")
                    st.caption(format_price(game))
                    trending = game.get("trending_score") or 0
                    st.caption(f"🔥 {trending:.1f}")
                    if st.button("Detail", key=f"home_trend_{game['id']}"):
                        st.session_state["detail_game_id"] = game["id"]
                        st.session_state["previous_page"]  = "🏠 Home"
                        st.rerun()
    except Exception:
        st.info("Tidak bisa memuat data trending.")
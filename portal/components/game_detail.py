# portal/components/game_detail.py
import streamlit as st
import httpx
import plotly.graph_objects as go
from portal.utils.currency import format_price

API_URL = "http://127.0.0.1:8000"


def render_score_gauge(score: float, title: str, color: str = "#2563EB"):
    """
    Tampilkan gauge chart untuk skor 0-100.
    Analogi: seperti speedometer — makin tinggi makin bagus!
    """
    fig = go.Figure(go.Indicator(
        mode  = "gauge+number",
        value = round(score * 100, 1) if score <= 1 else round(score, 1),
        title = {"text": title, "font": {"size": 14}},
        gauge = {
            "axis": {"range": [0, 100]},
            "bar":  {"color": color},
            "steps": [
                {"range": [0,  40], "color": "#FEE2E2"},
                {"range": [40, 70], "color": "#FEF3C7"},
                {"range": [70, 100],"color": "#D1FAE5"},
            ],
        }
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)


def render_shap_chart(game: dict):
    """Visualisasi kenapa game ini direkomendasikan."""
    review_count = game.get("steam_review_count", 0) or 0
    popularity   = min(review_count / 1_000_000, 1.0)

    factors = {
        "Trending Score"      : round((game.get("trending_score") or 0) * 0.10, 3),
        "Synopsis Similarity" : round((game.get("steam_review_score", 0) or 0) * 0.25, 3),
        "Popularity"          : round(popularity * 0.25, 3),
        "Community Sentiment" : round((game.get("sentiment_score", 0) or 0) * 0.40, 3),
    }

    labels = list(factors.keys())
    values = list(factors.values())
    colors = ["#2563EB" if v > 0.05 else "#94A3B8" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.0%}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        title  = "🔍 Kenapa game ini direkomendasikan?",
        height = 280,
        margin = dict(l=20, r=60, t=40, b=20),
        xaxis  = dict(range=[0, 0.5]),
    )
    st.plotly_chart(fig, use_container_width=True)


def fetch_game(game_id: int) -> dict | None:
    """Ambil detail game dari API."""
    try:
        r = httpx.get(f"{API_URL}/games/{game_id}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fetch_similar(game_id: int) -> list:
    """Ambil game serupa."""
    try:
        r = httpx.get(
            f"{API_URL}/games/similar/{game_id}",
            params={"limit": 6},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("games", [])
    except Exception:
        pass
    return []


def fetch_videos(game_id: int) -> list:
    """Ambil video YouTube gameplay."""
    try:
        r = httpx.get(f"{API_URL}/games/youtube/{game_id}", timeout=15)
        if r.status_code == 200:
            return r.json().get("videos", [])
    except Exception:
        pass
    return []


def render():
    # ── Cek apakah ada game yang dipilih ─────────────────────────────────────
    game_id = st.session_state.get("detail_game_id")

    if not game_id:
        st.title("🎮 Detail Game")
        st.info("Pilih game dari halaman Search atau Trending untuk melihat detailnya.")
        return

    # ── Fetch data ────────────────────────────────────────────────────────────
    with st.spinner("Memuat detail game..."):
        game = fetch_game(game_id)

    if not game:
        st.error("Game tidak ditemukan!")
        return
    
    # ── Tombol Back ───────────────────────────────────────────────────────────
    previous = st.session_state.get("previous_page", "🏠 Home")
    label    = previous.split(" ", 1)[-1]  # hapus emoji di depan

    if st.button(f"← Kembali ke {label}"):
        st.session_state["go_back_to"]     = previous
        st.session_state["detail_game_id"] = None
        st.rerun()

    # ── Header ────────────────────────────────────────────────────────────────
    st.title(f"🎮 {game['title']}")

    if game.get("steam_id"):
        steam_url = f"https://store.steampowered.com/app/{game['steam_id']}"
        st.markdown(f"[🛒 Lihat di Steam]({steam_url})")

    st.markdown("---")

    # ── Info Utama ────────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])

    with col1:
        if game.get("header_image"):
            st.image(game["header_image"], use_container_width=True)

        # Tags
        if game.get("tags"):
            tags = game["tags"][:8]
            st.markdown("**Tags:**")
            st.markdown(" ".join([f"`{t}`" for t in tags]))

    with col2:
        # Metadata
        st.markdown(f"**Developer:** {game.get('developer', '-')}")
        st.markdown(f"**Publisher:** {game.get('publisher', '-')}")

        genres = ", ".join(game.get("genres") or [])
        st.markdown(f"**Genre:** {genres}")

        st.markdown(f"**Harga:** {format_price(game)}")

        review_count = game.get("steam_review_count", 0) or 0
        review_score = game.get("steam_review_score", 0) or 0
        st.markdown(f"**Rating:** {review_score:.0%} dari {review_count:,} reviews")

        st.markdown(f"**Mod Support:** {'✅' if game.get('has_mod_support') else '❌'}")

        if game.get("steam_workshop_url"):
            st.markdown(f"[🔧 Steam Workshop]({game['steam_workshop_url']})")

    st.markdown("---")

    # ── Skor Analytics ───────────────────────────────────────────────────────
    st.subheader("📊 Analytics")
    c1, c2, c3 = st.columns(3)

    with c1:
        render_score_gauge(
            game.get("sentiment_score") or 0,
            "Sentiment Score", "#10B981"
        )
    with c2:
        render_score_gauge(
            game.get("trending_score") or 0,
            "Trending Score", "#F59E0B"
        )
    with c3:
        render_score_gauge(
            game.get("steam_review_score") or 0,
            "Review Score", "#2563EB"
        )

    # ── SHAP Chart ────────────────────────────────────────────────────────────
    render_shap_chart(game)

    st.markdown("---")

    # ── Deskripsi ─────────────────────────────────────────────────────────────
    if game.get("description") or game.get("short_desc"):
        st.subheader("📖 Deskripsi")
        desc = game.get("short_desc") or ""
        if desc:
            st.markdown(desc)
        with st.expander("Baca selengkapnya..."):
            full_desc = game.get("description") or "-"
            # Strip HTML tags sederhana
            import re
            full_desc = re.sub(r"<[^>]+>", "", full_desc)
            st.markdown(full_desc[:3000])
        st.markdown("---")

    # ── YouTube Video ─────────────────────────────────────────────────────────
    st.subheader("📺 Video Gameplay")
    with st.spinner("Memuat video..."):
        videos = fetch_videos(game_id)

    if videos:
        for video in videos[:2]:
            st.components.v1.iframe(video["embed_url"], height=380)
            st.caption(f"📺 {video['title'][:70]}")
    else:
        game_name = game["title"].replace(" ", "+")
        st.markdown(f"[🔍 Cari di YouTube](https://youtube.com/results?search_query={game_name}+gameplay)")

    st.markdown("---")

    # ── Game Serupa ───────────────────────────────────────────────────────────
    st.subheader("💡 Kamu Mungkin Juga Suka")

    with st.spinner("Memuat rekomendasi..."):
        similar = fetch_similar(game_id)

    if similar:
        cols = st.columns(3)
        for i, sg in enumerate(similar[:6]):
            with cols[i % 3]:
                if sg.get("header_image"):
                    st.image(sg["header_image"], use_container_width=True)
                st.markdown(f"**{sg['title']}**")
                genres_text = ", ".join((sg.get("genres") or [])[:2])
                st.caption(f"🎮 {genres_text}")
                st.caption(f"⭐ {sg.get('steam_review_score', 0):.0%}")
                st.caption(f"💰 {format_price(sg)}")
                if st.button("Detail", key=f"similar_{sg['id']}"):
                    st.session_state["detail_game_id"] = sg["id"]
                    st.rerun()
    else:
        st.info("Tidak ada rekomendasi serupa.")
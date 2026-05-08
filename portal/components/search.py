# portal/components/search.py
import streamlit as st
import httpx
import plotly.graph_objects as go

API_URL = "http://127.0.0.1:8000"


def render_shap_chart(game: dict):
    review_count = game.get("steam_review_count", 0) or 0
    popularity   = min(review_count / 1_000_000, 1.0)

    factors = {
        "Community Sentiment" : round((game.get("steam_review_score", 0) or 0) * 0.40, 3),
        "Popularity"          : round(popularity * 0.30, 3),
        "Mod Community"       : 0.20 if game.get("has_mod_support") else 0.0,
        "Trending Score"      : round((game.get("trending_score") or 0.3) * 0.10, 3),
    }

    labels = list(factors.keys())
    values = list(factors.values())
    colors = ["#2563EB" if v > 0 else "#94A3B8" for v in values]

    fig = go.Figure(go.Bar(
        x           = values,
        y           = labels,
        orientation = "h",
        marker_color= colors,
        text        = [f"{v:.0%}" for v in values],
        textposition= "outside",
    ))
    fig.update_layout(
        title       = f"🔍 Kenapa '{game['title']}' direkomendasikan?",
        xaxis_title = "Kontribusi Skor",
        height      = 300,
        margin      = dict(l=20, r=20, t=40, b=20),
        xaxis       = dict(range=[0, 0.5]),
    )
    st.plotly_chart(fig, use_container_width=True)


def render():
    st.title("🔍 Search & Rekomendasi Game")

    # ── Sidebar Filter ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("🎯 Filter")
        has_mod = st.checkbox("🔧 Mod Support")
        is_free = st.checkbox("🆓 Gratis")
        st.markdown("---")
        if not st.session_state.get("user_id"):
            st.warning("💡 Login untuk rekomendasi personal!")

    # ── Search Bar ─────────────────────────────────────────────────────────────
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("🔍 Cari game...", placeholder="contoh: dragon age, RPG, action")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_btn = st.button("Cari", type="primary", use_container_width=True)

    # ── Hasil Search ───────────────────────────────────────────────────────────
    games = []

    if search_btn or query:
        with st.spinner("🔄 Mencari..."):
            try:
                if query:
                    resp = httpx.get(
                        f"{API_URL}/games/search",
                        params={"q": query, "limit": 20},
                        timeout=10,
                    )
                else:
                    params = {"limit": 20}
                    if has_mod:
                        params["has_mod_support"] = True
                    if is_free:
                        params["is_free"] = True
                    resp = httpx.get(f"{API_URL}/games/", params=params, timeout=10)

                data  = resp.json()
                games = data.get("games", [])

                if has_mod:
                    games = [g for g in games if g.get("has_mod_support")]
                if is_free:
                    games = [g for g in games if g.get("is_free")]

            except Exception as e:
                st.error(f"Error: {e}")

        if not games:
            st.info("Game tidak ditemukan. Coba kata kunci lain!")
        else:
            st.markdown(f"**Ditemukan {len(games)} game**")
            st.markdown("---")

            for game in games:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.markdown(f"### 🎮 {game['title']}")
                        genres_text = ', '.join((game.get('genres') or [])[:3])
                        st.caption(f"**Genre:** {genres_text}")
                        if game.get("short_desc"):
                            st.caption(str(game["short_desc"])[:100] + "...")

                    with col2:
                        review_count = game.get("steam_review_count", 0) or 0
                        st.metric("Rating", f"{game.get('steam_review_score', 0):.0%}")
                        st.caption(f"📝 {review_count:,} reviews")
                        harga = "Gratis" if game.get("is_free") else f"${game.get('price_usd', 0):.2f}"
                        st.caption(f"💰 {harga}")
                        if game.get("has_mod_support"):
                            st.caption("🔧 Mod Support ✅")

                    with col3:
                        if st.button("Detail", key=f"btn_{game['id']}"):
                            st.session_state["selected_game"] = game

                    st.markdown("---")

            # ── Rekomendasi Serupa ─────────────────────────────────────────────
            st.markdown("---")
            st.subheader("💡 Kamu Mungkin Juga Suka")

            game_ids    = [g["id"] for g in games[:3]]
            seen_ids    = {g["id"] for g in games}
            similar_all = []

            for gid in game_ids:
                try:
                    r = httpx.get(
                        f"{API_URL}/games/similar/{gid}",
                        params={"limit": 3},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        for sg in r.json().get("games", []):
                            if sg["id"] not in seen_ids:
                                similar_all.append(sg)
                                seen_ids.add(sg["id"])
                except Exception:
                    pass

            similar_all.sort(key=lambda x: x.get("steam_review_score", 0), reverse=True)
            similar_all = similar_all[:6]

            if similar_all:
                cols = st.columns(3)
                for i, sg in enumerate(similar_all):
                    with cols[i % 3]:
                        if sg.get("header_image"):
                            st.image(sg["header_image"], use_container_width=True)
                        st.markdown(f"**{sg['title']}**")
                        genres_text = ', '.join((sg.get('genres') or [])[:2])
                        st.caption(f"🎮 {genres_text}")
                        review_count = sg.get("steam_review_count") or 0
                        st.caption(f"⭐ {sg.get('steam_review_score', 0):.0%} — 📝 {review_count:,} reviews")
                        harga = "Gratis" if sg.get("is_free") else f"${sg.get('price_usd', 0):.2f}"
                        st.caption(f"💰 {harga}")
                        if sg.get("has_mod_support"):
                            st.caption("🔧 Mod Support ✅")
                        if st.button("Detail", key=f"rec_{sg['id']}"):
                            st.session_state["selected_game"] = sg
                            st.rerun()
                        st.markdown("---")
            else:
                st.info("Tidak ada rekomendasi serupa ditemukan.")

    # ── Game Detail + SHAP ─────────────────────────────────────────────────────
    if st.session_state.get("selected_game"):
        game = st.session_state["selected_game"]

        st.markdown("---")
        st.subheader(f"🎯 Detail: {game['title']}")

        col1, col2 = st.columns(2)
        with col1:
            if game.get("header_image"):
                st.image(game["header_image"], use_container_width=True)
        with col2:
            st.write(f"**Developer:** {game.get('developer', '-')}")
            st.write(f"**Publisher:** {game.get('publisher', '-')}")
            st.write(f"**Genre:** {', '.join(game.get('genres') or [])}")
            tags_text = ', '.join((game.get('tags') or [])[:5])
            st.write(f"**Tags:** {tags_text}")
            harga = "Gratis" if game.get("is_free") else f"${game.get('price_usd', 0):.2f}"
            st.write(f"**Harga:** {harga}")
            review_count = game.get("steam_review_count", 0) or 0
            st.write(f"**Rating:** {game.get('steam_review_score', 0):.0%} dari {review_count:,} reviews")
            st.write(f"**Mod Support:** {'✅' if game.get('has_mod_support') else '❌'}")
            if game.get("steam_id"):
                steam_url = f"https://store.steampowered.com/app/{game['steam_id']}"
                st.markdown(f"[🛒 Beli di Steam]({steam_url})")

        render_shap_chart(game)

        if st.button("✖ Tutup Detail"):
            st.session_state["selected_game"] = None
            st.rerun()
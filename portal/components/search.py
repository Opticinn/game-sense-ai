# portal/components/search.py
import streamlit as st
import httpx
import plotly.graph_objects as go

API_URL = "http://127.0.0.1:8000"

def render_shap_chart(game: dict, query: str = ""):
    """
    Tampilkan SHAP chart — kenapa game ini direkomendasikan?
    
    4 faktor:
    - Community Sentiment : seberapa positif review komunitas
    - Popularity          : seberapa banyak yang main
    - Synopsis Similarity : seberapa mirip deskripsi dengan query
    - Trending Score      : seberapa ramai dibicarakan sekarang
    """
    review_count = game.get("steam_review_count", 0) or 0
    popularity   = min(review_count / 1_000_000, 1.0)

    # Hitung synopsis similarity — seberapa mirip judul/deskripsi dengan query
    synopsis_score = 0.0
    if query:
        query_lower = query.lower()
        title       = (game.get("title") or "").lower()
        short_desc  = (game.get("short_desc") or "").lower()
        genres_text = " ".join(game.get("genres") or []).lower()
        tags_text   = " ".join((game.get("tags") or [])[:10]).lower()

        # Hitung berapa kata dari query yang cocok
        query_words = [w for w in query_lower.split() if len(w) > 2]
        if query_words:
            all_text = f"{title} {short_desc} {genres_text} {tags_text}"
            matched  = sum(1 for w in query_words if w in all_text)
            synopsis_score = round(matched / len(query_words), 3)
    else:
        # Kalau tidak ada query — pakai review score sebagai proxy
        synopsis_score = round((game.get("steam_review_score", 0) or 0) * 0.5, 3)

    factors = {
        "Community Sentiment" : round((game.get("steam_review_score", 0) or 0) * 0.40, 3),
        "Popularity"          : round(popularity * 0.25, 3),
        "Synopsis Similarity" : round(synopsis_score * 0.25, 3),
        "Trending Score"      : round((game.get("trending_score") or 0.3) * 0.10, 3),
    }

    labels = list(factors.keys())
    values = list(factors.values())
    colors = ["#2563EB" if v > 0.05 else "#94A3B8" for v in values]

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
    
    # Scroll ke detail kalau baru diklik
    if st.session_state.get("scroll_to_detail"):
        st.session_state["scroll_to_detail"] = False
        st.components.v1.html("""
            <script>
                setTimeout(function() {
                    var el = document.getElementById('game-detail');
                    if (el) el.scrollIntoView({behavior: 'smooth', block: 'start'});
                }, 500);
            </script>
        """, height=0)
        
        # Toast notif (klik kedua dan seterusnya)
    if st.session_state.get("show_toast"):
        st.toast("👇 Scroll ke bawah untuk melihat detail!", icon="❗")
        st.session_state["show_toast"] = False

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
        query = st.text_input("🔍 Cari game...", placeholder="contoh: god of war, RPG, action")
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
                    col1, col2, col3, col4 = st.columns([1, 3, 2, 1])

                    # ── Poster Game ────────────────────────────────────────────
                    with col1:
                        if game.get("header_image"):
                            st.image(game["header_image"], use_container_width=True)

                    with col2:
                        st.markdown(f"### 🎮 {game['title']}")
                        genres_text = ', '.join((game.get('genres') or [])[:3])
                        st.caption(f"**Genre:** {genres_text}")
                        if game.get("short_desc"):
                            st.caption(str(game["short_desc"])[:100] + "...")

                    with col3:
                        review_count = game.get("steam_review_count", 0) or 0
                        st.metric("Rating", f"{game.get('steam_review_score', 0):.0%}")
                        st.caption(f"📝 {review_count:,} reviews")
                        harga = "Gratis" if game.get("is_free") else f"${game.get('price_usd', 0):.2f}"
                        st.caption(f"💰 {harga}")
                        if game.get("has_mod_support"):
                            st.caption("🔧 Mod Support ✅")

                    # Tombol Detail di hasil search
                    if st.button("Detail", key=f"btn_{game['id']}"):
                        st.session_state["selected_game"] = game
                        if st.session_state.get("detail_clicked_before"):
                            st.session_state["show_toast"] = True
                        else:
                            st.session_state["scroll_to_detail"]    = True
                            st.session_state["detail_clicked_before"] = True
                        st.rerun()

                    st.markdown("---")

            # ── Game Detail + SHAP ─────────────────────────────────────────────
            # Anchor untuk scroll target
            st.components.v1.html(
                '<div id="game-detail"></div>',
                height=0,
            )

            if st.session_state.get("selected_game"):
                game = st.session_state["selected_game"]

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

                render_shap_chart(game, query=query)

                # ── Embed YouTube ──────────────────────────────────────────────
                st.markdown("---")
                st.subheader("▶️ Video Gameplay")
                try:
                    yt_resp = httpx.get(
                        f"{API_URL}/games/youtube/{game['id']}",
                        timeout=15,
                    )
                    if yt_resp.status_code == 200:
                        videos = yt_resp.json().get("videos", [])
                        if videos:
                            first_video = videos[0]
                            st.components.v1.iframe(
                                first_video["embed_url"],
                                height=400,
                            )
                            st.caption(f"📺 {first_video['title'][:60]}")
                            st.caption(f"Channel: {first_video['channel_name']}")
                        else:
                            game_name = game["title"].replace(" ", "+")
                            st.markdown(f"[🔍 Cari di YouTube](https://youtube.com/results?search_query={game_name}+gameplay)")
                except Exception:
                    game_name = game["title"].replace(" ", "+")
                    st.markdown(f"[🔍 Cari di YouTube](https://youtube.com/results?search_query={game_name}+gameplay)")

                if st.button("✖ Tutup Detail"):
                    st.session_state["selected_game"] = None
                    st.rerun()

                st.markdown("---")

            # ── Rekomendasi Serupa ─────────────────────────────────────────────
            st.subheader("💡 Kamu Mungkin Juga Suka")

            # Ambil game_ids dari hasil search — bukan hardcode
            game_ids    = [g["id"] for g in games[:3]]
            seen_ids    = {g["id"] for g in games}
            similar_all = []

            for gid in game_ids:
                try:
                    r = httpx.get(
                        f"{API_URL}/games/similar/{gid}",
                        params={"limit": 4},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        for sg in r.json().get("games", []):
                            # Cegah duplikat berdasarkan title juga
                            if sg["id"] not in seen_ids and sg["title"] not in [x["title"] for x in similar_all]:
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
                        method = sg.get("method", "genre")
                        if method == "ncf":
                            st.caption("🤖 Rekomendasi NCF")
                        else:
                            st.caption("🎮 Genre Serupa")
                        harga = "Gratis" if sg.get("is_free") else f"${sg.get('price_usd', 0):.2f}"
                        st.caption(f"💰 {harga}")
                        if sg.get("has_mod_support"):
                            st.caption("🔧 Mod Support ✅")
                        # Tombol Detail di rekomendasi serupa
                        if st.button("Detail", key=f"rec_{sg['id']}"):
                            st.session_state["selected_game"] = sg
                            if st.session_state.get("detail_clicked_before"):
                                st.session_state["show_toast"] = True
                            else:
                                st.session_state["scroll_to_detail"]    = True
                                st.session_state["detail_clicked_before"] = True
                            st.rerun()
                        st.markdown("---")
            else:
                st.info("Tidak ada rekomendasi serupa ditemukan.")
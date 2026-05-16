# portal/components/trending.py
import streamlit as st
import httpx
import plotly.express as px
import pandas as pd
from portal.utils.currency import format_price

API_URL = "http://127.0.0.1:8000"


def render():
    st.title("📈 Trending Games")
    st.caption("Game yang paling banyak dimainkan dan dibicarakan sekarang")

    # ── Filter ────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        show_mod  = st.checkbox("🔧 Hanya game dengan Mod")
    with col2:
        show_free = st.checkbox("🆓 Hanya game gratis")
    with col3:
        limit = st.selectbox("Tampilkan", [10, 20, 50], index=0)

    st.markdown("---")

    # ── Fetch Data ────────────────────────────────────────────────────────────
    try:
        if show_mod:
            resp = httpx.get(f"{API_URL}/trending/mod", params={"limit": limit}, timeout=10)
        else:
            params = {"limit": limit}
            if show_free:
                params["is_free"] = True
            resp = httpx.get(f"{API_URL}/trending/", params=params, timeout=10)

        data  = resp.json()
        games = data.get("games", [])

        if not games:
            st.info("Belum ada data trending.")
            return

        # ── Chart ─────────────────────────────────────────────────────────────
        df = pd.DataFrame([{
            "title"        : g["title"][:25],
            "trending"     : round((g.get("trending_score") or 0), 1),
            "review_score" : round((g.get("steam_review_score") or 0) * 100, 1),
            "mod_support"  : "✅ Mod" if g.get("has_mod_support") else "❌ No Mod",
        } for g in games])

        tab1, tab2 = st.tabs(["🔥 Trending Score", "⭐ Review Score"])

        with tab1:
            fig = px.bar(
                df, x="trending", y="title",
                orientation="h",
                color="mod_support",
                color_discrete_map={"✅ Mod": "#2563EB", "❌ No Mod": "#94A3B8"},
                title=f"🔥 Top {len(games)} Trending Games",
                labels={"trending": "Trending Score", "title": ""},
            )
            fig.update_layout(height=max(300, len(games) * 25), margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig2 = px.bar(
                df, x="review_score", y="title",
                orientation="h",
                color="mod_support",
                color_discrete_map={"✅ Mod": "#10B981", "❌ No Mod": "#94A3B8"},
                title=f"⭐ Top {len(games)} by Review Score",
                labels={"review_score": "Review Score (%)", "title": ""},
            )
            fig2.update_layout(height=max(300, len(games) * 25), margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")

        # ── List Game ─────────────────────────────────────────────────────────
        st.subheader(f"← Top {len(games)} Games")

        for i, game in enumerate(games, 1):
            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])

            with col1:
                st.markdown(f"**#{i}**")
                if game.get("header_image"):
                    st.image(game["header_image"], use_container_width=True)

            with col2:
                st.markdown(f"**{game['title']}**")
                genres = ", ".join((game.get("genres") or [])[:2])
                st.caption(f"🎮 {genres}")
                if game.get("has_mod_support"):
                    st.caption("🔧 Mod Support ✅")

            with col3:
                # Fix rating bug — kalau > 1 berarti sudah skala 0-100
                score = game.get("steam_review_score") or 0
                if score > 1:
                    score = score / 100
                st.metric("Rating", f"{score:.0%}")
                review_count = game.get("steam_review_count") or 0
                st.caption(f"📝 {review_count:,} reviews")

            with col4:
                st.caption(format_price(game))
                trending = game.get("trending_score") or 0
                st.caption(f"🔥 Trending: {trending:.1f}")
                if st.button("Detail", key=f"trend_{game['id']}"):
                    st.session_state["detail_game_id"] = game["id"]
                    st.session_state["previous_page"]  = "📈 Trending"
                    st.rerun()

            st.markdown("---")

    except Exception as e:
        st.error(f"Tidak bisa terhubung ke server: {e}")
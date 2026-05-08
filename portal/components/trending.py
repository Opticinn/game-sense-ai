# portal/pages/trending.py
import streamlit as st
import httpx
import plotly.express as px
import pandas as pd

API_URL = "http://127.0.0.1:8000"


def render():
    st.title("📈 Trending Games")
    st.caption("Game yang paling banyak dimainkan dan dibicarakan sekarang")

    # ── Filter ─────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        show_mod  = st.checkbox("🔧 Hanya game dengan Mod")
    with col2:
        show_free = st.checkbox("🆓 Hanya game gratis")
    with col3:
        limit = st.selectbox("Tampilkan", [10, 20, 50], index=0)

    st.markdown("---")

    # ── Fetch Data ─────────────────────────────────────────────────────────────
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

        # ── Chart ──────────────────────────────────────────────────────────────
        df = pd.DataFrame([{
            "title"        : g["title"][:30],
            "review_score" : g.get("steam_review_score", 0),
            "review_count" : g.get("steam_review_count", 0) or 0,
            "mod_support"  : "✅ Mod" if g.get("has_mod_support") else "❌ No Mod",
        } for g in games])

        fig = px.bar(
            df.head(10),
            x     = "review_score",
            y     = "title",
            orientation = "h",
            color = "mod_support",
            title = "Top 10 Games by Review Score",
            color_discrete_map={"✅ Mod": "#2563EB", "❌ No Mod": "#94A3B8"},
        )
        fig.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

        # ── Game List ──────────────────────────────────────────────────────────
        st.subheader(f"🏆 Top {len(games)} Games")

        for i, game in enumerate(games, 1):
            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])

            col1.markdown(f"**#{i}**")
            col2.markdown(f"**{game['title']}**")
            col2.caption(f"{', '.join((game.get('genres') or [])[:2])}")
            col3.metric("Rating", f"{game.get('steam_review_score', 0):.0%}")

            price = "Gratis" if game.get("is_free") else f"${game.get('price_usd', 0):.2f}"
            col4.caption(f"💰 {price}")
            col4.caption("🔧 Mod" if game.get("has_mod_support") else "")

    except Exception as e:
        st.error(f"Tidak bisa terhubung ke server: {e}")
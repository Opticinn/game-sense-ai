# portal/app.py
import sys
import os

# Tambahkan root folder ke Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# portal/app.py
import streamlit as st

st.set_page_config(
    page_title = "GameSense AI",
    page_icon  = "🎮",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ── Session State Init ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "detail_game_id" not in st.session_state:
    st.session_state.detail_game_id = None

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("🎮 GameSense AI")
st.sidebar.markdown("---")

# Login sederhana
with st.sidebar.expander("👤 Login"):
    username = st.text_input("Username", placeholder="masukkan username")
    if st.button("Login"):
        if username:
            st.session_state.user_id = username
            st.success(f"✅ Login sebagai {username}!")
            st.rerun()

if st.session_state.user_id:
    st.sidebar.success(f"👤 {st.session_state.user_id}")
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.rerun()
else:
    st.sidebar.info("💡 Login untuk rekomendasi personal!")

st.sidebar.markdown("---")

# Navigasi
page = st.sidebar.radio(
    "Navigasi",
    ["🏠 Home", "🔍 Search & Rekomendasi", "📈 Trending", "🤖 AI Chat", "🎮 Detail Game", "📝 Daftar"],
)

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Qwen2.5 7B + NCF + SHAP")
st.sidebar.caption("Data: Steam + YouTube + Reddit")


# Cek back navigation
if st.session_state.get("go_back_to"):
    target = st.session_state.pop("go_back_to")
    st.session_state["detail_game_id"] = None
    # Force re-render halaman asal
    if target == "🔍 Search & Rekomendasi":
        from portal.components.search import render
        render()
    elif target == "📈 Trending":
        from portal.components.trending import render
        render()
    st.stop()

# ── Routing ────────────────────────────────────────────────────────────────────
# Auto redirect ke detail kalau ada game yang dipilih
if st.session_state.get("detail_game_id"):
    from portal.components.game_detail import render
    render()
elif page == "🏠 Home":
    from portal.components.home import render
    render()
elif page == "🔍 Search & Rekomendasi":
    from portal.components.search import render
    render()
elif page == "📈 Trending":
    from portal.components.trending import render
    render()
elif page == "🤖 AI Chat":
    from portal.components.chat import render
    render()
elif page == "📝 Daftar":
    from portal.components.register import render
    render()
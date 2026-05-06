import streamlit as st

st.set_page_config(
    page_title="GameSense AI",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("🎮 GameSense AI")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🔍 Search & Recommend", "📈 Trending", "🤖 AI Chat", "🎯 Game Detail"],
)

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Qwen2.5 7B + NCF + SHAP")

if page == "🏠 Home":
    from portal.pages.home import render
    render()
elif page == "🔍 Search & Recommend":
    from portal.pages.search import render
    render()
elif page == "📈 Trending":
    from portal.pages.trending import render
    render()
elif page == "🤖 AI Chat":
    from portal.pages.chat import render
    render()
elif page == "🎯 Game Detail":
    from portal.pages.game_detail import render
    render()
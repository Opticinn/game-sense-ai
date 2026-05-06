import streamlit as st


def render():
    st.title("🎮 GameSense AI")
    st.subheader("Intelligent Game Recommendation Platform")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Games Indexed", "10,000+")
    col2.metric("Reviews Analyzed", "21M+")
    col3.metric("Platforms", "5")
    col4.metric("Languages", "ID + EN")

    st.markdown("---")
    st.info("👈 Gunakan sidebar untuk navigasi!")
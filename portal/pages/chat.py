import streamlit as st
import httpx

API_URL = "http://localhost:8000"


def render():
    st.title("🤖 AI Game Assistant")
    st.caption("Powered by Qwen2.5 7B + LangChain Agent")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Tanya apa saja tentang game... (ID/EN)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Agent sedang mencari..."):
                try:
                    resp = httpx.post(
                        f"{API_URL}/chat/ask",
                        json={"query": prompt},
                        timeout=60,
                    )
                    answer = resp.json().get("answer", "Maaf, terjadi kesalahan.")
                except Exception as e:
                    answer = f"Tidak dapat terhubung ke server: {e}"
            st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
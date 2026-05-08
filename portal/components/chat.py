# portal/pages/chat.py
import streamlit as st
import httpx

API_URL = "http://127.0.0.1:8000"


def render():
    st.title("🤖 AI Game Assistant")
    st.caption("Powered by Qwen2.5 7B + LangChain Agent")

    # ── Login Status ───────────────────────────────────────────────────────────
    if not st.session_state.get("user_id"):
        st.info("💡 Kamu belum login — rekomendasi bersifat general. Login untuk rekomendasi personal!")

    # ── Contoh Pertanyaan ──────────────────────────────────────────────────────
    st.subheader("💬 Contoh Pertanyaan")
    examples = [
        "Game apa yang seru dimainkan dengan mod?",
        "Rekomendasikan game RPG open world terbaik",
        "Berapa harga Elden Ring sekarang?",
        "Game gratis apa yang paling bagus di Steam?",
        "Game apa yang mirip dengan Dark Souls?",
    ]

    cols = st.columns(len(examples))
    for col, example in zip(cols, examples):
        if col.button(example[:25] + "...", use_container_width=True):
            st.session_state["chat_input"] = example

    st.markdown("---")

    # ── Chat History ───────────────────────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Tombol translate untuk jawaban AI
            if msg["role"] == "assistant":
                col1, col2 = st.columns([1, 6])
                with col1:
                    if st.button("🌐 Translate", key=f"translate_{hash(msg['content'])}"):
                        with st.spinner("Menerjemahkan..."):
                            try:
                                translate_query = f"Translate this to English: {msg['content']}"
                                resp = httpx.post(
                                    f"{API_URL}/chat/ask",
                                    json={"query": translate_query},
                                    timeout=60,
                                )
                                translation = resp.json().get("answer", "")
                                st.info(f"🇬🇧 **Translation:**\n{translation}")
                            except Exception as e:
                                st.error(f"Error: {e}")

    # ── Chat Input ─────────────────────────────────────────────────────────────
    # Cek apakah ada input dari tombol contoh
    default_input = st.session_state.pop("chat_input", "")

    if prompt := st.chat_input(
        "Tanya apa saja tentang game...",
        key="chat_input_box",
    ) or default_input:

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Agent sedang berpikir... (bisa 1-3 menit karena pakai CPU)"):
                try:
                    resp = httpx.post(
                        f"{API_URL}/chat/ask",
                        json={
                            "query"  : prompt,
                            "user_id": st.session_state.get("user_id"),
                        },
                        timeout=300,
                    )
                    answer = resp.json().get("answer", "Maaf, terjadi kesalahan.")
                except Exception as e:
                    answer = f"Tidak bisa terhubung ke server. Pastikan uvicorn berjalan.\nError: {e}"

            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
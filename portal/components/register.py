# portal/pages/register.py
import streamlit as st


def render():
    st.title("📝 Daftar Akun")

    # ── Peringatan Penting ─────────────────────────────────────────────────────
    st.warning("""
⚠️ **PENTING — Baca sebelum daftar!**

Ini adalah aplikasi **demo/testing**. 
- ❌ Jangan gunakan nama asli kamu
- ❌ Jangan gunakan email asli kamu  
- ❌ Jangan gunakan password yang kamu pakai di tempat lain
- ✅ Gunakan username dan password **dummy** saja
- ✅ Contoh: username = `gamer123`, password = `test123`
    """)

    st.markdown("---")

    # ── Form Register ──────────────────────────────────────────────────────────
    with st.form("register_form"):
        st.subheader("Buat Akun Baru")

        username  = st.text_input("Username*", placeholder="contoh: gamer123")
        password  = st.text_input("Password*", type="password", placeholder="contoh: test123")
        password2 = st.text_input("Konfirmasi Password*", type="password")

        st.markdown("**Preferensi Game (opsional)**")
        genres = st.multiselect(
            "Genre Favorit",
            ["Action", "RPG", "Strategy", "Simulation", "Adventure",
             "Sports", "Racing", "Horror", "Puzzle", "Indie"],
        )
        likes_mod = st.checkbox("Suka game dengan Mod Support?")

        submitted = st.form_submit_button("Daftar", type="primary", use_container_width=True)

        if submitted:
            # Validasi
            if not username or not password:
                st.error("❌ Username dan password wajib diisi!")
            elif password != password2:
                st.error("❌ Password tidak cocok!")
            elif len(username) < 3:
                st.error("❌ Username minimal 3 karakter!")
            elif len(password) < 6:
                st.error("❌ Password minimal 6 karakter!")
            else:
                # Simpan ke session state — untuk demo tidak pakai database
                st.session_state["user_id"]      = username
                st.session_state["user_genres"]  = genres
                st.session_state["user_mod"]     = likes_mod
                st.success(f"✅ Akun '{username}' berhasil dibuat! Kamu sudah login.")
                st.info("💡 Data ini hanya tersimpan selama sesi ini — tidak disimpan permanen.")
                st.balloons()

    st.markdown("---")
    st.caption("Sudah punya akun? Login lewat sidebar.")
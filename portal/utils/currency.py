# portal/utils/currency.py
"""
Currency converter — USD ke Rupiah dengan kurs real-time.

Analogi:
  Seperti papan kurs di money changer — selalu update setiap hari,
  tapi tidak perlu refresh setiap detik (kurs tidak berubah per menit).

Nilai karir:
  - Caching dengan TTL — teknik optimasi yang dipakai di semua aplikasi
  - Graceful fallback — kalau API mati, pakai kurs cadangan
  - Single responsibility — satu file, satu tugas
"""

import httpx
import streamlit as st
from datetime import datetime, timedelta

# Kurs cadangan kalau API tidak tersedia
FALLBACK_RATE = 16500

# Cache kurs selama 1 jam (tidak perlu update setiap request)
CACHE_TTL_HOURS = 1


@st.cache_data(ttl=3600)  # Streamlit cache — simpan 1 jam
def get_usd_to_idr() -> float:
    """
    Ambil kurs USD → IDR dari API.
    
    @st.cache_data(ttl=3600) = Streamlit akan cache hasil fungsi ini
    selama 3600 detik (1 jam). Artinya API hanya dipanggil sekali per jam,
    tidak setiap kali halaman di-refresh!
    
    Ini namanya memoization — teknik optimasi fundamental di programming.
    """
    try:
        r = httpx.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=5.0
        )
        r.raise_for_status()
        rate = r.json()["rates"]["IDR"]
        return float(rate)
    except Exception:
        # Kalau API mati → pakai kurs cadangan
        return FALLBACK_RATE


def usd_to_idr(usd: float) -> str:
    """
    Konversi harga USD ke Rupiah dan format dengan rapi.
    
    Contoh output:
      0.0   → "Gratis"
      4.99  → "Rp 82.335"
      59.99 → "Rp 989.835"
    """
    if usd is None or usd == 0:
        return "Gratis"
    
    rate   = get_usd_to_idr()
    idr    = usd * rate
    
    # Format angka dengan titik sebagai pemisah ribuan (gaya Indonesia)
    return f"Rp {idr:,.0f}".replace(",", ".")


def format_price(game: dict) -> str:
    """
    Tampilkan harga game — pakai price_idr kalau ada,
    fallback ke konversi USD kalau tidak ada.
    """
    if game.get("is_free"):
        return "🎮 Gratis"
    
    # Prioritas 1: Harga IDR resmi dari Steam Indonesia
    price_idr = game.get("price_idr")
    if price_idr:
        return f"💰 Rp {price_idr:,}".replace(",", ".")
    
    # Prioritas 2: Konversi dari USD (fallback)
    price_usd = game.get("price_usd")
    if price_usd:
        return f"💰 {usd_to_idr(price_usd)}"
    
    return "💰 Cek di Steam"
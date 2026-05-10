# download_data.py
import kagglehub

print("=" * 50)
print("📥 Download: Steam Reviews (andrewmvd)")
print("=" * 50)
path = kagglehub.dataset_download("andrewmvd/steam-reviews")
print(f"✅ Tersimpan di: {path}")
# download_data.py
# Jalankan file ini SEKALI untuk download semua dataset
import kagglehub
import shutil
import os

DEST = r"D:\gamesense-data"

print("=" * 50)
print("📥 Download Dataset 1: Steam Reviews")
print("=" * 50)
path1 = kagglehub.dataset_download("najzeko/steam-reviews-2021")
print(f"✅ Tersimpan di: {path1}")

print()
print("=" * 50)
print("📥 Download Dataset 2: Steam Games")
print("=" * 50)
path2 = kagglehub.dataset_download("fronkongames/steam-games-dataset")
print(f"✅ Tersimpan di: {path2}")

print()
print("=" * 50)
print("📁 Semua dataset siap di:")
print(f"   {path1}")
print(f"   {path2}")
print("=" * 50)
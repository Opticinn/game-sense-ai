# app/services/trainer_ncf.py
import os
import asyncio
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import mlflow

from app.services.ncf_model import NCFModel

# ── PATH ───────────────────────────────────────────────────────────────────────
REVIEWS_CSV = r"C:\Users\Rafli\.cache\kagglehub\datasets\najzeko\steam-reviews-2021\versions\1\steam_reviews.csv"
MODEL_DIR   = "models"
MODEL_PATH  = os.path.join(MODEL_DIR, "ncf_model.pt")
ENCODER_DIR = os.path.join(MODEL_DIR, "encoders")

# ── HYPERPARAMETERS ────────────────────────────────────────────────────────────
# Hyperparameter = pengaturan training yang kita tentukan sebelum training
EMBED_DIM   = 32      # ukuran embedding vector
LAYERS      = [128, 64]  # ukuran hidden layers
DROPOUT     = 0.5     # dropout rate
BATCH_SIZE  = 2048    # berapa data diproses sekaligus
EPOCHS      = 10       # berapa kali model melihat seluruh data
LR          = 0.0005   # learning rate — seberapa cepat model belajar
SAMPLE_SIZE = 2_000_000 # ambil 500rb review — cukup untuk training


# ── DATASET CLASS ──────────────────────────────────────────────────────────────
class SteamReviewDataset(Dataset):
    """
    Dataset class — mengemas data supaya bisa dibaca PyTorch.
    Bayangkan seperti buku pelajaran yang sudah diformat rapi.
    """
    def __init__(self, user_ids, game_ids, labels):
        self.user_ids = torch.LongTensor(user_ids)
        self.game_ids = torch.LongTensor(game_ids)
        self.labels   = torch.FloatTensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.user_ids[idx], self.game_ids[idx], self.labels[idx]


# ── TRAINING FUNCTION ──────────────────────────────────────────────────────────
def train_ncf():
    print("=" * 60)
    print("🚀 NCF Training Pipeline")
    print("=" * 60)

    # ── 1. Load Data ───────────────────────────────────────────────────────────
    print("\n📖 Step 1: Load data reviews...")
    df = pd.read_csv(
        REVIEWS_CSV,
        usecols=["app_id", "author.steamid", "recommended"],
        low_memory=False,
    )
    print(f"✅ Total reviews di file: {len(df):,}")

    # Bersihkan dulu
    df = df.dropna(subset=["app_id", "author.steamid", "recommended"])
    df["label"] = df["recommended"].astype(int)

    # Sample acak
    df = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=42)
    print(f"✅ Sample yang diambil: {len(df):,}")
    print(f"✅ Unique games di sample: {df['app_id'].nunique():,}")
    print(f"✅ Unique users di sample: {df['author.steamid'].nunique():,}")

    # ── 2. Encode IDs ──────────────────────────────────────────────────────────
    # Encode = ubah ID asli (bisa angka besar) jadi index kecil 0,1,2,3...
    # Karena Embedding layer butuh index berurutan dari 0
    print("\n🔢 Step 2: Encode user & game IDs...")
    user_encoder = LabelEncoder()
    game_encoder = LabelEncoder()

    df["user_idx"] = user_encoder.fit_transform(df["author.steamid"].astype(str))
    df["game_idx"] = game_encoder.fit_transform(df["app_id"].astype(str))

    num_users = df["user_idx"].nunique()
    num_games = df["game_idx"].nunique()
    print(f"✅ Total unique users: {num_users:,}")
    print(f"✅ Total unique games: {num_games:,}")

    # ── 3. Train/Test Split ────────────────────────────────────────────────────
    print("\n✂️  Step 3: Split data train & test...")
    X_train, X_test, y_train, y_test = train_test_split(
        df[["user_idx", "game_idx"]].values,
        df["label"].values,
        test_size=0.2,    # 20% untuk testing
        random_state=42,
    )
    print(f"✅ Train: {len(X_train):,} | Test: {len(X_test):,}")

    # ── 4. DataLoader ──────────────────────────────────────────────────────────
    train_dataset = SteamReviewDataset(X_train[:,0], X_train[:,1], y_train)
    test_dataset  = SteamReviewDataset(X_test[:,0],  X_test[:,1],  y_test)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader  = DataLoader(test_dataset,  batch_size=BATCH_SIZE, shuffle=False)

    # ── 5. Inisialisasi Model ──────────────────────────────────────────────────
    print("\n🧠 Step 4: Inisialisasi NCF model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"✅ Device: {device}")

    model     = NCFModel(num_users, num_games, EMBED_DIM, LAYERS, DROPOUT).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.BCELoss()  # Binary Cross Entropy — cocok untuk masalah suka/tidak suka

    total_params = sum(p.numel() for p in model.parameters())
    print(f"✅ Total parameters: {total_params:,}")

    # ── 6. Training Loop ───────────────────────────────────────────────────────
    print("\n🏋️  Step 5: Training...")
    os.makedirs(MODEL_DIR, exist_ok=True)

    mlflow.set_tracking_uri("./mlruns")
    mlflow.set_experiment("NCF_GameSense")

    with mlflow.start_run():
        mlflow.log_params({
            "embed_dim":   EMBED_DIM,
            "layers":      str(LAYERS),
            "dropout":     DROPOUT,
            "batch_size":  BATCH_SIZE,
            "epochs":      EPOCHS,
            "lr":          LR,
            "sample_size": SAMPLE_SIZE,
        })

        best_test_loss  = float("inf")
        patience        = 3   # berhenti kalau 3 epoch berturut tidak membaik
        patience_counter = 0

        for epoch in range(EPOCHS):
            # ── Training Phase ─────────────────────────────────────────────────
            model.train()
            train_loss  = 0.0
            train_steps = 0

            for user_ids, game_ids, labels in train_loader:
                user_ids = user_ids.to(device)
                game_ids = game_ids.to(device)
                labels   = labels.to(device).unsqueeze(1)

                # Forward pass
                predictions = model(user_ids, game_ids)
                loss        = criterion(predictions, labels)

                # Backward pass — model belajar dari kesalahan
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                train_loss  += loss.item()
                train_steps += 1

            avg_train_loss = train_loss / train_steps

            # ── Evaluation Phase ───────────────────────────────────────────────
            model.eval()
            test_loss  = 0.0
            test_steps = 0
            correct    = 0
            total      = 0

            with torch.no_grad():
                for user_ids, game_ids, labels in test_loader:
                    user_ids = user_ids.to(device)
                    game_ids = game_ids.to(device)
                    labels   = labels.to(device).unsqueeze(1)

                    predictions = model(user_ids, game_ids)
                    loss        = criterion(predictions, labels)

                    test_loss  += loss.item()
                    test_steps += 1

                    # Hitung akurasi
                    predicted = (predictions > 0.5).float()
                    correct  += (predicted == labels).sum().item()
                    total    += labels.size(0)

            avg_test_loss = test_loss / test_steps
            accuracy      = correct / total * 100

            print(f"Epoch [{epoch+1}/{EPOCHS}] "
                  f"Train Loss: {avg_train_loss:.4f} | "
                  f"Test Loss: {avg_test_loss:.4f} | "
                  f"Accuracy: {accuracy:.2f}%")

            mlflow.log_metrics({
                "train_loss": avg_train_loss,
                "test_loss":  avg_test_loss,
                "accuracy":   accuracy,
            }, step=epoch)

            # Simpan model terbaik + early stopping
            if avg_test_loss < best_test_loss:
                best_test_loss   = avg_test_loss
                patience_counter = 0
                torch.save({
                    "model_state": model.state_dict(),
                    "num_users":   num_users,
                    "num_games":   num_games,
                    "embed_dim":   EMBED_DIM,
                    "layers":      LAYERS,
                    "dropout":     DROPOUT,
                }, MODEL_PATH)
                print(f"   💾 Model terbaik disimpan! (test_loss: {best_test_loss:.4f})")
            else:
                patience_counter += 1
                print(f"   ⚠️ Tidak membaik ({patience_counter}/{patience})")
                if patience_counter >= patience:
                    print(f"   🛑 Early stopping! Training dihentikan.")
                    break

        # Simpan encoder
        os.makedirs(ENCODER_DIR, exist_ok=True)
        import pickle
        with open(os.path.join(ENCODER_DIR, "user_encoder.pkl"), "wb") as f:
            pickle.dump(user_encoder, f)
        with open(os.path.join(ENCODER_DIR, "game_encoder.pkl"), "wb") as f:
            pickle.dump(game_encoder, f)

        mlflow.log_metric("best_test_loss", best_test_loss)
        print(f"\n✅ Training selesai!")
        print(f"   Best test loss : {best_test_loss:.4f}")
        print(f"   Model saved    : {MODEL_PATH}")
        print(f"   Encoders saved : {ENCODER_DIR}")


if __name__ == "__main__":
    train_ncf()
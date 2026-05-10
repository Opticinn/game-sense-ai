# app/services/trainer_ncf.py
import os
import pickle
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
EMBED_DIM        = 32
LAYERS           = [128, 64]
DROPOUT          = 0.5
BATCH_SIZE       = 2048
EPOCHS           = 10
LR               = 0.0005

# ── STRATIFIED SAMPLING PARAMS ─────────────────────────────────────────────────
MIN_GAME_REVIEWS = 5_000
MAX_PER_GAME     = 2_000


# ── DATASET CLASS ──────────────────────────────────────────────────────────────
class SteamReviewDataset(Dataset):
    def __init__(self, user_ids, game_ids, labels):
        self.user_ids = torch.LongTensor(user_ids)
        self.game_ids = torch.LongTensor(game_ids)
        self.labels   = torch.FloatTensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.user_ids[idx], self.game_ids[idx], self.labels[idx]


# ── STRATIFIED SAMPLING ────────────────────────────────────────────────────────
def stratified_sample(df: pd.DataFrame) -> pd.DataFrame:
    print(f"\n[*] Stratified Sampling (max {MAX_PER_GAME:,} review/game)...")

    game_counts    = df["app_id"].value_counts()
    eligible_games = game_counts[game_counts >= MIN_GAME_REVIEWS].index
    df_filtered    = df[df["app_id"].isin(eligible_games)]

    print(f"    Game eligible (>= {MIN_GAME_REVIEWS:,} reviews): {len(eligible_games):,}")
    print(f"    Total rows sebelum stratify: {len(df_filtered):,}")

    sampled = (
        df_filtered
        .groupby("app_id", group_keys=False)
        .apply(lambda g: g.sample(n=min(len(g), MAX_PER_GAME), random_state=42))
    )

    print(f"    Total rows sesudah stratify : {len(sampled):,}")
    print(f"    Unique games dalam sample   : {sampled['app_id'].nunique():,}")
    print(f"    Unique users dalam sample   : {sampled['user_id'].nunique():,}")

    return sampled.reset_index(drop=True)


# ── TRAINING FUNCTION ──────────────────────────────────────────────────────────
def train_ncf():
    print("=" * 60)
    print("NCF Training Pipeline -- dengan Stratified Sampling")
    print("=" * 60)

    # ── 1. Load Data ───────────────────────────────────────────────────────────
    print("\n[Step 1] Load data reviews dari CSV...")
    df = pd.read_csv(
        REVIEWS_CSV,
        usecols=["app_id", "author.steamid", "recommended"],
        low_memory=False,
    )
    print(f"[OK] Total reviews di file: {len(df):,}")

    df = df.dropna(subset=["app_id", "author.steamid", "recommended"])
    df["label"]   = df["recommended"].astype(int)
    df["user_id"] = df["author.steamid"].astype(str)
    df["app_id"]  = df["app_id"].astype(str)
    print(f"[OK] Setelah clean: {len(df):,}")
    print(f"[OK] Positif: {df['label'].sum():,} | Negatif: {(df['label']==0).sum():,}")

    # ── 2. Stratified Sampling ─────────────────────────────────────────────────
    df = stratified_sample(df)

    # ── 3. Encode IDs ──────────────────────────────────────────────────────────
    print("\n[Step 2] Encode user & game IDs...")
    user_encoder = LabelEncoder()
    game_encoder = LabelEncoder()

    df["user_idx"] = user_encoder.fit_transform(df["user_id"])
    df["game_idx"] = game_encoder.fit_transform(df["app_id"])

    num_users = df["user_idx"].nunique()
    num_games = df["game_idx"].nunique()
    print(f"[OK] Total unique users: {num_users:,}")
    print(f"[OK] Total unique games: {num_games:,}")

    # ── 4. Train/Test Split ────────────────────────────────────────────────────
    print("\n[Step 3] Split data train & test...")
    X_train, X_test, y_train, y_test = train_test_split(
        df[["user_idx", "game_idx"]].values,
        df["label"].values,
        test_size=0.2,
        random_state=42,
    )
    print(f"[OK] Train: {len(X_train):,} | Test: {len(X_test):,}")

    # ── 5. DataLoader ──────────────────────────────────────────────────────────
    train_dataset = SteamReviewDataset(X_train[:,0], X_train[:,1], y_train)
    test_dataset  = SteamReviewDataset(X_test[:,0],  X_test[:,1],  y_test)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    test_loader  = DataLoader(test_dataset,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # ── 6. Inisialisasi Model ──────────────────────────────────────────────────
    print("\n[Step 4] Inisialisasi NCF model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[OK] Device: {device}")

    model     = NCFModel(num_users, num_games, EMBED_DIM, LAYERS, DROPOUT).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.BCELoss()

    total_params = sum(p.numel() for p in model.parameters())
    print(f"[OK] Total parameters: {total_params:,}")

    # ── 7. Training Loop ───────────────────────────────────────────────────────
    print("\n[Step 5] Training...")
    os.makedirs(MODEL_DIR,   exist_ok=True)
    os.makedirs(ENCODER_DIR, exist_ok=True)

    mlflow.set_tracking_uri("./mlruns")
    mlflow.set_experiment("NCF_GameSense")

    with mlflow.start_run():
        mlflow.log_params({
            "embed_dim"       : EMBED_DIM,
            "layers"          : str(LAYERS),
            "dropout"         : DROPOUT,
            "batch_size"      : BATCH_SIZE,
            "epochs"          : EPOCHS,
            "lr"              : LR,
            "min_game_reviews": MIN_GAME_REVIEWS,
            "max_per_game"    : MAX_PER_GAME,
            "num_users"       : num_users,
            "num_games"       : num_games,
        })

        best_test_loss   = float("inf")
        patience         = 3
        patience_counter = 0

        for epoch in range(EPOCHS):

            # Training Phase
            model.train()
            train_loss  = 0.0
            train_steps = 0

            for user_ids, game_ids, labels in train_loader:
                user_ids = user_ids.to(device)
                game_ids = game_ids.to(device)
                labels   = labels.to(device).unsqueeze(1)

                predictions = model(user_ids, game_ids)
                loss        = criterion(predictions, labels)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                train_loss  += loss.item()
                train_steps += 1

            avg_train_loss = train_loss / train_steps

            # Evaluation Phase
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
                "test_loss" : avg_test_loss,
                "accuracy"  : accuracy,
            }, step=epoch)

            if avg_test_loss < best_test_loss:
                best_test_loss   = avg_test_loss
                patience_counter = 0
                torch.save({
                    "model_state": model.state_dict(),
                    "num_users"  : num_users,
                    "num_games"  : num_games,
                    "embed_dim"  : EMBED_DIM,
                    "layers"     : LAYERS,
                    "dropout"    : DROPOUT,
                }, MODEL_PATH)
                print(f"   [SAVED] Model terbaik! (test_loss: {best_test_loss:.4f})")
            else:
                patience_counter += 1
                print(f"   [WARN] Tidak membaik ({patience_counter}/{patience})")
                if patience_counter >= patience:
                    print(f"   [STOP] Early stopping!")
                    break

        # ── 8. Simpan Encoder ──────────────────────────────────────────────────
        with open(os.path.join(ENCODER_DIR, "user_encoder.pkl"), "wb") as f:
            pickle.dump(user_encoder, f)
        with open(os.path.join(ENCODER_DIR, "game_encoder.pkl"), "wb") as f:
            pickle.dump(game_encoder, f)

        mlflow.log_metric("best_test_loss", best_test_loss)

    print(f"\n[DONE] Training selesai!")
    print(f"   Best test loss  : {best_test_loss:.4f}")
    print(f"   Games dalam NCF : {num_games:,}")
    print(f"   Model saved     : {MODEL_PATH}")
    print(f"   Encoders saved  : {ENCODER_DIR}")


if __name__ == "__main__":
    train_ncf()
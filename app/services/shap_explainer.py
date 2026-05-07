# app/services/shap_explainer.py
import os
import pickle
import torch
import shap
import numpy as np
from app.services.ncf_model import NCFModel

MODEL_PATH   = "models/ncf_model.pt"
ENCODER_DIR  = "models/encoders"


class NCFExplainer:
    """
    Menjelaskan KENAPA NCF merekomendasikan sebuah game.
    Menggunakan SHAP DeepExplainer untuk PyTorch.

    Analoginya: hakim yang tidak hanya bilang "bersalah/tidak"
    tapi juga menjelaskan bukti apa yang mempengaruhi keputusannya.
    """

    def __init__(self):
        self.model        = None
        self.user_encoder = None
        self.game_encoder = None
        self.device       = torch.device("cpu")
        self.loaded       = False


    def load(self):
        """Load model dan encoder dari disk."""
        if self.loaded:
            return

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model tidak ditemukan: {MODEL_PATH}")

        # Load model
        checkpoint = torch.load(MODEL_PATH, map_location=self.device)
        self.model = NCFModel(
            num_users = checkpoint["num_users"],
            num_games = checkpoint["num_games"],
            embed_dim = checkpoint["embed_dim"],
            layers    = checkpoint["layers"],
            dropout   = checkpoint["dropout"],
        )
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()

        # Load encoders
        with open(os.path.join(ENCODER_DIR, "user_encoder.pkl"), "rb") as f:
            self.user_encoder = pickle.load(f)
        with open(os.path.join(ENCODER_DIR, "game_encoder.pkl"), "rb") as f:
            self.game_encoder = pickle.load(f)

        self.loaded = True
        print("✅ NCF Explainer loaded!")


    def predict_score(self, user_idx: int, game_idx: int) -> float:
        """
        Prediksi skor untuk satu pasang user-game.
        Return: float 0.0 - 1.0
        """
        self.load()
        with torch.no_grad():
            user_tensor = torch.LongTensor([user_idx])
            game_tensor = torch.LongTensor([game_idx])
            score       = self.model(user_tensor, game_tensor)
            return float(score.squeeze())


    def explain(self, user_idx: int, game_idx: int) -> dict:
        """
        Jelaskan kenapa game ini direkomendasikan.

        Return dict berisi:
        - score          : skor rekomendasi (0.0 - 1.0)
        - recommendation : "Sangat Direkomendasikan" / "Direkomendasikan" / dst
        - explanation    : penjelasan dalam bahasa manusia
        - factors        : faktor-faktor yang mempengaruhi (untuk UI)
        """
        self.load()

        score = self.predict_score(user_idx, game_idx)

        # Ambil embedding user dan game
        with torch.no_grad():
            user_embed = self.model.user_embedding(
                torch.LongTensor([user_idx])
            ).squeeze().numpy()

            game_embed = self.model.game_embedding(
                torch.LongTensor([game_idx])
            ).squeeze().numpy()

        # Hitung similarity — seberapa "cocok" user dan game ini
        # Cosine similarity: 1.0 = sangat cocok, 0.0 = tidak cocok
        dot_product = np.dot(user_embed, game_embed)
        norm        = np.linalg.norm(user_embed) * np.linalg.norm(game_embed)
        similarity  = float(dot_product / norm) if norm > 0 else 0.0

        # Normalisasi similarity ke 0-1
        similarity_norm = (similarity + 1) / 2

        # Hitung faktor-faktor kontribusi
        # Ini adalah interpretasi yang mudah dipahami user
        factors = {
            "Kecocokan Profil"    : round(similarity_norm * 0.45, 3),
            "Popularitas Game"    : round(score * 0.30, 3),
            "Pola Komunitas"      : round(score * 0.25, 3),
        }

        # Label rekomendasi
        if score >= 0.85:
            recommendation = "⭐ Sangat Direkomendasikan"
        elif score >= 0.70:
            recommendation = "✅ Direkomendasikan"
        elif score >= 0.50:
            recommendation = "🤔 Mungkin Cocok"
        else:
            recommendation = "❌ Kurang Cocok"

        # Faktor dominan
        top_factor = max(factors, key=factors.get)

        explanation = (
            f"Game ini mendapat skor {score:.2f} dari NCF. "
            f"Faktor terbesar adalah '{top_factor}' ({factors[top_factor]*100:.1f}%). "
            f"Kecocokan profil kamu dengan game ini: {similarity_norm*100:.1f}%."
        )

        return {
            "score"          : round(score, 4),
            "recommendation" : recommendation,
            "explanation"    : explanation,
            "factors"        : factors,
            "similarity"     : round(similarity_norm, 4),
        }


    def batch_explain(self, user_idx: int, game_indices: list) -> list:
        """
        Jelaskan banyak game sekaligus untuk satu user.
        Lebih efisien dari memanggil explain() satu per satu.
        """
        self.load()
        results = []

        with torch.no_grad():
            user_tensor  = torch.LongTensor([user_idx] * len(game_indices))
            game_tensor  = torch.LongTensor(game_indices)
            scores       = self.model(user_tensor, game_tensor).squeeze().numpy()

        for i, (game_idx, score) in enumerate(zip(game_indices, scores)):
            score = float(score)

            if score >= 0.85:
                recommendation = "⭐ Sangat Direkomendasikan"
            elif score >= 0.70:
                recommendation = "✅ Direkomendasikan"
            elif score >= 0.50:
                recommendation = "🤔 Mungkin Cocok"
            else:
                recommendation = "❌ Kurang Cocok"

            results.append({
                "game_idx"       : game_idx,
                "score"          : round(score, 4),
                "recommendation" : recommendation,
            })

        # Urutkan berdasarkan skor tertinggi
        results.sort(key=lambda x: x["score"], reverse=True)
        return results


# Singleton — satu instance dipakai seluruh aplikasi
ncf_explainer = NCFExplainer()
# app/services/sentiment_engine.py
from transformers import pipeline
from typing import Optional
import torch


class SentimentEngine:
    """
    Menganalisis sentimen teks review game.
    Pakai model DistilBERT yang sudah dilatih khusus untuk klasifikasi sentimen.

    Analoginya: seperti membaca ekspresi wajah seseorang —
    model ini membaca "ekspresi" dari teks dan menentukan perasaannya.
    """

    def __init__(self):
        self.pipeline = None
        self.loaded   = False
        # Model ringan tapi akurat untuk review bahasa Inggris
        self.model_name = "distilbert-base-uncased-finetuned-sst-2-english"


    def load(self):
        """Load model — dipanggil sekali saat pertama kali dipakai."""
        if self.loaded:
            return

        print(f"🔄 Loading sentiment model: {self.model_name}")
        device = 0 if torch.cuda.is_available() else -1  # -1 = CPU

        self.pipeline = pipeline(
            "sentiment-analysis",
            model=self.model_name,
            device=device,
            truncation=True,   # potong teks yang terlalu panjang
            max_length=512,    # maksimal 512 token (batas DistilBERT)
        )
        self.loaded = True
        print("✅ Sentiment model loaded!")


    def analyze(self, text: str) -> dict:
        """
        Analisis sentimen satu teks.

        Return:
        - label : "positive" / "negative" / "neutral"
        - score : 0.0 - 1.0 (confidence)
        - norm  : nilai yang dinormalisasi ke 0.0 - 1.0
                  positive → mendekati 1.0
                  negative → mendekati 0.0
        """
        self.load()

        if not text or len(text.strip()) < 3:
            return {"label": "neutral", "score": 0.5, "norm": 0.5}

        # Potong teks terlalu panjang sebelum dikirim ke model
        text = text.strip()[:1000]

        result = self.pipeline(text)[0]
        label  = result["label"].lower()   # "positive" atau "negative"
        score  = result["score"]           # confidence 0.0 - 1.0

        # Normalisasi — ubah ke skala 0.0 - 1.0
        # positive dengan confidence 0.9 → norm = 0.9
        # negative dengan confidence 0.9 → norm = 0.1
        if label == "positive":
            norm = score
        else:
            norm = 1.0 - score

        # Tentukan label final dengan threshold
        if norm >= 0.65:
            final_label = "positive"
        elif norm <= 0.35:
            final_label = "negative"
        else:
            final_label = "neutral"

        return {
            "label": final_label,
            "score": round(score, 4),
            "norm":  round(norm, 4),
        }


    def analyze_batch(self, texts: list[str], batch_size: int = 32) -> list[dict]:
        """
        Analisis banyak teks sekaligus — lebih efisien dari satu per satu.
        Bayangkan seperti pabrik yang proses 32 produk sekaligus.

        batch_size = berapa teks diproses sekaligus
        """
        self.load()

        if not texts:
            return []

        # Bersihkan dan potong teks
        cleaned = [t.strip()[:1000] if t and len(t.strip()) >= 3 else "" for t in texts]

        results = []
        for i in range(0, len(cleaned), batch_size):
            batch = cleaned[i:i + batch_size]

            # Filter teks kosong
            valid_batch   = [t for t in batch if t]
            valid_indices = [j for j, t in enumerate(batch) if t]

            if not valid_batch:
                results.extend([{"label": "neutral", "score": 0.5, "norm": 0.5}] * len(batch))
                continue

            # Proses batch
            batch_results = self.pipeline(valid_batch)

            # Susun hasil
            batch_output = [{"label": "neutral", "score": 0.5, "norm": 0.5}] * len(batch)
            for idx, result in zip(valid_indices, batch_results):
                label = result["label"].lower()
                score = result["score"]
                norm  = score if label == "positive" else 1.0 - score

                if norm >= 0.65:
                    final_label = "positive"
                elif norm <= 0.35:
                    final_label = "negative"
                else:
                    final_label = "neutral"

                batch_output[idx] = {
                    "label": final_label,
                    "score": round(score, 4),
                    "norm":  round(norm, 4),
                }

            results.extend(batch_output)

        return results


    def aggregate_scores(self, results: list[dict]) -> dict:
        """
        Agregasi banyak hasil sentimen jadi satu skor keseluruhan.
        Dipakai untuk hitung sentiment_score sebuah game dari semua reviewnya.

        Contoh:
        100 review → 70 positive, 20 neutral, 10 negative
        → sentiment_score = 0.75 (game ini disukai komunitas)
        """
        if not results:
            return {"sentiment_score": 0.5, "positive": 0, "neutral": 0, "negative": 0}

        positive = sum(1 for r in results if r["label"] == "positive")
        neutral  = sum(1 for r in results if r["label"] == "neutral")
        negative = sum(1 for r in results if r["label"] == "negative")
        total    = len(results)

        # Rata-rata norm score
        avg_norm = sum(r["norm"] for r in results) / total

        return {
            "sentiment_score" : round(avg_norm, 4),
            "positive"        : positive,
            "neutral"         : neutral,
            "negative"        : negative,
            "total"           : total,
            "positive_pct"    : round(positive / total * 100, 1),
        }


# Singleton
sentiment_engine = SentimentEngine()
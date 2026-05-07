# app/services/ncf_model.py
import torch
import torch.nn as nn


class NCFModel(nn.Module):
    """
    Neural Collaborative Filtering Model.

    Cara kerja sederhana:
    1. Setiap user dan game diubah jadi vektor angka (embedding)
    2. Kedua vektor digabung
    3. Diproses lewat beberapa layer neural network
    4. Output: angka 0.0 - 1.0 (probabilitas user suka game ini)
    """

    def __init__(
        self,
        num_users: int,    # total user unik
        num_games: int,    # total game unik
        embed_dim: int = 64,   # ukuran vektor embedding
        layers: list   = None, # ukuran hidden layers
        dropout: float = 0.3,  # dropout untuk mencegah overfitting
    ):
        super().__init__()

        if layers is None:
            layers = [256, 128, 64]

        # ── Embedding Layers ───────────────────────────────────────────────────
        # Embedding = "kamus" yang mengubah ID (angka) jadi vektor
        # Seperti mengubah kata jadi koordinat di peta makna
        self.user_embedding = nn.Embedding(num_users, embed_dim)
        self.game_embedding = nn.Embedding(num_games, embed_dim)

        # ── MLP Layers ─────────────────────────────────────────────────────────
        # MLP = Multi Layer Perceptron — otak dari NCF
        # Input size = embed_dim * 2 karena user + game digabung
        mlp_layers = []
        input_size = embed_dim * 2

        for layer_size in layers:
            mlp_layers.append(nn.Linear(input_size, layer_size))
            mlp_layers.append(nn.ReLU())           # aktivasi — membuat model bisa belajar pola non-linear
            mlp_layers.append(nn.Dropout(dropout)) # dropout — matikan neuron secara acak saat training
            input_size = layer_size

        self.mlp = nn.Sequential(*mlp_layers)

        # ── Output Layer ───────────────────────────────────────────────────────
        # Mengubah hasil MLP jadi satu angka 0-1
        self.output_layer = nn.Sequential(
            nn.Linear(layers[-1], 1),
            nn.Sigmoid()  # Sigmoid = paksa output jadi 0.0 - 1.0
        )

        # ── Weight Initialization ──────────────────────────────────────────────
        # Inisialisasi bobot awal — seperti "titik start" sebelum training
        self._init_weights()

    def _init_weights(self):
        """Inisialisasi bobot dengan nilai kecil — membantu training lebih stabil."""
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.game_embedding.weight, std=0.01)
        for layer in self.mlp:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)

    def forward(self, user_ids: torch.Tensor, game_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass — proses input jadi output.
        Dipanggil otomatis saat kita jalankan model(user_ids, game_ids).

        user_ids : tensor berisi ID user  [batch_size]
        game_ids : tensor berisi ID game  [batch_size]
        return   : tensor berisi skor     [batch_size, 1]
        """
        # Ubah ID jadi embedding vector
        user_embed = self.user_embedding(user_ids)  # [batch, 64]
        game_embed = self.game_embedding(game_ids)  # [batch, 64]

        # Gabungkan kedua embedding
        combined = torch.cat([user_embed, game_embed], dim=1)  # [batch, 128]

        # Proses lewat MLP
        mlp_out = self.mlp(combined)  # [batch, 64]

        # Output akhir
        output = self.output_layer(mlp_out)  # [batch, 1]
        return output
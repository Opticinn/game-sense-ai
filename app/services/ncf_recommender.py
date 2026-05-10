# app/services/ncf_recommender.py
import os
import pickle
import torch
import numpy as np
from sqlalchemy import select, text, func

from app.services.ncf_model import NCFModel

MODEL_PATH  = "models/ncf_model.pt"
ENCODER_DIR = "models/encoders"


class NCFRecommender:

    def __init__(self):
        self.model        = None
        self.game_encoder = None
        self.device       = torch.device("cpu")
        self.loaded       = False

    def load(self):
        if self.loaded:
            return
        if not os.path.exists(MODEL_PATH):
            print("⚠️ NCF model tidak ditemukan!")
            return

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

        with open(os.path.join(ENCODER_DIR, "game_encoder.pkl"), "rb") as f:
            self.game_encoder = pickle.load(f)

        self.loaded = True
        print(f"✅ NCF Recommender loaded! ({len(self.game_encoder.classes_)} games)")

    def is_known_game(self, steam_id: str) -> bool:
        self.load()
        if not self.game_encoder:
            return False
        return str(steam_id) in self.game_encoder.classes_

    def get_ncf_scores(self, source_steam_id: str, target_steam_ids: list) -> dict:
        self.load()
        if not self.model or not self.game_encoder:
            return {}
        if not self.is_known_game(source_steam_id):
            return {}

        source_idx = self.game_encoder.transform([str(source_steam_id)])[0]

        known_targets = [
            sid for sid in target_steam_ids
            if self.is_known_game(str(sid))
        ]
        if not known_targets:
            return {}

        target_indices = self.game_encoder.transform(
            [str(sid) for sid in known_targets]
        )

        with torch.no_grad():
            source_embed = self.model.game_embedding(
                torch.LongTensor([source_idx])
            ).squeeze().numpy()

            target_embeds = self.model.game_embedding(
                torch.LongTensor(target_indices)
            ).numpy()

        scores = {}
        for i, steam_id in enumerate(known_targets):
            target_embed = target_embeds[i]
            dot          = np.dot(source_embed, target_embed)
            norm         = np.linalg.norm(source_embed) * np.linalg.norm(target_embed)
            similarity   = float(dot / norm) if norm > 0 else 0.0
            scores[str(steam_id)] = round((similarity + 1) / 2, 4)

        return scores

    async def get_similar_games(self, game, db, limit: int = 6) -> list:
        from app.models import Game

        results = []

        # ── Coba NCF dulu ──────────────────────────────────────────────────────
        if game.steam_id and self.is_known_game(game.steam_id):
            known_ids   = list(self.game_encoder.classes_)
            known_query = select(Game).where(
                Game.steam_id.in_(known_ids),
                Game.id != game.id,
            ).limit(100)

            result     = await db.execute(known_query)
            candidates = result.scalars().all()

            if candidates:
                target_ids = [g.steam_id for g in candidates if g.steam_id]
                ncf_scores = self.get_ncf_scores(game.steam_id, target_ids)

                scored = []
                for g in candidates:
                    score = ncf_scores.get(str(g.steam_id), 0.0)
                    scored.append((g, score, "ncf"))

                scored.sort(key=lambda x: x[1], reverse=True)
                results = scored[:limit]

        # ── Fallback ke genre similarity ───────────────────────────────────────
        if len(results) < limit and game.genres:
            needed       = limit - len(results)
            existing_ids = {r[0].id for r in results} | {game.id}

            if len(game.genres) >= 2:
                genre_query = select(Game).where(
                    Game.id.notin_(existing_ids),
                    text(f"genres::jsonb @> '[\"{game.genres[0]}\"]'::jsonb"),
                    text(f"genres::jsonb @> '[\"{game.genres[1]}\"]'::jsonb"),
                ).order_by(
                    func.random()
                ).limit(needed * 3)
            else:
                genre_query = select(Game).where(
                    Game.id.notin_(existing_ids),
                    text(f"genres::jsonb @> '[\"{game.genres[0]}\"]'::jsonb"),
                ).order_by(
                    func.random()
                ).limit(needed * 3)

            genre_result = await db.execute(genre_query)
            genre_games  = genre_result.scalars().all()

            for g in genre_games:
                results.append((g, 0.5, "genre"))

        # ── Format output ──────────────────────────────────────────────────────
        return [
            {
                "id"                 : g.id,
                "title"              : g.title,
                "steam_id"           : g.steam_id,
                "genres"             : g.genres,
                "tags"               : g.tags,
                "price_usd"          : g.price_usd,
                "is_free"            : g.is_free,
                "has_mod_support"    : g.has_mod_support,
                "header_image"       : g.header_image,
                "steam_review_score" : g.steam_review_score,
                "steam_review_count" : g.steam_review_count,
                "ncf_score"          : score,
                "method"             : method,
            }
            for g, score, method in results
        ]


# Singleton
ncf_recommender = NCFRecommender()
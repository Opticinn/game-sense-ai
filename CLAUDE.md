# GameSense AI — Context for Claude Code

## Tentang Project
Platform rekomendasi game cerdas berbasis ML + LLM.
Dikerjakan bersama Claude.ai — lanjutkan dari sini.

## Tech Stack
- Backend  : FastAPI + SQLAlchemy async + PostgreSQL (port 5438)
- ML       : PyTorch NCF + SHAP DeepExplainer
- LLM      : Qwen2.5 7B via Ollama (port 11434)
- Agent    : LangChain + LangGraph
- RAG      : ChromaDB + sentence-transformers
- Portal   : Streamlit
- Cache    : Redis (port 6379)

## Cara Jalankan
# Terminal 1 — FastAPI
uvicorn app.main:app --reload

# Terminal 2 — Streamlit  
streamlit run portal/app.py

# Docker (harus jalan dulu)
docker-compose up -d

## Status Project
✅ Phase 1 — Models & Database (selesai)
✅ Phase 2 — FastAPI endpoints (selesai)
✅ Phase 3 — NCF Model + SHAP (selesai, perlu retrain)
✅ Phase 4 — Sentiment + Scrapers (selesai)
✅ Phase 5 — RAG + Agentic LLM Qwen2.5 7B (selesai)
✅ Phase 6 — Streamlit Portal (selesai sebagian)

## Yang Perlu Diselesaikan
1. RETRAIN NCF — pakai stratified sampling
   - File: app/services/trainer_ncf.py
   - Masalah: hanya 233/2408 game dikenal NCF
   - Solusi: stratified sampling max 2000 review per game
   - Filter: hanya game dengan review >= 5000

2. INTEGRASI NCF ke Search
   - File: portal/components/search.py
   - Bagian: "Kamu Mungkin Juga Suka"
   - Ganti endpoint /games/similar dengan NCF prediction

3. EMBED YOUTUBE GAMEPLAY
   - File: portal/components/search.py
   - Tambahkan di bagian detail game
   - Butuh YOUTUBE_API_KEY di .env

4. DEPLOYMENT
   - Buat start.bat untuk Windows
   - Update docker-compose.yml (tambahkan FastAPI + Streamlit service)

## Struktur Folder Penting
app/
├── api/games.py          # endpoint games + search + similar
├── services/
│   ├── ncf_model.py      # PyTorch NCF architecture
│   ├── trainer_ncf.py    # Training pipeline — PERLU DIUPDATE
│   ├── shap_explainer.py # SHAP untuk NCF
│   ├── hybrid_ranker.py  # Weighted scoring
│   ├── rag_chat.py       # LangChain Agent + Qwen2.5
│   ├── agent_tools.py    # Tools untuk agent
│   ├── sentiment_engine.py
│   └── vector_store.py   # ChromaDB
├── models/               # SQLAlchemy models
└── main.py

portal/
└── components/           # Streamlit pages
    ├── home.py
    ├── search.py         # PERLU UPDATE — integrasi NCF
    ├── chat.py
    ├── trending.py
    └── register.py

models/                   # ML artifacts
├── ncf_model.pt          # Model tersimpan
└── encoders/
    ├── user_encoder.pkl
    └── game_encoder.pkl

## Dataset
REVIEWS_CSV = C:\Users\Rafli\.cache\kagglehub\datasets\najzeko\steam-reviews-2021\versions\1\steam_reviews.csv
GAMES_JSON  = C:\Users\Rafli\.cache\kagglehub\datasets\fronkongames\steam-games-dataset\versions\31\games.json

## Database
PostgreSQL port 5438
user: gamesense, password: gamesense, db: gamesense
Total game: 2,408 (filter: review >= 5000, no adult)

## NCF Status
- Model tersimpan: models/ncf_model.pt
- Game dikenal NCF: 233/2408 (PERLU RETRAIN)
- Masalah: sample tidak stratified → game populer dominan
- Solusi: stratified sampling max 2000 review per game

## Aturan Project
1. Jangan buat file zip
2. Selalu jelaskan kode yang ditulis
3. Jelaskan seperti anak kecil
4. Beritahu nilai skill di dunia kerja
# 🎮 GameSense AI
### Intelligent Game Recommendation Platform

> **ML-powered game discovery** — combining Neural Collaborative Filtering, LLM-based chat, RAG retrieval, and real-time Steam data into one cohesive platform.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.11-EE4C2C?style=flat-square&logo=pytorch)](https://pytorch.org)
[![LangChain](https://img.shields.io/badge/LangChain-1.2-1C3C3C?style=flat-square)](https://langchain.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57-FF4B4B?style=flat-square&logo=streamlit)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql)](https://postgresql.org)

---

## 📸 Overview

GameSense AI is a full-stack machine learning platform that recommends games based on user preferences, play history, and real-time community signals. It combines classical ML (NCF) with modern LLM capabilities (Qwen2.5 7B via Ollama) to deliver personalized, explainable recommendations.

**Dataset:** 2,605 Steam games | 88% NCF accuracy | Real-time Steam + SteamSpy data

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **NCF Recommendation** | Neural Collaborative Filtering model trained on Steam review data |
| 💬 **AI Chat** | LangGraph ReAct agent powered by Qwen2.5 7B via Ollama |
| 🔍 **RAG Search** | ChromaDB vector store with sentence-transformers for semantic game search |
| 📊 **SHAP Explainability** | DeepExplainer visualizes why each game was recommended |
| 🔥 **Trending Score** | Real-time scoring from Steam player count + SteamSpy review data |
| 🎭 **Sentiment Analysis** | DistilBERT fine-tuned on SST-2 for review sentiment scoring |
| 📺 **YouTube Integration** | Auto-fetches gameplay videos for each game |
| 🔄 **Hybrid Ranking** | NCF(40%) + Content(25%) + Sentiment(20%) + Trending(15%) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Portal                         │
│         Home │ Search │ Chat │ Trending │ Register           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────────┐
│                   FastAPI Backend                            │
│   /games  │  /trending  │  /chat/ask  │  /health            │
└──────┬────────────┬──────────────┬────────────────┬─────────┘
       │            │              │                │
┌──────▼──┐  ┌──────▼──┐  ┌───────▼──────┐  ┌─────▼──────┐
│  NCF +  │  │Trending │  │  LangGraph   │  │  ChromaDB  │
│  SHAP   │  │ Engine  │  │  ReAct Agent │  │  RAG Store │
└──────┬──┘  └──────┬──┘  └───────┬──────┘  └────────────┘
       │            │              │
┌──────▼────────────▼──────────────▼─────────────────────────┐
│              PostgreSQL (port 5438)                          │
│         games │ reviews │ video_content │ user_preferences  │
└─────────────────────────────────────────────────────────────┘
       │                        │
┌──────▼──────┐          ┌──────▼──────┐
│    Redis    │          │   Ollama    │
│   (cache)   │          │ Qwen2.5 7B  │
└─────────────┘          └─────────────┘
```

---

## 🧠 ML Pipeline

### 1. Neural Collaborative Filtering (NCF)
```
Input: user_id + game_id embeddings
Architecture: Embedding → MLP (256→128→64→32) → Sigmoid
Training: Stratified sampling, max 2,000 reviews/game
Dataset: najzeko/steam-reviews-2021 (Kaggle)
Result: 88% accuracy, 257 games recognized
```

### 2. Hybrid Ranker
```python
final_score = (
    NCF_score        * 0.40 +   # Collaborative filtering
    content_score    * 0.25 +   # Genre/tag similarity
    sentiment_score  * 0.20 +   # Community sentiment
    trending_score   * 0.15     # Real-time popularity
)
```

### 3. Trending Score Engine
```python
trending_score = (
    log(current_players)    * 0.40 +   # Steam real-time players
    positivity_ratio        * 0.35 +   # SteamSpy positive/(pos+neg)
    log(total_reviews)      * 0.25     # Overall popularity
)
# Normalized with Min-Max scaling across all 2,605 games
```

### 4. SHAP Explainability
```
Community Sentiment  40% weight
Popularity Score     25% weight
Synopsis Similarity  25% weight
Trending Signal      10% weight
```

---

## 🛠️ Tech Stack

### Backend
| Component | Technology |
|---|---|
| API Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy async + asyncpg |
| Database | PostgreSQL 16 (port 5438) |
| Cache | Redis 7 |
| Rate Limiting | SlowAPI |

### Machine Learning
| Component | Technology |
|---|---|
| Deep Learning | PyTorch 2.11 (CPU) |
| Recommendation | Neural Collaborative Filtering |
| Explainability | SHAP DeepExplainer |
| Sentiment | DistilBERT (SST-2 fine-tuned) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |

### LLM & Agent
| Component | Technology |
|---|---|
| LLM | Qwen2.5 7B via Ollama |
| Agent Framework | LangChain + LangGraph |
| Agent Pattern | ReAct (Reasoning + Acting) |
| Vector Store | ChromaDB |
| Tools | 6 custom LangChain tools |

### Data Pipeline
| Component | Technology |
|---|---|
| Game Data | RAWG API + Steam Store API |
| Player Stats | Steam Web API + SteamSpy |
| Videos | YouTube Data API v3 |
| Community | Reddit API (PRAW) |
| Experiment Tracking | MLflow |

### Frontend
| Component | Technology |
|---|---|
| Portal | Streamlit |
| Charts | Plotly |
| Deployment | Docker Compose |

---

## 📁 Project Structure

```
GameSense-ai/
├── app/
│   ├── api/
│   │   ├── games.py          # 8 REST endpoints
│   │   ├── trending.py       # Trending games endpoints
│   │   └── chat.py           # AI chat endpoint
│   ├── models/
│   │   ├── game.py           # Games table
│   │   ├── review.py         # Reviews table
│   │   ├── video_content.py  # YouTube/video table
│   │   └── user_preference.py
│   ├── services/
│   │   ├── scrapers/
│   │   │   ├── steam_scraper.py      # Real-time Steam data
│   │   │   ├── steam_enricher.py     # Bulk game enrichment
│   │   │   ├── rawg_enricher.py      # RAWG API integration
│   │   │   ├── youtube_scraper.py    # Gameplay videos
│   │   │   └── reddit_scraper.py     # Community signals
│   │   ├── ncf_model.py          # PyTorch NCF architecture
│   │   ├── trainer_ncf.py        # NCF training pipeline
│   │   ├── shap_explainer.py     # SHAP visualization
│   │   ├── hybrid_ranker.py      # Weighted scoring system
│   │   ├── ncf_recommender.py    # Hybrid recommendation
│   │   ├── sentiment_engine.py   # DistilBERT sentiment
│   │   ├── trending_score.py     # Real-time trending engine
│   │   ├── vector_store.py       # ChromaDB RAG store
│   │   ├── agent_tools.py        # LangChain tools
│   │   └── rag_chat.py           # LangGraph ReAct agent
│   ├── config.py             # Pydantic settings
│   ├── database.py           # Async SQLAlchemy setup
│   ├── schemas.py            # Pydantic schemas
│   └── main.py               # FastAPI app entry point
├── portal/
│   ├── app.py                # Streamlit entry point
│   └── components/
│       ├── home.py           # Dashboard + quick search
│       ├── search.py         # Game search + SHAP chart
│       ├── chat.py           # AI chat interface
│       ├── trending.py       # Trending games + charts
│       └── register.py       # User registration
├── scripts/
│   ├── run_enrichment.py     # Data pipeline CLI
│   └── find_steam_ids.py     # Steam ID fuzzy matcher
├── models/
│   ├── ncf_model.pt          # Trained NCF weights
│   └── encoders/             # user_encoder + game_encoder
├── chroma_db/                # Persisted vector store
├── docker-compose.yml        # All services
├── requirements.txt
└── start.bat                 # One-click launcher (Windows)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop
- 8GB RAM minimum (16GB recommended for Qwen2.5 7B)

### 1. Clone & Setup
```bash
git clone https://github.com/Opticinn/game-sense-ai
cd game-sense-ai
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` file:
```env
DATABASE_URL=postgresql+asyncpg://gamesense:gamesense@localhost:5438/gamesense
REDIS_URL=redis://localhost:6379
STEAM_API_KEY=your_steam_api_key
RAWG_API_KEY=your_rawg_api_key
YOUTUBE_API_KEY=your_youtube_api_key
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
```

### 3. Start Services
```bash
# Option A: One-click launcher (Windows)
start.bat

# Option B: Manual
docker-compose up -d
uvicorn app.main:app --reload        # Terminal 1
streamlit run portal/app.py          # Terminal 2
```

### 4. Pull LLM Model
```bash
docker exec -it gamesense_ollama ollama pull qwen2.5:7b
```

### 5. Access
| Service | URL |
|---|---|
| Streamlit Portal | http://localhost:8501 |
| FastAPI Docs | http://localhost:8000/docs |
| MLflow UI | http://localhost:5000 |

---

## 📊 Data Pipeline

Run the enrichment pipeline to populate/update game data:

```bash
# Add new games from RAWG
python scripts/run_enrichment.py --source rawg --pages 20

# Update existing game data from Steam
python scripts/run_enrichment.py --source steam

# Calculate trending scores (real-time)
python scripts/run_enrichment.py --source trending

# Run everything
python scripts/run_enrichment.py --source all
```

---

## 🔌 API Endpoints

### Games
```
GET    /games/              List all games (paginated)
GET    /games/search        Search games by title/genre
GET    /games/{id}          Get game detail
GET    /games/similar/{id}  Get similar games (NCF hybrid)
GET    /games/youtube/{id}  Get gameplay videos
POST   /games/              Create game
PUT    /games/{id}          Update game
DELETE /games/{id}          Delete game
```

### Trending
```
GET /trending/              Top trending games
GET /trending/mod           Top moddable games
```

### Chat
```
POST /chat/ask              Ask AI about any game
```

---

## 🤖 AI Chat Examples

```
"Recommend me a game like Elden Ring but easier"
"What are the best co-op games under $20?"
"Is Cyberpunk 2077 worth buying now?"
"Show me trending RPGs this month"
"What mods are popular for Skyrim?"
```

The ReAct agent automatically decides which tools to use:
- `search_game` — semantic search in vector store
- `get_game_price` — real-time Steam price
- `get_current_players` — live player count
- `get_gameplay_video` — YouTube embed
- `get_mod_games` — moddable game recommendations
- `get_mod_videos` — mod showcase videos

---

## ⚙️ Docker Services

```yaml
services:
  postgres:   port 5438   # Main database
  redis:      port 6379   # Cache layer
  ollama:     port 11434  # LLM inference
  mlflow:     port 5000   # Experiment tracking
```

---

## 📈 Model Performance

| Metric | Value |
|---|---|
| NCF Accuracy | 88% |
| Games in Database | 2,605 |
| Games with NCF Support | 257 |
| Vector Store Documents | 2,605 |
| Embedding Model | all-MiniLM-L6-v2 |
| LLM Response Time | ~1-3 min (CPU) |

> **Note:** LLM response is slow (~1-3 min) because inference runs on CPU. GPU deployment would reduce this to ~5-10 seconds.

---

## 🗺️ Roadmap

- [ ] GPU support for faster LLM inference
- [ ] Redis caching for API endpoints
- [ ] Multilingual sentiment (Indonesian reviews)
- [ ] Docker Compose full deployment (FastAPI + Streamlit as services)
- [ ] User authentication with JWT
- [ ] Personalized recommendations with login history

---

## 👨‍💻 Author

**Muhamad Rafli Fauzi**
- GitHub: [@Opticinn](https://github.com/Opticinn)
- Project: [game-sense-ai](https://github.com/Opticinn/game-sense-ai)

---

## 📄 License

This project is for educational and portfolio purposes.

---

<div align="center">
  <sub>Built with ❤️ using FastAPI, PyTorch, LangChain, and Streamlit</sub>
</div>
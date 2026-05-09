# OSINT-SENTINEL: AI-Native Investigation Platform

OSINT-SENTINEL is an autonomous investigation platform designed to track missing persons by analyzing social media signals. It utilizes a proactive intelligence pipeline powered by LangGraph, Gemini 1.5 Flash, and a multi-agent orchestration layer.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Docker & Docker Compose** (for PostgreSQL, Redis, and Qdrant)
- **Python 3.14+**
- **Node.js 18+**
- **API Keys**:
  - `GEMINI_API_KEY`: From Google AI Studio (for video analysis and embeddings).
  - `APIFY_TOKEN`: From Apify (for TikTok scraping).

### 2. Infrastructure Setup
Start the required databases and message brokers:
```bash
cd backend
docker-compose up -d
```
This launches:
- **PostgreSQL**: Stores cases, leads, and raw posts.
- **Redis**: Handles LangGraph persistence and proactive stream ingestion.
- **Qdrant**: Vector database for semantic claim clustering.

### 3. Backend Setup
```bash
cd backend
python -m venv env
.\env\Scripts\activate  # Windows
# source env/bin/activate # Linux/Mac

pip install -r requirements.txt
```

#### LLM Configuration (Gemma 4)
If your machine has limited resources (RAM/GPU), you can use a hosted API instead of local Ollama:

**Option A: Local (Ollama)**
```env
LLM_PROVIDER=ollama
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=gemma2
```

**Option B: Hosted (Groq) - Recommended for speed**
```env
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key
```

**Option C: Hosted (Google AI Studio)**
```env
LLM_PROVIDER=google
GEMINI_API_KEY=your_google_key
```

Create a `.env` file in the `backend/` directory with your chosen configuration:
```env
DATABASE_URL=postgresql+asyncpg://nexus:nexus@localhost:5432/nexus
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your_google_ai_studio_key
APIFY_TOKEN=your_apify_token
```

Start the API:
```bash
uvicorn api.main:app --reload --port 8000
```

### 4. Frontend Setup
```bash
cd ../osint-system
npm install
```

Create a `.env` file in the `osint-system/` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the development server:
```bash
npm run dev
```

---

## 🛠 Using the System

### 1. Create a New Case
Go to `http://localhost:5173/new-case`. Enter the subject's name, description, and last known location. Clicking "Launch Investigation" will:
- Create a case record in PostgreSQL.
- Trigger the LangGraph agent in the background.

### 2. Proactive Investigation Pipeline
The agent follows this autonomous flow:
1.  **Bootstrap**: Generates search keywords using a local LLM (Gemma 4).
2.  **TikTok Search**: Scrapes relevant posts via Apify.
3.  **Video Analysis**: Gemini 1.5 Flash analyzes videos for spoken claims and location signals.
4.  **Claim Extraction**: Extracts structured data (sightings, locations) from text and video.
5.  **Clustering**: Groups similar claims using Qdrant vector similarity.
6.  **Scoring**: Ranks clusters based on crowd signal, bot scores, and source diversity.
7.  **Lead Generation**: Surfaces actionable intelligence for investigators.

### 3. Human-in-the-Loop (HITL)
If the agent identifies an "urgent" lead, it may pause for human review (via the `human_review_interrupt` node). 
- View leads at `http://localhost:5173/case/{case_id}`.
- Resume a paused investigation by calling:
  `POST /api/cases/{case_id}/resume`

### 4. Autonomous Monitoring
The system includes a **Redis Stream Listener**. If external scrapers or community feeds push new data to `osint:normalized_posts`, the backend will automatically wake up the relevant investigation and process the new intel.

---

## 🏗 Architecture Details

- **Persistence**: LangGraph state is stored in PostgreSQL using `AsyncPostgresSaver`, allowing investigations to survive service restarts.
- **Performance**: 
  - **Batch Ingestion**: Posts and leads are written to DB in batches using `on_conflict_do_nothing`.
  - **Parallel Embeddings**: Multi-threaded embedding generation with a 20-request concurrency semaphore.
- **Intelligence**: Mix of Gemini 1.5 Flash (vision) and local Gemma 4 (text) for optimal cost/privacy.

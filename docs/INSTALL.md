# Installation & Setup Guide

This document provides a step-by-step guide to setting up the OSINT-SENTINEL environment for local development and testing.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
- **Docker & Docker Compose**: Required for running the database and message broker services.
- **Python 3.14+**: The backend is built with FastAPI.
- **Node.js 18+**: The frontend is built with React/Vite.
- **Git**: For version control.

---

## 🚀 Quick Start Sequence

Follow these steps in order to ensure all dependencies and services are properly linked.

### 1. Infrastructure (Databases & Brokers)
Start the core services using Docker:
```bash
cd backend
docker-compose up -d
```
**Services launched:**
- **PostgreSQL**: Stores persistent investigation data (Cases, Leads, Posts).
- **Redis**: Manages LangGraph state persistence and the proactive ingestion stream.
- **Qdrant**: Vector database for semantic claim clustering and similarity search.

### 2. Backend Setup
```bash
cd backend
python -m venv env
.\env\Scripts\activate  # Windows
# source env/bin/activate # Linux/Mac

pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd osint-system
npm install
```

---

## 🔑 Configuration (.env)

The system requires specific environment variables to function. Create `.env` files in both the `backend/` and `osint-system/` directories.

### Backend (`backend/.env`)
```env
# Database Connections
DATABASE_URL=postgresql+asyncpg://nexus:nexus@localhost:5432/nexus
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379

# AI Providers
LLM_PROVIDER=google  # options: google, ollama, groq
GEMINI_API_KEY=your_google_ai_studio_key
APIFY_TOKEN=your_apify_token

# Local LLM (Optional)
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=gemma2
```

### Frontend (`osint-system/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🏃 Running the Application

1. **Start the Backend:**
   ```bash
   cd backend
   uvicorn api.main:app --reload --port 8000
   ```

2. **Start the Frontend:**
   ```bash
   cd osint-system
   npm run dev
   ```

3. **Access the Dashboard:**
   Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🛠 Troubleshooting

- **Database Connection Refused:** Ensure Docker containers are running (`docker ps`).
- **Missing API Keys:** Verify that your `GEMINI_API_KEY` and `APIFY_TOKEN` are active and correctly pasted in `.env`.
- **Node Version Incompatibility:** Use `node -v` to ensure you are on version 18 or higher.

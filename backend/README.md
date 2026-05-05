# OSINT-NEXUS Backend - Technical Audit (May 5, 2026)

This document summarizes the results of a comprehensive technical audit and subsequent architectural refactor (May 2026).

## 1. Project Summary
OSINT-NEXUS is an investigation platform designed to track missing persons by analyzing social media signals, with a heavy current focus on TikTok ingestion and AI-driven video intelligence.

**Current Tech Stack:**
- **Framework:** FastAPI (Python 3.11)
- **Orchestration:** LangGraph (StateGraph-based agent)
- **AI Models:** Gemini 1.5 Flash (Video Analysis), Gemini (Extraction/Clustering)
- **Storage:** PostgreSQL (SQLAlchemy), Redis (Streams/Checkpoints), Qdrant (Vector DB)
- **External APIs:** Apify (TikTok Scraper), Google Vision, Tavily

**Status:** The system has been refactored to a **Proactive Ingestion Model** where data acquisition is the mandatory first step of any investigation. Core agent bugs have been resolved, and the pipeline flow is now strictly aligned with the intended user experience.

## 2. Recent Architectural Improvements (Branch: feature/proactive-ingestion)

### A. Proactive Pipeline
- **Mandatory Ingestion:** Removed conditional "Maybe-Search" logic. The agent now treats bootstrapping and initial TikTok/Web searches as the core entry point for every case.
- **Improved State Management:** Switched to a unified `CaseState` that prioritizes user-entered subject information (Name, Location) to drive scraping.

### B. Bug Fixes & Stability
- **Resolved Import Hell:** Fixed circular imports between `state.py` and `nodes.py`.
- **Naming Consistency:** Consolidated all tracing logic under `_make_trace` and aligned state field names (e.g., `video_analyses`).
- **Type Safety:** Integrated `VideoSignals` directly into the state schema to ensure Gemini results are correctly handled.

### C. Refactored Nodes
- **`bootstrap_node`**: New entry point that initializes the investigation based on user input.
- **`tiktok_search_node`**: Now strictly follows the bootstrap to ensure the pipeline always has fresh data.

## 3. Remaining Implementation Gaps (Next Sprint)

1. **Database Wiring:** The models are defined, but nodes do not yet write to the DB.
2. **Vector Pipeline:** The clustering node needs to generate embeddings and upsert to Qdrant.
3. **Real-time API:** Implement the FastAPI stream listener to trigger the graph automatically.
4. **LLM Intelligence:** Replace claim extraction stubs with real Gemini-based extraction logic.

## 4. Technical Debt (Minor)
- **Gemini Quota Tracking:** Need a persistent counter for daily API usage across all cases.
- **Config Tuning:** Move engagement thresholds from hardcoded constants to `.env` / `Settings`.

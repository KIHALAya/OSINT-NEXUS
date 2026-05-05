# OSINT-NEXUS Backend - Technical Audit (May 5, 2026)

This document summarizes the results of a comprehensive technical audit of the OSINT-NEXUS backend.

## 1. Project Summary
OSINT-NEXUS is an investigation platform designed to track missing persons by analyzing social media signals, with a heavy current focus on TikTok ingestion and AI-driven video intelligence.

**Current Tech Stack:**
- **Framework:** FastAPI (Python 3.11)
- **Orchestration:** LangGraph (StateGraph-based agent)
- **AI Models:** Gemini 1.5 Flash (Video Analysis), Gemini (Extraction/Clustering)
- **Storage:** PostgreSQL (SQLAlchemy), Redis (Streams/Checkpoints), Qdrant (Vector DB)
- **External APIs:** Apify (TikTok Scraper), Google Vision, Tavily

**Status:** High-quality "leaf" components (TikTok and Video analysis tools) exist, but core infrastructure (API, DB connectivity, Service layer) is largely missing or in stub form.

## 2. Critical Issues (Must Fix)

### A. Agent Logic Failures
- **Import Errors:** `graph.py` attempts to import from non-existent `agent.nodes_video`.
- **Naming Conflicts:** `nodes.py` calls `_make_trace` but defines `_trace`. State field mismatch: `video_analysis` (state) vs `video_analyses` (nodes).
- **Missing Imports:** `state.py` lacks the `VideoSignals` import.

### B. Empty Core Modules
- `api/main.py`, `db/database.py`, and `services/investigation.py` are currently empty (0 bytes), preventing application startup and data persistence.

### C. Fatal Deployment Configuration
- `Dockerfile` points to an empty `api.main:app`, causing immediate container crashes.

## 3. Medium Issues

### A. Stubbed Intelligence
- `claim_extractor_node` uses a hardcoded stub instead of real LLM extraction logic.
### B. Inefficient State Patterns
- `analyzed_post_ids` implemented as a list instead of a set, risking duplicate processing and increased API costs.
### C. Configuration Rigidity
- Hardcoded engagement and bot-score thresholds in `nodes.py` should be moved to environment variables.

## 4. Minor Issues / Code Smells

- **Gemini Quota Risk:** No global daily tracking for the 1,500/day free tier limit.
- **Redundant Logic:** Duplicate bot-score heuristic calculations across nodes.
- **Config Formatting:** Inconsistent indentation and redundant logic in `core/config.py`.

## 5. Missing Components

1. **Persistence Layer:** No logic to save results to PostgreSQL.
2. **Vector Search:** Qdrant integration for claim clustering is not implemented.
3. **Authentication:** No security layer on the API endpoints.
4. **Real-time Updates:** WebSocket infrastructure for live investigation updates is missing.

## 6. Recommended Next Steps

1. **Sanity Fix:** Correct imports, naming, and state mismatches in the agent package.
2. **Infrastructure:** Implement `db/database.py` and `api/main.py` entry points.
3. **Intelligence:** Replace stubs in `claim_extractor_node` with real LLM calls.
4. **Persistence:** Implement the `graph_updater_node` to sync LangGraph state with PostgreSQL.
5. **Vector Search:** Integrate Qdrant for automated claim clustering.

# OSINT-NEXUS: System Architecture & Technical Documentation

This document provides a comprehensive technical blueprint for the OSINT-NEXUS system. It reflects the **Hybrid-Intelligence Proactive Ingestion** model finalized in May 2026, optimized for US-based investigations.

---

## 1. System Philosophy: "Proactive, Private & Parallel"

OSINT-NEXUS is an automated intelligence platform designed to "hunt" for data once a missing person case is established. It transitions OSINT from a manual, reactive search to a proactive, agentic pipeline.

### Core Principles
- **Mandatory Ingestion:** Every investigation run begins with a fresh data acquisition phase (Scraping).
- **Hybrid Intelligence:** Leverages **Gemma 4 (Local)** for privacy-sensitive text processing and **Gemini 1.5 Flash (API)** for native multimodal video reasoning.
- **Privacy First:** Sensitive PII (names, specific sighting text) is processed on-premises via local LLM instances.
- **Parallel Execution:** High-latency AI calls are executed concurrently using `asyncio.gather` to minimize investigation turnaround time.
- **Sustainable Memory:** Implements a "Persist & Prune" pattern to prevent LangGraph state bloat while maintaining a permanent audit trail in PostgreSQL.

---

## 2. Technical Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | LangGraph (StateGraph) | Cyclic state machine & node-based pipeline control |
| **Local LLM** | Gemma 4 (via Ollama/vLLM) | Keyword generation, post triage, and PII-safe claim extraction |
| **Multimodal AI** | Gemini 1.5 Flash | Deep video analysis (frames + audio + transcript) |
| **Embeddings** | Google text-embedding-004 | 768-dim semantic representation for claim clustering |
| **Persistence** | PostgreSQL (SQLAlchemy) | Permanent longitudinal memory for all investigations |
| **Vector Store** | Qdrant | Real-time semantic search and cluster assignment |
| **Scraping** | Apify (TikTok Scraper) | Residential proxy scraping of cross-platform signals |
| **API** | FastAPI | Real-time REST endpoints and background task management |
| **Frontend** | React (Vite) | High-fidelity investigator dashboard with live state polling |

---

## 3. Detailed Investigation Nodes (`agent/nodes.py`)

The pipeline is organized into 10 specialized nodes, each with a discrete responsibility.

### Node 1: `bootstrap_node`
- **Role:** Generates investigation strategy.
- **Intelligence:** Uses **Gemma 4** to generate 5 context-aware US-based search keywords (e.g., city/state variations, Silver Alert hashtags).
- **Output:** `current_search_keywords`, `needs_tiktok_search = True`.

### Node 2: `tiktok_search_node`
- **Role:** Data acquisition.
- **Tool:** Calls `search_tiktok` (Apify).
- **Output:** `last_tiktok_result` containing up to 50 raw post objects.

### Node 3: `tiktok_ingestor_node`
- **Role:** Normalization.
- **Logic:** Converts raw Apify JSON into `IncomingPost` objects. Calculates a `bot_score` based on follower/engagement ratios.
- **Output:** `current_posts` (list).

### Node 4: `video_selector_node`
- **Role:** Intelligent Triage.
- **Intelligence:** Uses **Gemma 4** to analyze captions of all `current_posts`. It selects the top 5 videos most likely to contain real investigative signals (sightings, location mentions).
- **Output:** `video_analysis_queue`.

### Node 5: `video_analysis_node`
- **Role:** Multimodal Forensics.
- **Performance:** Executes **Gemini 1.5 Flash** calls in **parallel** for all queued videos.
- **Output:** `video_analyses_this_run` (PersonSignals, LocationSignals, SpokenClaims).

### Node 6: `claim_extractor_node`
- **Role:** Intelligence Distillation.
- **Intelligence:** Uses **Gemma 4** (Local) for private extraction of sighting claims from text posts and video results. Executes in **parallel**.
- **Vectorization:** Generates embeddings for every claim via `text-embedding-004`.
- **Output:** `current_claims`.

### Node 7: `clustering_node`
- **Role:** Semantic Grouping.
- **Tool:** Uses **Qdrant** Cosine Similarity (threshold > 0.78).
- **Logic:** Automatically groups new claims into existing "Claim Clusters" or spawns new clusters for novel signals.

### Node 8: `scoring_node`
- **Role:** Credibility Assessment.
- **Logic:** Computes a `crowd_score` (0.0 - 1.0) using frequency, platform diversity, average bot penalty, and recency bonus.
- **Output:** Updated `all_clusters` with scores.

### Node 9: `lead_generator_node`
- **Role:** Actionable Output.
- **Logic:** Converts clusters with `final_score > 0.5` into `Lead` objects. Suggests US-specific actions (e.g., "Contact Transit Police").
- **Output:** `current_leads`.

### Node 10: `graph_updater_node`
- **Role:** Persistence & Pruning.
- **Logic:** Writes all "current" data to PostgreSQL. **Prunes** transient lists from `CaseState` to prevent bloat.

---

## 4. State Schemas (`agent/state.py`)

### `CaseState` (The Graph State)
```python
class CaseState(TypedDict):
    # Core Metadata
    case_id: str
    subject_name: str
    subject_description: str
    
    # Persistent Memory (operator.add)
    all_posts: list[IncomingPost]
    all_claims: list[ExtractedClaim]
    all_clusters: list[ClusterState]
    all_leads: list[LeadState]
    agent_trace: list[AgentStep]
    
    # Transient Memory (Reset per run)
    current_posts: list[IncomingPost]
    current_claims: list[ExtractedClaim]
    current_leads: list[LeadState]
    video_analysis_queue: list[dict]
```

---

## 5. Persistence Schema (PostgreSQL)

- **`cases`:** Root investigation metadata.
- **`raw_posts`:** Permanent archive of every social media signal ingested. Includes `bot_score` and `engagement_score`.
- **`extracted_claims`:** Atomic units of evidence. Linked to posts and clusters. Stores the `qdrant_point_id`.
- **`leads`:** The final "Product." Categorized by priority (`urgent`, `high`, `medium`) and linked to supporting evidence chains.

---

## 6. Local LLM Integration (Gemma 4)

The system communicates with a local LLM via `backend/tools/local_llm.py`. 
- **Endpoint:** `http://localhost:11434/v1` (Default Ollama).
- **Format:** Enforces JSON output via `response_format={"type": "json_object"}`.
- **Usage:** Replaces Gemini for all text-only tasks to ensure data residency and cost-efficiency.

---

## 7. Performance & Latency

By parallelizing Gemini and Gemma calls, a typical investigation run (50 posts, 5 videos) completes in **< 60 seconds**, compared to 5+ minutes in the sequential prototype. 

- **Video Processing:** Concurrent upload and inference.
- **Claim Extraction:** Concurrent batch text analysis.
- **Database:** Atomic single-transaction writes at run termination.

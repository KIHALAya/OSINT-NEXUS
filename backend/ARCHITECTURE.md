# OSINT-NEXUS: System Architecture & Developer Guide

This document provides a technical blueprint for the OSINT-NEXUS backend. It reflects the **Proactive Ingestion** model implemented in May 2026.

---

## 1. System Philosophy: "Proactive Investigation"
Unlike reactive systems that wait for triggers, OSINT-NEXUS is designed to **hunt for data** once a case is established.
- **Mandatory Ingestion:** Every investigation run begins with a data acquisition phase (Scraping).
- **State Persistence:** The `CaseState` (TypedDict) acts as a longitudinal record, accumulating claims and video analyses across multiple runs.
- **Traceable Reasoning:** Every decision made by a node is recorded in an `agent_trace`, allowing investigators to audit the AI's logic.

---

## 2. Technical Stack
| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | LangGraph | State machine & proactive pipeline flow |
| **Inference** | Gemini 1.5 Flash | Multimodal video analysis (Audio/Visual/OCR) |
| **Search/Ingest**| Apify (TikTok) | Residential proxy scraping of viral content |
| **Relational DB** | PostgreSQL | Source of truth for cases, leads, and historical posts |
| **Vector DB** | Qdrant | Semantic claim clustering (Similarity Search) |

---

## 3. The Proactive Flow (The "Happy Path")

### Step 1: Bootstrap (`bootstrap_node`)
The run starts here. The system captures the current subject name and location. It sets the `needs_tiktok_search` flag to `True` by default to ensure the pipeline is primed with fresh data.

### Step 2: Mandatory Ingestion (`tiktok_search` -> `tiktok_ingestor`)
The agent calls the TikTok Scraper via Apify. It uses the subject's name and known locations to build search keywords. The `ingestor` node then normalizes these results into a platform-agnostic `IncomingPost` format.

### Step 3: High-Signal Filtering (`video_selector`)
The system analyzes the engagement (plays/shares) and account credibility (bot score) of all ingested posts. It selects the top candidates for expensive multimodal analysis.

### Step 4: Multimodal Extraction (`video_analysis`)
Selected videos are sent to Gemini 1.5 Flash. The model analyzes frames, audio, and text simultaneously to extract sightings, clothing descriptions, and spoken claims.

### Step 5: Claim Synthesis (`claim_extractor`)
The system aggregates claims from both text (captions) and video analysis. This unified pool of `ExtractedClaim` objects is what drives the clustering and lead generation in later stages.

---

## 4. Key Directory Structure
```
backend/
├── agent/             # Logic & Orchestration
│   ├── graph.py       # Pipeline definition (The "Brain")
│   ├── nodes.py       # Node implementations (The "Agents")
│   └── state.py       # State schema (The "Memory")
├── tools/             # External Integrations (Decoupled)
│   ├── tiktok_search.py
│   └── video_analysis.py
└── db/                # Persistence
    └── models.py      # SQLAlchemy ORM
```

---

## 5. Architectural Standards (Team Rules)

### A. The "operator.add" Rule
Never overwrite lists in the state. Always use `Annotated[list, operator.add]`. This ensures that if the agent finds 3 claims in Run 1 and 2 claims in Run 2, the investigator sees all 5.

### B. Traceability
Every node **must** return an `agent_trace` via the `_make_trace` helper. 
```python
trace = _make_trace(agent="name", input_summary="...", decision="...", reasoning="...")
```

### C. Sequential Gemini Calls
To stay within free-tier rate limits (1,500/day) and avoid concurrency issues with the Gemini Files API, always analyze videos **sequentially** within the `video_analysis_node`.

### D. Platform Agnosticism
Nodes after `tiktok_ingestor` should not care about the source of the post. Always work with the `IncomingPost` and `ExtractedClaim` types.

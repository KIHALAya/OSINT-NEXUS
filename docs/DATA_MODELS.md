# Data Models & Persistence

This document describes the single source of truth for all data within the OSINT-SENTINEL ecosystem, covering relational, vector, and graph state schemas.

---

## 🗄 Relational Schema (PostgreSQL)

Located in `backend/db/models.py`. The database stores persistent, longitudinal data for investigations.

### 1. `cases`
The root record for any investigation.
- `id`: Unique identifier (e.g., `CASE-2026-XXXX`).
- `subject_name`: Name of the missing person.
- `subject_description`: Physical traits, last seen location, and context.
- `status`: `active`, `monitoring`, or `closed`.

### 2. `raw_posts`
A permanent archive of every social media signal ingested.
- `source`: Platform (tiktok, twitter, reddit).
- `normalized_text`: Cleaned caption/content.
- `bot_score`: Probability the account is automated.
- `engagement_score`: Derived from likes/shares/plays.

### 3. `extracted_claims`
Atomic units of evidence extracted from posts or videos.
- `text`: The raw claim (e.g., "Seen at a gas station in Austin").
- `qdrant_point_id`: Links to the embedding vector in Qdrant.
- `cluster_id`: Links multiple claims to a single event cluster.

### 4. `leads`
Validated intelligence surfaced to the dashboard.
- `priority`: `urgent`, `high`, `medium`.
- `evidence_summary`: Synthesized evidence chain.

---

## 🔢 Vector Schema (Qdrant)

The system uses a Qdrant collection for semantic similarity.
- **Vector Dimension:** 768 (using `text-embedding-004`).
- **Metric:** Cosine Similarity.
- **Payload:** Includes `claim_id`, `case_id`, and `source_post_id` for cross-referencing.

---

## 🧠 Graph State (`CaseState`)

The LangGraph state manages memory *during* a run. Defined in `backend/agent/state.py`.

### Persistent Memory (Merged via `operator.add`)
- `all_posts`: Growing list of ingested signals.
- `all_claims`: Every extracted claim across all runs.
- `all_clusters`: The current state of evidence grouping.
- `agent_trace`: Audit trail of node decisions and reasoning.

### Transient Memory (Reset per run)
- `current_posts`: Posts ingested in the *current* cycle.
- `video_analysis_queue`: Videos pending Gemini analysis.
- `current_leads`: Leads generated in the *current* cycle.

---

*For SQL implementation, see `backend/db/models.py`.*

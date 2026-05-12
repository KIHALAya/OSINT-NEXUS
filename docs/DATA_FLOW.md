# Data Flow & Debugging Lifecycle

This document provides a step-by-step trace of data as it flows through the OSINT-SENTINEL system. Use this as a reference to identify where data might be dropping, failing to transform, or losing metadata.

---

## 🚉 Station 0: Ingestion & Triggering

Data enters the system through two primary entry points:

### A. Manual Case Creation (REST)
- **Format:** `POST /api/cases`
- **Payload:** `{"subject_name": "...", "subject_description": "...", "location": "..."}`
- **Action:** Creates a record in Postgres `cases` table and initializes a `CaseState` in Redis.

### B. Proactive Stream (Redis)
- **Format:** Redis Stream `normalized.posts.v1`
- **Payload:** Raw JSON from external scrapers.
- **Action:** The `_stream_listener` in `api/main.py` matches the post to an existing `case_id` and triggers the Graph.

---

## 🚉 Station 1: `bootstrap_node`
- **Input:** `CaseState` (Metadata only).
- **Transformation:** Deterministic normalization of the subject name.
- **Output (State Change):** 
    - `current_search_queries`: `list[str]` (e.g., `["John Doe"]`)
    - `current_hashtags`: `list[str]` (e.g., `["johndoe"]`)
    - `needs_tiktok_search`: `True`

---

## 🚉 Station 2: `tiktok_search_node`
- **Input:** `current_search_keywords`.
- **Transformation:** Calls Apify TikTok Scraper.
- **Output (Transient):** `last_tiktok_result`: Raw JSON list from Apify (includes `desc`, `video_url`, `author_meta`).

---

## 🚉 Station 3: `tiktok_ingestor_node` (The Normalizer)
- **Input:** `last_tiktok_result`.
- **Transformation:** Maps raw JSON to the `IncomingPost` model.
- **Format (`IncomingPost`):**
    ```json
    {
      "id": "ev_123...",
      "source": "tiktok",
      "post_id": "736...",
      "normalized_text": "caption content",
      "bot_score": 0.15,
      "video_url": "https://...",
      "author_followers": 5000
    }
    ```
- **Output (State Change):** `current_posts` (list of objects above).

---

## 🚉 Station 4: `video_selector_node` (The Triage)
- **Input:** `current_posts`.
- **Transformation:** LLM scans captions. It filters for posts that mention "saw him", "location", or physical descriptions.
- **Output (State Change):** `video_analysis_queue`: `list[dict]` containing URLs and context for the top 5 videos.

---

## 🚉 Station 5: `video_analysis_node` (Multimodal Analysis)
- **Input:** `video_analysis_queue`.
- **Transformation:** **Gemini 1.5 Flash** analyzes the video bytes + audio.
- **Output (Transient):** `video_analyses_this_run`:
    ```json
    {
      "spoken_claims": ["He was wearing a red hat"],
      "visual_signals": {"clothing": "red hat", "landmarks": "Shell gas station"},
      "confidence": 0.92
    }
    ```

---

## 🚉 Station 6: `claim_extractor_node` (Structured Evidence)
- **Input:** `current_posts` + `video_analyses_this_run`.
- **Transformation:** LLM extracts atomic facts. Generates a **768-dim embedding** for each.
- **Format (`ExtractedClaim`):**
    ```json
    {
      "claim_id": "clm_abc...",
      "text": "Subject spotted at Shell station in Austin",
      "embedding": [0.12, -0.04, ...],
      "source_post_id": "ev_123"
    }
    ```
- **Output (State Change):** `current_claims`.

---

## 🚉 Station 7: `clustering_node` (Semantic Linkage)
- **Input:** `current_claims`.
- **Transformation:** Vector search in **Qdrant**.
- **Logic:**
    - If `cosine_similarity > 0.78` → Assign to existing `cluster_id`.
    - Else → Create new `cluster_id`.
- **Output (State Change):** `all_clusters` updated with new claim links.

---

## 🚉 Station 8: `scoring_node` (Credibility)
- **Input:** `all_clusters`.
- **Transformation:** Calculation of `crowd_score`.
- **Variables:**
    - `frequency`: How many people said this?
    - `diversity`: Are they from different platforms/accounts?
    - `bot_penalty`: Are these accounts likely bots?
- **Output (State Change):** Updates `final_score` on each cluster.

---

## 🚉 Station 9: `lead_generator_node` (Output)
- **Input:** Clusters where `final_score > 0.5`.
- **Transformation:** Synthesizes a human-readable lead.
- **Output (State Change):** `current_leads`:
    ```json
    {
      "lead_id": "lead_xyz",
      "priority": "high",
      "summary": "Multiple sightings confirmed at Austin Shell station.",
      "supporting_cluster_id": "clust_123"
    }
    ```

---

## 🚉 Station 10: `graph_updater_node` (Persistence)
- **Input:** All `current_*` lists.
- **Action:**
    1.  Writes `current_posts` to Postgres `raw_posts`.
    2.  Writes `current_claims` to Postgres `extracted_claims`.
    3.  Writes `current_leads` to Postgres `leads`.
    4.  Upserts embeddings to **Qdrant**.
- **Cleanup:** Clears `current_posts`, `current_claims`, and `video_analysis_queue` from the state to prevent bloat.

---

## 🐛 Debugging Quick-Ref

| Symptom | Check Station(s) | Likely Cause |
| :--- | :--- | :--- |
| **No posts found** | 1, 2 | Keywords too narrow or Apify credits empty. |
| **Videos not analyzed** | 4 | Triage logic in `video_selector` is too strict. |
| **Duplicate leads** | 7 | Clustering threshold (0.78) is too high. |
| **Low quality leads** | 8 | Bot detection or diversity penalty is too weak. |
| **Data not in Postgres** | 10 | Transaction failure or database connection drop. |

# Agent Pipeline & Intelligence

This document provides a deep dive into the autonomous logic and intelligence nodes that power the OSINT-SENTINEL investigation engine.

---

## 🧠 Intelligence Orchestration

The agent is built using **LangGraph**, implemented in `backend/agent/nodes.py`. It utilizes a hybrid model to balance speed, cost, and multimodal capabilities.

### Hybrid Model Strategy
- **Gemma 4 (Local/Groq):** Used for text-heavy tasks like keyword generation, post triage, and PII-safe claim extraction.
- **Gemini 1.5 Flash (Cloud):** Used specifically for multimodal video reasoning (audio transcripts, frame analysis, spoken claims).

---

## ⚙️ Node Breakdown

### 1. `bootstrap_node`
- **Goal:** Strategy generation.
- **Logic:** Generates deterministic search signals:
    - **Exact Name:** The subject's full name.
    - **Normalized Hashtag:** Subject's name lowercased, spaces and punctuation removed (e.g., "Gabby Petito" → `gabbypetito`).
- **Why:** Deterministic hashtags return far higher quality investigative results on platforms like TikTok than AI-generated phrases. LLM expansion is deferred to the streaming intelligence layer.

### 2. `tiktok_search_node`
- **Goal:** Data acquisition.
- **Logic:** Interfaces with the Apify TikTok Scraper tool to fetch recent posts matching the bootstrap keywords.

### 3. `tiktok_ingestor_node`
- **Goal:** Signal normalization.
- **Logic:** Converts raw platform data into a unified `IncomingPost` schema. Calculates an initial `bot_score` based on metadata (follower count, engagement ratios).

### 4. `video_selector_node`
- **Goal:** Intelligent triage.
- **Logic:** Uses an LLM to scan captions/metadata of all ingested posts to select the top-N videos that likely contain real investigative signals.

### 5. `video_analysis_node`
- **Goal:** Multimodal forensics.
- **Logic:** Executes Gemini 1.5 Flash calls in parallel. Extracts:
    - **PersonSignals:** Clothing, physical features mentioned or seen.
    - **LocationSignals:** Background landmarks, street signs, accent cues.
    - **SpokenClaims:** Direct quotes regarding sightings or intent.

### 6. `claim_extractor_node`
- **Goal:** Intelligence distillation.
- **Logic:** Combines text from posts and results from video analysis into atomic "Claims." Each claim is assigned a vector embedding.

### 7. `clustering_node`
- **Goal:** Semantic grouping.
- **Logic:** Uses Qdrant cosine similarity (threshold ~0.78) to find existing clusters or create new ones. This deduplicates identical sightings across different accounts.

### 8. `scoring_node`
- **Goal:** Credibility assessment.
- **Formula:** `crowd_score` = (Source Diversity × Frequency) - Bot Penalty + Recency Bonus.

### 9. `lead_generator_node`
- **Goal:** Actionable output.
- **Logic:** Clusters that exceed a confidence threshold are promoted to "Leads," including a synthesized summary and link to supporting evidence chains.

---

## 🛠 Tools & Utilities

The agent leverages specialized tools located in `backend/tools/`:
- `tiktok_search.py`: Wrapper for the Apify API.
- `video_analysis.py`: Gemini multimodal integration.
- `embeddings.py`: Vector generation and Qdrant interaction.
- `local_llm.py`: Interface for Ollama/Groq.

---

*For implementation details, refer to `backend/agent/nodes.py`.*

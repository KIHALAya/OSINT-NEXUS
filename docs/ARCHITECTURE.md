# System Architecture

This document outlines the high-level design and service orchestration of the OSINT-SENTINEL platform.

---

## 🏛 Core Philosophy: "Proactive & Parallel"

OSINT-SENTINEL transitions traditional OSINT from a manual, reactive search to an autonomous, agentic pipeline. It is designed to "hunt" for data rather than simply waiting for queries.

### Principles
- **Mandatory Ingestion:** Every investigation run begins with fresh data acquisition.
- **Hybrid Intelligence:** Orchestrates between local LLMs (privacy/cost) and high-power multimodal APIs (vision).
- **Semantic Persistence:** Uses vector embeddings to group disparate signals into cohesive "evidence clusters."

---

## 🗺 Service Map

The system is composed of four primary layers:

1.  **Frontend (React/Vite):** A high-fidelity dashboard for investigators to track real-time agent progress and review leads.
2.  **API Layer (FastAPI):** Orchestrates requests, manages background tasks, and provides a RESTful interface to the database.
3.  **Intelligence Layer (LangGraph):** A cyclic state machine that controls the investigation flow through discrete specialized nodes.
4.  **Data Layer:**
    *   **PostgreSQL:** Relational storage for structured data (Cases, Leads, Audit Trails).
    *   **Redis:** Persistence for LangGraph checkpoints and stream management.
    *   **Qdrant:** Vector store for semantic search and claim clustering.

---

## 🔄 The Data Lifecycle

The journey from a raw signal to an actionable lead follows this path:

1.  **Ingestion:** Scrapers (Apify) pull raw data from platforms like TikTok.
2.  **Normalization:** Raw JSON is converted into structured `IncomingPost` objects.
3.  **Multimodal Analysis:** Videos are analyzed by Gemini 1.5 Flash for audio/visual signals.
4.  **Claim Extraction:** Atomic claims (sightings, locations) are extracted and embedded.
5.  **Clustering:** Claims are grouped by semantic similarity in Qdrant.
6.  **Scoring:** Clusters are ranked based on frequency, source diversity, and bot-detection penalties.
7.  **Lead Generation:** High-confidence clusters are surfaced as actionable leads.

---

## 🧩 Orchestration Flow

The system uses **LangGraph** to manage the complexity of the 11-step pipeline. This allows for:
- **Resilience:** Investigations can be paused and resumed via Redis checkpoints.
- **Human-in-the-Loop:** Nodes can interrupt the flow to request human verification for "Urgent" signals.
- **Parallelism:** Independent nodes (like video analysis and claim extraction) can execute concurrently.

---

*For detailed node logic, see [AGENT_PIPELINE.md](./AGENT_PIPELINE.md).*
*For data schemas, see [DATA_MODELS.md](./DATA_MODELS.md).*

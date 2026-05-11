# Frontend Guide

The OSINT-SENTINEL frontend is a high-fidelity investigator dashboard built with React, Vite, and Vanilla CSS.

---

## 🎨 UI Overview

The application is designed for clarity and speed, focusing on surfacing actionable intelligence (Leads) over raw data.

### Primary Views
- **Dashboard (`/`):** A high-level view of all active cases, their priority, and recent lead counts.
- **Case View (`/case/{id}`):** The main workspace, featuring 5 specialized tabs:
    1. **Intelligence Map:** A spatial/graph view of claims.
    2. **Leads:** Validated evidence chains.
    3. **Claim Clusters:** Grouped raw signals.
    4. **Community Feed:** Raw post ingestion monitoring.
    5. **Agent Chat:** Direct Q&A with the case-aware agent.
- **New Case (`/new-case`):** A guided wizard for launching new investigations.

---

## 🧩 Component Architecture

Located in `osint-system/src/components/`.

- **`KnowledgeGraph.jsx`:** Renders an SVG-based graph of how claims link to evidence.
- **`ClaimClusters.jsx`:** Displays semantic groups with their respective crowd/bot scores.
- **`AgentChat.jsx`:** A real-time chat interface that queries the LangGraph state.
- **`Leads.jsx`:** Priority-sorted cards for actionable intelligence.

---

## 🔄 State Management & Synchronization

- **Live Polling:** The frontend polls the `/api/cases/{id}/status` endpoint during active agent runs to update progress bars and live logs.
- **Mock Data:** Located in `src/data/mockData.js` for rapid UI prototyping without a running backend.

---

## 🛠 Development

```bash
cd osint-system
npm install
npm run dev
```

---

*For styling patterns, see `osint-system/src/styles/globals.css`.*

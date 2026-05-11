# OSINT-SENTINEL: AI-Native Investigation Platform

OSINT-SENTINEL is an autonomous intelligence platform designed to track missing persons by analyzing social media signals. It utilizes a proactive pipeline powered by LangGraph, Gemini 1.5 Flash, and semantic claim clustering.

---

## 📖 Documentation Map

To keep information organized and reduce redundancy, our documentation is split into specialized modules:

| Document | Description |
| :--- | :--- |
| **[🚀 Installation](./docs/INSTALL.md)** | Step-by-step setup guide for local development. |
| **[🏛 Architecture](./docs/ARCHITECTURE.md)** | High-level system design and service orchestration. |
| **[🧠 Agent Pipeline](./docs/AGENT_PIPELINE.md)** | Deep dive into LangGraph nodes and AI logic. |
| **[🗄 Data Models](./docs/DATA_MODELS.md)** | Schemas for PostgreSQL, Qdrant, and Graph State. |
| **[📡 API Reference](./docs/API_REFERENCE.md)** | REST endpoints and background stream listeners. |
| **[🎨 Frontend Guide](./docs/FRONTEND_GUIDE.md)** | React component map and UI/UX blueprint. |
| **[🤝 Contributing](./docs/CONTRIBUTING.md)** | Workflow rules, quality standards, and testing. |

---

## 🚀 Quick Start

1. **Infrastructure:** `cd backend && docker-compose up -d`
2. **Backend:** `cd backend && pip install -r requirements.txt && uvicorn api.main:app`
3. **Frontend:** `cd osint-system && npm install && npm run dev`

---

## 🛡 Disclaimer
This tool is for investigative research. Ensure compliance with platform Terms of Service and local privacy laws when deploying scrapers.

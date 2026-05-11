# OSINT-SENTINEL Backend

This directory contains the FastAPI backend, LangGraph agent, and database integration for the OSINT-SENTINEL platform.

---

## 📖 Documentation
To avoid redundancy, technical documentation has been moved to the root `docs/` directory:

- **[Installation Guide](../docs/INSTALL.md)**
- **[System Architecture](../docs/ARCHITECTURE.md)**
- **[Agent Pipeline Details](../docs/AGENT_PIPELINE.md)**
- **[Data Models](../docs/DATA_MODELS.md)**
- **[API Reference](../docs/API_REFERENCE.md)**

---

## 🚀 Quick Start
```bash
python -m venv env
.\env\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

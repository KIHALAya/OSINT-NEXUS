# API Reference

The OSINT-SENTINEL API is built with FastAPI and serves as the bridge between the frontend, the database, and the autonomous agent.

---

## 📡 REST Endpoints

### Cases
- `GET /api/cases`: List all active investigations.
- `POST /api/cases`: Create a new case.
- `GET /api/cases/{case_id}`: Fetch full metadata, leads, and claims for a specific case.
- `DELETE /api/cases/{case_id}`: Archive or delete a case.

### Investigation Control
- `POST /api/cases/{case_id}/trigger`: Manually start an agent run for a case.
- `POST /api/cases/{case_id}/resume`: Resume an investigation paused for human review.
- `GET /api/cases/{case_id}/status`: Get the real-time status of the LangGraph agent.

### Intelligence
- `GET /api/cases/{case_id}/leads`: Fetch only the validated leads.
- `GET /api/cases/{case_id}/clusters`: Fetch semantic claim clusters.

---

## 🔄 Redis Stream Integration

The backend includes a background listener that monitors Redis Streams for proactive data.

- **Stream Name:** `normalized.posts.v1`
- **Function:** When external scrapers or community feeds push data to this stream, the listener automatically identifies the relevant `case_id` and triggers the LangGraph agent to process the new data.

---

## 🛠 Setup & Development

The API is served by Uvicorn.
```bash
uvicorn api.main:app --reload --port 8000
```
- **Auto-Docs:** Swagger UI is available at `/docs`.
- **ReRedoc:** Alternative documentation available at `/redoc`.

---

*Implementation can be found in `backend/api/main.py` and `backend/api/routes/`.*

"""
api/main.py

FastAPI application — the real-time API entry point.

Three responsibilities:
  1. Startup: create DB tables, start Redis stream listener background task
  2. Stream listener: consume normalized.posts.v1 → trigger LangGraph runs
  3. REST endpoints: create cases, query leads/claims, get run status
"""

import asyncio
import datetime
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import build_graph, get_graph, setup_checkpointer

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from agent.state import CaseState
from core.config import get_settings
from db.database import create_tables, get_db
from db.models import Case, ExtractedClaimModel, Lead, RawPost

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    # Create tables
    await create_tables()
    logger.info("Database tables ready")

    # Setup LangGraph checkpointer
    await setup_checkpointer()

    # Start Redis stream listener in background
    listener_task = asyncio.create_task(_stream_listener())
    logger.info("Redis stream listener started")

    yield

    # Shutdown
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
    logger.info("API stopped")


app = FastAPI(
    title="OSINT-NEXUS API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Redis stream listener ─────────────────────────────────────────────────────

async def _stream_listener():
    """Background task: consumes normalized.posts.v1 from Redis Streams."""
    redis_client = await aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    stream = settings.stream_normalized_posts
    group = "intelligence-group"
    consumer = f"api-{uuid.uuid4().hex[:6]}"

    try:
        await redis_client.xgroup_create(stream, group, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    logger.info(f"Stream listener ready: stream={stream} group={group} consumer={consumer}")
    graph = await get_graph()

    while True:
        try:
            results = await redis_client.xreadgroup(groupname=group, consumername=consumer, streams={stream: ">"}, count=5, block=2000)
            if not results: continue

            for _, entries in results:
                for entry_id, raw_fields in entries:
                    try:
                        post = _deserialize(raw_fields)
                        case_id = post.get("case_id")
                        if not case_id:
                            await redis_client.xack(stream, group, entry_id)
                            continue

                        asyncio.create_task(_trigger_graph_run(graph, case_id, post))
                        await redis_client.xack(stream, group, entry_id)
                    except Exception as e:
                        logger.error(f"Failed to process stream entry {entry_id}: {e}")
        except asyncio.CancelledError: break
        except Exception as e:
            logger.error(f"Stream listener error: {e}", exc_info=True)
            await asyncio.sleep(2)
    await redis_client.aclose()


async def _trigger_graph_run(graph, case_id: str, post: dict):
    config = {"configurable": {"thread_id": case_id}}
    try:
        logger.info(f"Triggering graph run: case={case_id}")
        await graph.ainvoke({"incoming_post": post}, config=config)
    except Exception as e:
        logger.error(f"Graph run failed case={case_id}: {e}", exc_info=True)


def _deserialize(raw_fields: dict[str, str]) -> dict[str, Any]:
    result = {}
    for k, v in raw_fields.items():
        try: result[k] = json.loads(v)
        except: result[k] = v
    return result


# ── Request / response models ─────────────────────────────────────────────────

class CreateCaseRequest(BaseModel):
    subject_name: str
    subject_description: str
    age: int | None = None
    location: str | None = None
    last_seen_date: str | None = None
    priority: str = "high"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/cases")
async def list_cases(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Case).order_by(Case.created_at.desc()))
    cases = result.scalars().all()
    return [{
        "id": c.id, "subject": c.subject_name, "age": c.age, "lastSeen": c.last_seen_date,
        "location": c.location, "status": c.status, "priority": c.priority,
        "created_at": c.created_at.isoformat()
    } for c in cases]


@app.post("/api/cases", status_code=201)
async def create_case(req: CreateCaseRequest, db: AsyncSession = Depends(get_db)) -> dict:
    case_id = f"CASE-{datetime.datetime.utcnow().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"
    case = Case(
        id=case_id, subject_name=req.subject_name, subject_description=req.subject_description,
        age=req.age, location=req.location, last_seen_date=req.last_seen_date,
        priority=req.priority, status="active"
    )
    db.add(case)
    await db.commit()
    return {"case_id": case_id, "status": "created"}


@app.delete("/api/cases/{case_id}")
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    case = await db.get(Case, case_id)
    if not case: raise HTTPException(status_code=404, detail="Not found")
    await db.execute(delete(Lead).where(Lead.case_id == case_id))
    await db.execute(delete(ExtractedClaimModel).where(ExtractedClaimModel.case_id == case_id))
    await db.execute(delete(RawPost).where(RawPost.case_id == case_id))
    await db.delete(case)
    await db.commit()
    return {"status": "deleted"}


@app.patch("/api/cases/{case_id}/status")
async def update_case_status(case_id: str, status: str, db: AsyncSession = Depends(get_db)) -> dict:
    case = await db.get(Case, case_id)
    if not case: raise HTTPException(status_code=404, detail="Not found")
    case.status = status
    await db.commit()
    return {"status": "updated", "new_status": status}


@app.post("/api/cases/{case_id}/upload")
async def upload_files(case_id: str, files: list[UploadFile] = File(...)):
    case_path = os.path.join(UPLOAD_DIR, case_id)
    os.makedirs(case_path, exist_ok=True)
    saved = []
    for file in files:
        path = os.path.join(case_path, file.filename)
        with open(path, "wb") as f: f.write(await file.read())
        saved.append(file.filename)
    return {"case_id": case_id, "files": saved}


@app.post("/api/cases/{case_id}/run")
async def run_investigation(case_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    case = await db.get(Case, case_id)
    if not case: raise HTTPException(status_code=404, detail="Not found")
    graph = await get_graph()
    initial_state = {
        "case_id": case_id, "run_id": str(uuid.uuid4()), "subject_name": case.subject_name, "subject_description": case.subject_description or "",
        "all_posts": [], "all_claims": [], "all_clusters": [], "all_leads": [], "agent_trace": [],
        "analyzed_post_ids": [], "current_search_keywords": [], "last_tiktok_result": None,
        "current_posts": [], "current_claims": [], "current_clusters": [],
        "current_leads": [], "video_analysis_queue": [], "video_analyses_this_run": [],
        "needs_tiktok_search": True, "needs_video_analysis": False, "needs_verification": [], "needs_human_review": False,
        "tiktok_normalized_posts_this_run": [], "extracted_claims_this_run": [],
        "scores_this_run": {}, "misinfo_flags_this_run": [], "tiktok_viral_flags": [],
    }
    background_tasks.add_task(_run_graph_blocking, graph, initial_state, case_id)
    return {"status": "running"}


@app.post("/api/cases/{case_id}/resume")
async def resume_investigation(case_id: str, background_tasks: BackgroundTasks):
    graph = await get_graph()
    config = {"configurable": {"thread_id": case_id}}
    snapshot = await graph.aget_state(config)
    if not snapshot.next: raise HTTPException(status_code=400, detail="Not paused")
    background_tasks.add_task(_resume_graph_blocking, graph, case_id)
    return {"status": "resuming"}


async def _run_graph_blocking(graph, initial_state: dict, case_id: str):
    try: await graph.ainvoke(initial_state, config={"configurable": {"thread_id": case_id}})
    except Exception as e: logger.error(f"Fail case={case_id}: {e}", exc_info=True)


async def _resume_graph_blocking(graph, case_id: str):
    try: await graph.ainvoke(None, config={"configurable": {"thread_id": case_id}})
    except Exception as e: logger.error(f"Fail case={case_id}: {e}", exc_info=True)


@app.get("/api/cases/{case_id}/leads")
async def get_leads(case_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lead).where(Lead.case_id == case_id).order_by(Lead.final_score.desc()))
    leads = res.scalars().all()
    return [{"lead_id": l.id, "title": l.title, "confidence": l.confidence, "priority": l.priority, "evidence": l.evidence, "status": l.status} for l in leads]


@app.get("/api/cases/{case_id}/claims")
async def get_claims(case_id: str, claim_type: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ExtractedClaimModel).where(ExtractedClaimModel.case_id == case_id)
    if claim_type: q = q.where(ExtractedClaimModel.claim_type == claim_type)
    res = await db.execute(q.order_by(ExtractedClaimModel.extraction_confidence.desc()))
    return [{"claim_id": c.id, "claim_type": c.claim_type, "statement": c.statement, "confidence": c.extraction_confidence} for c in res.scalars().all()]


@app.get("/api/cases/{case_id}/clusters")
async def get_clusters(case_id: str):
    graph = await get_graph()
    try:
        snap = await graph.aget_state({"configurable": {"thread_id": case_id}})
        return snap.values.get("all_clusters", [])
    except: return []


@app.get("/api/cases/{case_id}/posts")
async def get_posts(case_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RawPost).where(RawPost.case_id == case_id).order_by(RawPost.engagement_score.desc()).limit(limit))
    return [{"post_id": p.post_id, "source": p.source, "text": p.normalized_text, "engagement_score": p.engagement_score} for p in res.scalars().all()]

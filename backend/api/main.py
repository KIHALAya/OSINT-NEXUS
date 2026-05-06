"""
api/main.py

FastAPI application — the real-time API entry point.

Three responsibilities:
  1. Startup: create DB tables, start Redis stream listener background task
  2. Stream listener: consume normalized.posts.v1 → trigger LangGraph runs
  3. REST endpoints: create cases, query leads/claims, get run status

This is Gap #3 from the architecture doc:
  "Implement the FastAPI stream listener to trigger the graph automatically"
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import build_graph, get_graph
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

    # Start Redis stream listener in background
    # Disabled for MVP: Investigation is triggered by New Case form
    # listener_task = asyncio.create_task(_stream_listener())
    # logger.info("Redis stream listener started")

    yield

    # Shutdown
    # listener_task.cancel()
    # try:
    #     await listener_task
    # except asyncio.CancelledError:
    #     pass
    logger.info("API stopped")


app = FastAPI(
    title="OSINT-NEXUS API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Redis stream listener ─────────────────────────────────────────────────────

async def _stream_listener():
    """
    Background task: consumes normalized.posts.v1 from Redis Streams
    and triggers a LangGraph run for each high-signal post.

    Uses consumer group "intelligence-group" so multiple API instances
    don't process the same message twice.
    """
    redis_client = await aioredis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )
    stream = settings.stream_normalized_posts
    group = "intelligence-group"
    consumer = f"api-{uuid.uuid4().hex[:6]}"

    # Create consumer group if it doesn't exist
    try:
        await redis_client.xgroup_create(stream, group, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    logger.info(f"Stream listener ready: stream={stream} group={group} consumer={consumer}")

    graph = get_graph()

    while True:
        try:
            results = await redis_client.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=5,
                block=2000,
            )

            if not results:
                continue

            for _, entries in results:
                for entry_id, raw_fields in entries:
                    try:
                        post = _deserialize(raw_fields)
                        case_id = post.get("case_id")

                        if not case_id:
                            logger.warning(f"Post {entry_id} has no case_id — skipping")
                            await redis_client.xack(stream, group, entry_id)
                            continue

                        # Trigger graph run for this case
                        asyncio.create_task(
                            _trigger_graph_run(graph, case_id, post)
                        )

                        await redis_client.xack(stream, group, entry_id)

                    except Exception as e:
                        logger.error(f"Failed to process stream entry {entry_id}: {e}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Stream listener error: {e}", exc_info=True)
            await asyncio.sleep(2)

    await redis_client.aclose()


async def _trigger_graph_run(graph, case_id: str, post: dict):
    """
    Invoke the graph for a case_id.
    thread_id = case_id ensures state accumulates across runs.
    """
    config = {"configurable": {"thread_id": case_id}}

    try:
        logger.info(f"Triggering graph run: case={case_id}")
        await graph.ainvoke(
            {
                "incoming_post": post,
                # These are set once at case creation and persist via checkpointer
                # On first run they come from DB; subsequent runs read from state
            },
            config=config,
        )
        logger.info(f"Graph run complete: case={case_id}")
    except Exception as e:
        logger.error(f"Graph run failed case={case_id}: {e}", exc_info=True)


def _deserialize(raw_fields: dict[str, str]) -> dict[str, Any]:
    result = {}
    for k, v in raw_fields.items():
        try:
            result[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            result[k] = v
    return result


# ── Request / response models ─────────────────────────────────────────────────

class CreateCaseRequest(BaseModel):
    subject_name: str
    subject_description: str
    age: int | None = None
    location: str | None = None
    last_seen_date: str | None = None
    priority: str = "high"


class RunInvestigationRequest(BaseModel):
    case_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/cases")
async def list_cases(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all investigation cases."""
    result = await db.execute(
        select(Case).order_by(Case.created_at.desc())
    )
    cases = result.scalars().all()
    return [
        {
            "id": c.id,
            "subject": c.subject_name,
            "age": c.age,
            "lastSeen": c.last_seen_date,
            "location": c.location,
            "status": c.status,
            "priority": c.priority,
            "created_at": c.created_at.isoformat(),
        }
        for c in cases
    ]


@app.post("/api/cases", status_code=201)
async def create_case(
    req: CreateCaseRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new investigation case.
    Returns the case_id to use for all subsequent API calls.
    """
    import datetime
    case_id = f"CASE-{datetime.datetime.utcnow().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"

    case = Case(
        id=case_id,
        subject_name=req.subject_name,
        subject_description=req.subject_description,
        age=req.age,
        location=req.location,
        last_seen_date=req.last_seen_date,
        priority=req.priority,
        status="active",
    )
    db.add(case)
    await db.commit()

    logger.info(f"Case created: {case_id} subject={req.subject_name}")
    return {"case_id": case_id, "status": "created"}


@app.post("/api/cases/{case_id}/run")
async def run_investigation(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Manually trigger an investigation run for a case.
    Runs the full proactive pipeline: TikTok search → video analysis → claim extraction → leads.

    Returns immediately; the graph run happens in the background.
    Poll /api/cases/{case_id}/leads to see results.
    """
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    graph = get_graph()

    # Build initial state from case record
    initial_state: dict = {
        "case_id": case_id,
        "subject_name": case.subject_name,
        "subject_description": case.subject_description or "",
        "all_posts": [],
        "all_claims": [],
        "all_clusters": [],
        "all_leads": [],
        "agent_trace": [],
        "analyzed_post_ids": [],
        "current_posts": [],
        "current_claims": [],
        "current_clusters": [],
        "current_leads": [],
        "video_analysis_queue": [],
        "video_analyses_this_run": [],
        "needs_tiktok_search": True,
        "needs_video_analysis": False,
        "needs_verification": [],
        "needs_human_review": False,
    }

    background_tasks.add_task(
        _run_graph_blocking, graph, initial_state, case_id
    )

    return {
        "case_id": case_id,
        "status": "running",
        "message": "Investigation started. Poll /api/cases/{case_id}/leads for results.",
    }


async def _run_graph_blocking(graph, initial_state: dict, case_id: str):
    config = {"configurable": {"thread_id": case_id}}
    try:
        await graph.ainvoke(initial_state, config=config)
        logger.info(f"Investigation complete: case={case_id}")
    except Exception as e:
        logger.error(f"Investigation failed case={case_id}: {e}", exc_info=True)


@app.get("/api/cases/{case_id}/leads")
async def get_leads(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return all leads for a case, ordered by confidence."""
    result = await db.execute(
        select(Lead)
        .where(Lead.case_id == case_id)
        .order_by(Lead.final_score.desc())
    )
    leads = result.scalars().all()
    return [
        {
            "lead_id": l.id,
            "title": l.title,
            "confidence": l.confidence,
            "priority": l.priority,
            "claim_count": l.claim_count,
            "unique_sources": l.unique_sources,
            "evidence": l.evidence,
            "action_required": l.action_required,
            "status": l.status,
            "created_at": l.created_at.isoformat(),
        }
        for l in leads
    ]


@app.get("/api/cases/{case_id}/claims")
async def get_claims(
    case_id: str,
    claim_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return extracted claims for a case, optionally filtered by type."""
    q = select(ExtractedClaimModel).where(ExtractedClaimModel.case_id == case_id)
    if claim_type:
        q = q.where(ExtractedClaimModel.claim_type == claim_type)
    q = q.order_by(ExtractedClaimModel.extraction_confidence.desc())

    result = await db.execute(q)
    claims = result.scalars().all()
    return [
        {
            "claim_id": c.id,
            "claim_type": c.claim_type,
            "statement": c.statement,
            "location_mentioned": c.location_mentioned,
            "confidence": c.extraction_confidence,
            "language": c.language,
            "from_video": c.from_video,
            "cluster_id": c.cluster_id,
        }
        for c in claims
    ]


@app.get("/api/cases/{case_id}/clusters")
async def get_clusters(case_id: str) -> list[dict]:
    """
    Return all clusters for a case.
    Reads from LangGraph checkpointer state.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": case_id}}
    try:
        snapshot = await graph.aget_state(config)
        clusters = snapshot.values.get("all_clusters", [])
        return clusters
    except Exception as e:
        return []


@app.get("/api/cases/{case_id}/trace")
async def get_trace(case_id: str) -> dict:
    """
    Return the agent trace from the last graph run.
    Reads from LangGraph checkpointer state.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": case_id}}
    try:
        snapshot = await graph.aget_state(config)
        trace = snapshot.values.get("agent_trace", [])
        return {"case_id": case_id, "trace": trace}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No state found for case {case_id}: {e}")


@app.get("/api/cases/{case_id}/posts")
async def get_posts(
    case_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return ingested posts for a case."""
    result = await db.execute(
        select(RawPost)
        .where(RawPost.case_id == case_id)
        .order_by(RawPost.engagement_score.desc())
        .limit(limit)
    )
    posts = result.scalars().all()
    return [
        {
            "post_id": p.post_id,
            "source": p.source,
            "text": p.normalized_text,
            "bot_score": p.bot_score,
            "engagement_score": p.engagement_score,
            "plays": p.plays,
            "shares": p.shares,
            "author_name": p.author_name,
            "ingested_at": p.ingested_at.isoformat(),
        }
        for p in posts
    ]
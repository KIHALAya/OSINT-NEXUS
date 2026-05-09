"""
agent/graph.py

The compiled LangGraph investigation pipeline.
All nodes are now real implementations — no stubs.

Proactive flow (per architecture doc):
  bootstrap → tiktok_search → tiktok_ingestor
           → video_selector → [video_analysis?]
           → claim_extractor → clustering → scoring
           → lead_generator → graph_updater → END
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg import AsyncConnection

from agent.state import CaseState
from core.config import settings
from agent.nodes import (
    bootstrap_node,
    tiktok_search_node,
    tiktok_ingestor_node,
    video_selector_node,
    video_analysis_node,
    claim_extractor_node,
    clustering_node,
    scoring_node,
    lead_generator_node,
    graph_updater_node,
)

logger = logging.getLogger(__name__)


# ── Routing ───────────────────────────────────────────────────────────────────

def route_tiktok(state: CaseState) -> str:
    return "tiktok_search" if state.get("needs_tiktok_search") else "video_selector"

def route_video(state: CaseState) -> str:
    return "video_analysis" if state.get("needs_video_analysis") else "claim_extractor"

def route_human_review(state: CaseState) -> str:
    return "human_review_interrupt" if state.get("needs_human_review") else "graph_updater"


# ── Build ─────────────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Compile the investigation graph.

    For production:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as cp:
            graph = build_graph(checkpointer=cp)

    For development / tests:
        graph = build_graph()   # uses MemorySaver
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
        logger.warning("Using MemorySaver — state will NOT persist between process restarts")

    b = StateGraph(CaseState)

    b.add_node("bootstrap",           bootstrap_node)
    b.add_node("tiktok_search",        tiktok_search_node)
    b.add_node("tiktok_ingestor",      tiktok_ingestor_node)
    b.add_node("video_selector",       video_selector_node)
    b.add_node("video_analysis",       video_analysis_node)
    b.add_node("claim_extractor",      claim_extractor_node)
    b.add_node("clustering",           clustering_node)
    b.add_node("scoring",              scoring_node)
    b.add_node("lead_generator",       lead_generator_node)
    b.add_node("graph_updater",        graph_updater_node)
    b.add_node("human_review_interrupt", _human_review_node)

    b.set_entry_point("bootstrap")

    b.add_conditional_edges("bootstrap", route_tiktok, {
        "tiktok_search":  "tiktok_search",
        "video_selector": "video_selector",
    })

    b.add_edge("tiktok_search",   "tiktok_ingestor")
    b.add_edge("tiktok_ingestor", "video_selector")

    b.add_conditional_edges("video_selector", route_video, {
        "video_analysis":  "video_analysis",
        "claim_extractor": "claim_extractor",
    })

    b.add_edge("video_analysis",  "claim_extractor")
    b.add_edge("claim_extractor", "clustering")
    b.add_edge("clustering",      "scoring")
    b.add_edge("scoring",         "lead_generator")

    b.add_conditional_edges("lead_generator", route_human_review, {
        "human_review_interrupt": "human_review_interrupt",
        "graph_updater":          "graph_updater",
    })

    b.add_edge("human_review_interrupt", "graph_updater")
    b.add_edge("graph_updater",           END)

    return b.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review_interrupt"],
    )


async def _human_review_node(state: CaseState) -> dict:
    """
    Graph pauses here for urgent leads.
    Resume via: graph.invoke(Command(resume={}), config=config)
    """
    logger.info(f"[human_review] paused — case={state['case_id']} urgent leads await review")
    return {}


# Module-level singleton for import by api/
_graph = None
_pool = None

async def setup_checkpointer():
    """
    Called once at application startup.
    Ensures Postgres tables/indexes for LangGraph exist.
    """
    if "postgresql" in settings.DATABASE_URL:
        dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        # IMPORTANT: setup() must run on a connection with autocommit=True
        # because it uses CREATE INDEX CONCURRENTLY which cannot run in a transaction.
        async with await AsyncConnection.connect(dsn, autocommit=True) as conn:
            checkpointer = AsyncPostgresSaver(conn)
            await checkpointer.setup()
            logger.info("LangGraph Postgres checkpointer setup complete")

async def get_graph():
    global _graph, _pool
    if _graph is None:
        # Check if we should use Postgres persistence
        if "postgresql" in settings.DATABASE_URL:
            # langgraph-checkpoint-postgres uses psycopg DSN format.
            # Convert SQLAlchemy asyncpg URL to standard postgres DSN if necessary.
            dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

            _pool = AsyncConnectionPool(conninfo=dsn, max_size=20)
            checkpointer = AsyncPostgresSaver(_pool)
            # Setup is now handled in setup_checkpointer() during startup
            _graph = build_graph(checkpointer=checkpointer)
        else:
            _graph = build_graph()
    return _graph
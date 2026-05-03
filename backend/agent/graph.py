"""
agent/graph.py

Builds and compiles the LangGraph investigation graph.

Node execution order:
  intake → [tiktok_search? → tiktok_ingestor] → claim_extractor
        → clustering → scoring → [verify?] → misinfo_filter
        → [human_review?] → lead_generator → graph_updater → END

TikTok fits in as a conditional branch right after intake:
  - intake sets needs_tiktok_search = True when the incoming post
    mentions a TikTok-specific signal OR when it's the first post
    for a case that has no TikTok coverage yet.
  - The tiktok_search_node calls the @tool and merges results into state.
  - Then normal pipeline continues with all sources combined.
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from agent.state import CaseState
from agent.nodes import (
    intake_node,
    tiktok_search_node,
    tiktok_ingestor_node,
    claim_extractor_node,
    clustering_node,
    scoring_node,
    verification_node,
    misinfo_filter_node,
    lead_generator_node,
    graph_updater_node,
)

logger = logging.getLogger(__name__)


# ── Routing functions (conditional edges) ────────────────────────────────────

def route_after_intake(state: CaseState) -> str:
    """
    After intake: should we search TikTok before claim extraction?

    We search TikTok when:
    - The incoming post is FROM TikTok (we want more context around it)
    - It's the first run for this case (bootstrap TikTok coverage)
    - The intake node explicitly flagged it
    """
    if state.get("needs_tiktok_search"):
        return "tiktok_search"
    return "claim_extractor"


def route_after_scoring(state: CaseState) -> str:
    """After scoring: is there anything worth verifying?"""
    if state.get("needs_verification"):
        return "verifier"
    return "misinfo_filter"


def route_after_misinfo(state: CaseState) -> str:
    """After misinfo filter: does a human need to review?"""
    if state.get("needs_human_review"):
        return "human_review"
    return "lead_generator"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Builds and compiles the investigation graph.

    checkpointer: pass PostgresSaver for production, MemorySaver for dev/tests.
    If None, defaults to MemorySaver (in-memory, resets on restart).

    Usage:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as cp:
            graph = build_graph(checkpointer=cp)
            await graph.ainvoke(initial_state, config={"configurable": {"thread_id": case_id}})
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
        logger.warning("Using in-memory checkpointer — state won't survive restarts")

    builder = StateGraph(CaseState)

    # ── Register nodes ────────────────────────────────────────────────────────

    builder.add_node("intake", intake_node)

    # TikTok branch: two nodes
    #   tiktok_search  → calls the @tool, gets raw TikTokPosts
    #   tiktok_ingestor → converts TikTokPosts → NormalizedPosts in state
    builder.add_node("tiktok_search", tiktok_search_node)
    builder.add_node("tiktok_ingestor", tiktok_ingestor_node)

    builder.add_node("claim_extractor", claim_extractor_node)
    builder.add_node("clustering", clustering_node)
    builder.add_node("scoring", scoring_node)
    builder.add_node("verifier", verification_node)
    builder.add_node("misinfo_filter", misinfo_filter_node)

    # human_review is an interrupt node — graph pauses here until
    # the investigator calls graph.invoke(Command(resume=...), config)
    builder.add_node("human_review", _human_review_interrupt)

    builder.add_node("lead_generator", lead_generator_node)
    builder.add_node("graph_updater", graph_updater_node)

    # ── Edges ─────────────────────────────────────────────────────────────────

    builder.set_entry_point("intake")

    # intake → TikTok branch OR straight to claim_extractor
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "tiktok_search": "tiktok_search",
            "claim_extractor": "claim_extractor",
        },
    )

    # TikTok branch always rejoins at claim_extractor
    builder.add_edge("tiktok_search", "tiktok_ingestor")
    builder.add_edge("tiktok_ingestor", "claim_extractor")

    # Linear pipeline from claim extraction through clustering/scoring
    builder.add_edge("claim_extractor", "clustering")
    builder.add_edge("clustering", "scoring")

    # Conditional: verify or skip
    builder.add_conditional_edges(
        "scoring",
        route_after_scoring,
        {
            "verifier": "verifier",
            "misinfo_filter": "misinfo_filter",
        },
    )

    builder.add_edge("verifier", "misinfo_filter")

    # Conditional: human review or proceed
    builder.add_conditional_edges(
        "misinfo_filter",
        route_after_misinfo,
        {
            "human_review": "human_review",
            "lead_generator": "lead_generator",
        },
    )

    builder.add_edge("human_review", "lead_generator")
    builder.add_edge("lead_generator", "graph_updater")
    builder.add_edge("graph_updater", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],   # pause before executing this node
    )


async def _human_review_interrupt(state: CaseState) -> dict:
    """
    Pause point for investigator review.
    LangGraph interrupt() is called here automatically because
    this node is listed in interrupt_before= above.

    When the investigator approves via the API:
        graph.invoke(Command(resume={"approved": True}), config=config)
    the graph continues from this node's output.
    """
    logger.info(f"Graph paused for human review on case {state['case_id']}")
    # In production: emit a WebSocket event here so the frontend knows to show the review UI
    return {}
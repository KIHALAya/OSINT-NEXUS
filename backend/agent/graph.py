"""
agent/graph.py

Orchestration logic for the OSINT-NEXUS investigation agent.
Implements the 'Proactive Ingestion' model where data acquisition 
is the mandatory first step for every new investigation.
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import CaseState
from agent.nodes import (
    bootstrap_node, 
    tiktok_search_node, 
    tiktok_ingestor_node,
    video_selector_node, 
    video_analysis_node,
    claim_extractor_node, 
    clustering_node, 
    scoring_node,
    verification_node, 
    misinfo_filter_node,
    lead_generator_node, 
    graph_updater_node
)

logger = logging.getLogger(__name__)


# ── Routing Logic ─────────────────────────────────────────────────────────────

def route_after_video_selector(state: CaseState) -> str:
    """Routes to Gemini video analysis if high-signal videos were queued."""
    return "video_analysis" if state.get("needs_video_analysis") else "claim_extractor"


def route_after_scoring(state: CaseState) -> str:
    """Routes to human or AI verification if cluster scores are high."""
    return "verifier" if state.get("needs_verification") else "misinfo_filter"


def route_after_misinfo(state: CaseState) -> str:
    """Interrupts for human review if misinformation is suspected."""
    return "human_review" if state.get("needs_human_review") else "lead_generator"


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()

    workflow = StateGraph(CaseState)

    # 1. Define Nodes
    workflow.add_node("bootstrap",       bootstrap_node)
    workflow.add_node("tiktok_search",   tiktok_search_node)
    workflow.add_node("tiktok_ingestor", tiktok_ingestor_node)
    workflow.add_node("video_selector",  video_selector_node)
    workflow.add_node("video_analysis",  video_analysis_node)
    workflow.add_node("claim_extractor", claim_extractor_node)
    workflow.add_node("clustering",      clustering_node)
    workflow.add_node("scoring",         scoring_node)
    workflow.add_node("verifier",        verification_node)
    workflow.add_node("misinfo_filter",  misinfo_filter_node)
    workflow.add_node("human_review",    _human_review_interrupt)
    workflow.add_node("lead_generator",  lead_generator_node)
    workflow.add_node("graph_updater",   graph_updater_node)

    # 2. Define Edges (The Pipeline Flow)
    
    # Entry Point: Always bootstrap and then search
    workflow.set_entry_point("bootstrap")
    workflow.add_edge("bootstrap", "tiktok_search")
    
    # Ingestion Path
    workflow.add_edge("tiktok_search",   "tiktok_ingestor")
    workflow.add_edge("tiktok_ingestor", "video_selector")

    # Video Analysis Branch
    workflow.add_conditional_edges("video_selector", route_after_video_selector, {
        "video_analysis":  "video_analysis",
        "claim_extractor": "claim_extractor",
    })
    workflow.add_edge("video_analysis", "claim_extractor")

    # Intelligence Path
    workflow.add_edge("claim_extractor", "clustering")
    workflow.add_edge("clustering",      "scoring")

    # Verification & Filtering Branch
    workflow.add_conditional_edges("scoring", route_after_scoring, {
        "verifier":       "verifier",
        "misinfo_filter": "misinfo_filter",
    })
    workflow.add_edge("verifier", "misinfo_filter")

    # Finalization Branch
    workflow.add_conditional_edges("misinfo_filter", route_after_misinfo, {
        "human_review":   "human_review",
        "lead_generator": "lead_generator",
    })
    
    workflow.add_edge("human_review",   "lead_generator")
    workflow.add_edge("lead_generator", "graph_updater")
    workflow.add_edge("graph_updater",  END)

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )


async def _human_review_interrupt(state: CaseState) -> dict:
    logger.info(f"Graph paused for human review — case {state['case_id']}")
    return {}

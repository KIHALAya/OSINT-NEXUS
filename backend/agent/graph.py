"""
agent/graph_video.py

Updated graph with video analysis branch wired in.

Full node order:
    intake
      ↓ (needs_tiktok_search?)
    tiktok_search → tiktok_ingestor
      ↓ (both paths meet here)
    video_selector              ← NEW: decides what to analyze
      ↓ (needs_video_analysis?)
    video_analysis              ← NEW: calls Gemini for queued posts
      ↓ (both paths meet here)
    claim_extractor             ← now receives text + video claims
    → clustering → scoring
      ↓ (needs_verification?)
    verifier
    → misinfo_filter
      ↓ (needs_human_review?)
    human_review
    → lead_generator → graph_updater → END
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import CaseState
from agent.nodes_video import video_selector_node, video_analysis_node

logger = logging.getLogger(__name__)


def route_after_intake(state: CaseState) -> str:
    return "tiktok_search" if state.get("needs_tiktok_search") else "video_selector"


def route_after_tiktok_ingestor(state: CaseState) -> str:
    return "video_selector"


def route_after_video_selector(state: CaseState) -> str:
    return "video_analysis" if state.get("needs_video_analysis") else "claim_extractor"


def route_after_scoring(state: CaseState) -> str:
    return "verifier" if state.get("needs_verification") else "misinfo_filter"


def route_after_misinfo(state: CaseState) -> str:
    return "human_review" if state.get("needs_human_review") else "lead_generator"


def build_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()

    # Import stub nodes from nodes.py (unchanged)
    from agent.nodes import (
        intake_node, tiktok_search_node, tiktok_ingestor_node,
        claim_extractor_node, clustering_node, scoring_node,
        verification_node, misinfo_filter_node,
        lead_generator_node, graph_updater_node,
    )

    b = StateGraph(CaseState)

    b.add_node("intake",           intake_node)
    b.add_node("tiktok_search",    tiktok_search_node)
    b.add_node("tiktok_ingestor",  tiktok_ingestor_node)
    b.add_node("video_selector",   video_selector_node)    # NEW
    b.add_node("video_analysis",   video_analysis_node)    # NEW
    b.add_node("claim_extractor",  claim_extractor_node)
    b.add_node("clustering",       clustering_node)
    b.add_node("scoring",          scoring_node)
    b.add_node("verifier",         verification_node)
    b.add_node("misinfo_filter",   misinfo_filter_node)
    b.add_node("human_review",     _human_review_interrupt)
    b.add_node("lead_generator",   lead_generator_node)
    b.add_node("graph_updater",    graph_updater_node)

    b.set_entry_point("intake")

    b.add_conditional_edges("intake", route_after_intake, {
        "tiktok_search":  "tiktok_search",
        "video_selector": "video_selector",
    })

    b.add_edge("tiktok_search",   "tiktok_ingestor")
    b.add_edge("tiktok_ingestor", "video_selector")   # always goes to selector

    b.add_conditional_edges("video_selector", route_after_video_selector, {
        "video_analysis":  "video_analysis",
        "claim_extractor": "claim_extractor",
    })

    b.add_edge("video_analysis",  "claim_extractor")
    b.add_edge("claim_extractor", "clustering")
    b.add_edge("clustering",      "scoring")

    b.add_conditional_edges("scoring", route_after_scoring, {
        "verifier":      "verifier",
        "misinfo_filter": "misinfo_filter",
    })

    b.add_edge("verifier", "misinfo_filter")

    b.add_conditional_edges("misinfo_filter", route_after_misinfo, {
        "human_review":  "human_review",
        "lead_generator": "lead_generator",
    })

    b.add_edge("human_review",   "lead_generator")
    b.add_edge("lead_generator", "graph_updater")
    b.add_edge("graph_updater",  END)

    return b.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )


async def _human_review_interrupt(state: CaseState) -> dict:
    logger.info(f"Graph paused for human review — case {state['case_id']}")
    return {}
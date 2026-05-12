"""
agent/state.py

CaseState — the longitudinal memory of a single investigation.
thread_id = case_id means all runs for the same case share this state.
LangGraph's PostgresSaver checkpointer persists it between runs.
"""

from __future__ import annotations

import operator
from typing import Annotated
from typing_extensions import TypedDict

# ── Sub-types ─────────────────────────────────────────────────────────────────

class IncomingPost(TypedDict):
    event_id: str
    case_id: str
    source: str                 # "tiktok" | "reddit" | "twitter"
    post_id: str
    normalized_text: str
    detected_language: str
    bot_score: float
    is_duplicate: bool
    author_id: str
    author_name: str
    author_followers: int
    author_verified: bool
    engagement_score: float
    likes: int
    shares: int
    plays: int
    posted_at: str | None
    video_url: str | None       # populated for TikTok posts
    thumbnail_url: str | None
    hashtags: list[str]
    media: list[dict]


class ExtractedClaim(TypedDict):
    claim_id: str
    source_event_id: str
    case_id: str
    claim_type: str             # "sighting" | "location" | "rumour" | "denial"
    statement: str
    location_mentioned: str | None
    time_mentioned: str | None
    extraction_confidence: float
    language: str
    embedding_vector: list[float]   # 768-dim, populated by claim_extractor_node
    qdrant_point_id: str | None     # populated after Qdrant upsert
    from_video: bool
    video_post_id: str | None


class ClusterState(TypedDict):
    cluster_id: str
    label: str                  # human-readable label generated from top claims
    claim_ids: list[str]
    _point_ids: list[str]       # Qdrant internal IDs
    platform_breakdown: dict    # {"tiktok": 12, "reddit": 5, ...}
    crowd_score: float
    final_score: float
    status: str                 # "high-signal" | "medium" | "low" | "misinformation"
    misinfo_reason: str | None


class LeadState(TypedDict):
    lead_id: str
    cluster_id: str
    title: str
    confidence: float
    crowd_score: float
    final_score: float
    claim_count: int
    unique_sources: int
    evidence: list[str]
    action_required: str
    priority: str               # "urgent" | "high" | "medium" | "low"


class AgentStep(TypedDict):
    agent: str
    input_summary: str
    decision: str
    reasoning: str
    timestamp: int


# ── Main state ────────────────────────────────────────────────────────────────

class CaseState(TypedDict):

    # ── Identity (set once, never changes) ───────────────────────────────────
    case_id: str
    run_id: str
    subject_name: str
    subject_description: str    # fed into video analysis + claim extraction

    # ── Accumulated across ALL runs (operator.add = append) ──────────────────
    all_posts: Annotated[list[IncomingPost], operator.add]
    all_claims: Annotated[list[ExtractedClaim], operator.add]
    
    # ── Replaced across runs (NO operator.add for evolving sets) ─────────────
    all_clusters: list[ClusterState]
    all_leads: list[LeadState]
    
    agent_trace: Annotated[list[AgentStep], operator.add]

    # TikTok-specific accumulated
    analyzed_post_ids: Annotated[list[str], operator.add]   # prevents re-analysis

    # ── Current run (reset / replaced each run) ───────────────────────────────
    current_search_queries: list[str]
    current_hashtags: list[str]
    last_tiktok_result: dict | None             # Raw dict output, NEVER Pydantic
    current_posts: list[IncomingPost]           # posts ingested this run
    current_claims: list[ExtractedClaim]        # claims extracted this run
    current_clusters: list[ClusterState]        # clusters updated this run
    current_leads: list[LeadState]              # leads generated this run
    video_analysis_queue: list[dict]            # {post_id, video_url} queued this run
    video_analyses_this_run: list[dict]         # VideoSignals dicts this run

    # ── Routing signals (read by conditional edges) ───────────────────────────
    needs_tiktok_search: bool
    needs_video_analysis: bool
    needs_verification: list[str]   # cluster_ids above threshold
    needs_human_review: bool

    # ── Current run results (reset each run) ──────────────────────────────────
    tiktok_normalized_posts_this_run: list[IncomingPost]
    extracted_claims_this_run: list[ExtractedClaim]
    scores_this_run: dict[str, float]
    misinfo_flags_this_run: list[dict]
    tiktok_viral_flags: Annotated[list[dict], operator.add]

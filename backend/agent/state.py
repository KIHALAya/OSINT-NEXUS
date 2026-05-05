from __future__ import annotations

import operator
from typing import Annotated, Any
from typing_extensions import TypedDict

from tools.tiktok_search import TikTokPost, TikTokSearchResult
from tools.video_analysis import VideoSignals


# ── Sub-types ─────────────────────────────────────────────────────────────────

class IncomingPost(TypedDict):
    """A normalized post arriving from Redis Streams."""
    event_id: str
    case_id: str
    source: str          # "tiktok" | "reddit" | "twitter" | ...
    post_id: str
    normalized_text: str
    detected_language: str
    bot_score: float
    is_duplicate: bool
    author_id: str
    engagement_score: float
    posted_at: int | None
    media: list[dict]


class ExtractedClaim(TypedDict):
    claim_id: str
    source_event_id: str
    case_id: str
    type: str               # "sighting" | "rumour" | "contradiction"
    statement: str
    location_mentioned: str | None
    time_mentioned: str | None
    extraction_confidence: float
    embedding_vector: list[float]
    video_post_id: str | None # Optional link to video analysis


class ClusterState(TypedDict):
    cluster_id: str
    label: str
    claim_ids: list[str]
    crowd_score: float
    ai_verification_score: float
    final_score: float
    status: str             # "high-signal" | "medium" | "low" | "misinformation"
    misinfo_reason: str | None


class Lead(TypedDict):
    lead_id: str
    cluster_id: str
    title: str
    confidence: float
    evidence: list[str]
    action_required: str


class AgentStep(TypedDict):
    agent: str
    input_summary: str
    decision: str
    reasoning: str
    timestamp: int


# ── Main state ────────────────────────────────────────────────────────────────

class CaseState(TypedDict):
    """
    Full investigation state for one case.
    thread_id (= case_id) is the LangGraph key — state persists
    across all messages arriving for this case.

    Annotated[list, operator.add] means LangGraph *appends* to these
    lists when nodes return partial updates, rather than replacing them.
    This is what gives us accumulated context across multiple runs.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    case_id: str
    run_id: str

    # ── Subject Info (Set at bootstrap) ───────────────────────────────────────
    subject_name: str
    subject_description: str
    last_known_location: str | None
    last_seen_date: str | None

    # ── Incoming trigger (Optional, if run is post-driven) ─────────────────────
    incoming_post: IncomingPost | None

    # ── Accumulated context (grows across ALL runs for this case) ─────────────
    all_claims: Annotated[list[ExtractedClaim], operator.add]
    clusters: Annotated[list[ClusterState], operator.add]
    leads: Annotated[list[Lead], operator.add]
    agent_trace: Annotated[list[AgentStep], operator.add]

    # ── TikTok-specific state ─────────────────────────────────────────────────
    tiktok_posts: Annotated[list[TikTokPost], operator.add]
    last_tiktok_search: TikTokSearchResult | None
    
    # Video analysis results (accumulated)
    video_analyses: Annotated[list[VideoSignals], operator.add]

    # Tracks which post_ids have been analyzed to prevent duplicates
    analyzed_post_ids: Annotated[list[str], operator.add]
 
    # Posts queued for analysis this specific run
    video_analysis_queue: list[dict]

    # ── Routing signals ───────────────────────────────────────────────────────
    needs_tiktok_search: bool
    needs_video_analysis: bool
    needs_verification: list[str]   # cluster_ids
    needs_human_review: bool

    # ── Current run results (reset each run) ──────────────────────────────────
    tiktok_normalized_posts_this_run: list[IncomingPost]
    extracted_claims_this_run: list[ExtractedClaim]
    scores_this_run: dict[str, float]
    misinfo_flags_this_run: list[dict]
    tiktok_viral_flags: Annotated[list[dict], operator.add]

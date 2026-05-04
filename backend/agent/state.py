
from __future__ import annotations

from typing import Annotated, Any
import operator
from typing_extensions import TypedDict

from tools.tiktok_search import TikTokPost, TikTokSearchResult


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

    # ── Incoming trigger (changes each run) ───────────────────────────────────
    incoming_post: IncomingPost | None

    subject_description : str

    # ── Accumulated context (grows across ALL runs for this case) ─────────────
    # operator.add means each node can append to these lists
    all_claims: Annotated[list[ExtractedClaim], operator.add]
    clusters: Annotated[list[ClusterState], operator.add]
    leads: Annotated[list[Lead], operator.add]
    agent_trace: Annotated[list[AgentStep], operator.add]

    # ── TikTok-specific state ─────────────────────────────────────────────────
    # Raw posts from TikTok searches, accumulated across runs
    tiktok_posts: Annotated[list[TikTokPost], operator.add]

    # Last search result (replaced each run, not accumulated)
    last_tiktok_search: TikTokSearchResult | None

    #video  analysis results 
    video_analysis: Annotated[list[VideoSignals], operator.add]

     # NEW: tracks which post_ids have been analyzed so we never repeat
    # This is a set serialised as list (TypedDict doesn't support set)
    analyzed_post_ids: Annotated[list[str], operator.add]
 
    # NEW: posts the selector node queued for analysis this run
    video_analysis_queue: list[dict]    # list of {post_id, video_url}

    # Known viral content on TikTok for this case
    # Updated by the misinfo filter when it detects amplification patterns
    tiktok_viral_flags: Annotated[list[dict], operator.add]

    # ── Routing signals (set each run, read by conditional edges) ─────────────
    needs_tiktok_search: bool       # should the agent call search_tiktok?
    needs_video_analysis : bool
    needs_verification: list[str]   # cluster_ids above scoring threshold
    needs_human_review: bool

    # ── Current run results (reset each run) ──────────────────────────────────
    extracted_claims_this_run: list[ExtractedClaim]
    scores_this_run: dict[str, float]
    misinfo_flags_this_run: list[dict]
    tiktok_viral_flags : Annotated[list[dict], operator.add]
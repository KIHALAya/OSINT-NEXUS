"""
agent/nodes.py

Every node function in the investigation graph.
Each function receives CaseState and returns a dict of state updates.
LangGraph merges the returned dict into the existing state
(it does NOT replace the whole state).

TikTok-specific nodes:
  - tiktok_search_node    calls the @tool and stores raw results
  - tiktok_ingestor_node  converts TikTokPost objects into the
                           same normalized shape as posts from other
                           platforms, so claim_extractor_node is
                           platform-agnostic
"""

import hashlib
import logging
import time
import uuid
from typing import Any

from agent.state import CaseState, ExtractedClaim, AgentStep, IncomingPost
from tools.tiktok_search import search_tiktok, TikTokPost, TikTokSearchResult

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trace(agent: str, input_summary: str, decision: str, reasoning: str) -> AgentStep:
    return AgentStep(
        agent=agent,
        input_summary=input_summary,
        decision=decision,
        reasoning=reasoning,
        timestamp=int(time.time() * 1000),
    )


def _build_tiktok_keywords(state: CaseState) -> list[str]:
    """
    Build TikTok search keywords from the case context in state.
    In production this reads from a Case object in the DB.
    For now we derive from the incoming post's text and known signals.
    """
    keywords = []

    post = state.get("incoming_post")
    if post:
        # Include the post text itself as a search seed
        text = post.get("normalized_text", "")
        if text and len(text) > 5:
            # Take first meaningful chunk as a keyword
            keywords.append(text[:60].strip())

    # Always add case_id-based hashtag searches if we have structured data
    # In production: case_id → DB lookup → subject name, location
    # Hardcoded fallback for illustration
    case_id = state.get("case_id", "")
    if "0847" in case_id:
        keywords.extend(["amira benali", "morocco mall missing", "مول المغرب مختفية"])

    # Deduplicate, limit to 5 keywords (each adds to API cost and run time)
    seen = set()
    result = []
    for k in keywords:
        if k not in seen and k:
            seen.add(k)
            result.append(k)
    return result[:5]


# ── Node: intake ──────────────────────────────────────────────────────────────

async def intake_node(state: CaseState) -> dict:
    """
    Receives the incoming normalized post and decides whether to
    trigger a TikTok search before claim extraction.

    Triggers TikTok search when:
      1. This is the first post for the case (no prior TikTok coverage)
      2. The incoming post IS from TikTok (need context around it)
      3. Incoming post text contains TikTok-specific signals
         ("tiktok", "video", "duet", "@username" style patterns)
    """
    post = state.get("incoming_post")
    tiktok_posts_so_far = state.get("tiktok_posts", [])
    is_first_run = len(tiktok_posts_so_far) == 0
    incoming_is_tiktok = post and post.get("source") == "tiktok"

    needs_tiktok = bool(is_first_run or incoming_is_tiktok)

    trace = _trace(
        agent="intake",
        input_summary=f"post_id={post.get('post_id') if post else 'none'} source={post.get('source') if post else 'none'}",
        decision=f"needs_tiktok_search={needs_tiktok}",
        reasoning=(
            "First run for case — bootstrapping TikTok coverage" if is_first_run
            else "Incoming post is from TikTok — need broader context"
            if incoming_is_tiktok
            else "No TikTok search needed this run"
        ),
    )

    return {
        "needs_tiktok_search": needs_tiktok,
        "agent_trace": [trace],
    }


# ── Node: tiktok_search ───────────────────────────────────────────────────────

async def tiktok_search_node(state: CaseState) -> dict:
    """
    Calls the search_tiktok @tool.
    Stores the raw TikTokSearchResult in state.
    The tiktok_ingestor_node handles converting results to normalized posts.
    """
    case_id = state["case_id"]
    keywords = _build_tiktok_keywords(state)

    if not keywords:
        logger.warning(f"No TikTok keywords for case={case_id}, skipping search")
        return {
            "last_tiktok_search": None,
            "agent_trace": [_trace(
                "tiktok_search", "no keywords", "skipped", "Could not derive search keywords"
            )],
        }

    logger.info(f"TikTok search case={case_id} keywords={keywords}")

    # Call the @tool directly (it's just an async function)
    result: TikTokSearchResult = await search_tiktok.ainvoke({
        "case_id": case_id,
        "keywords": keywords,
        "max_results": 50,
    })

    trace = _trace(
        agent="tiktok_search",
        input_summary=f"keywords={keywords}",
        decision=f"found={result.total_found} posts, error={result.error}",
        reasoning=(
            f"Retrieved {result.total_found} TikTok posts via Apify {result.apify_actor_used}"
            if not result.error
            else f"Search failed: {result.error}"
        ),
    )

    return {
        "last_tiktok_search": result,
        "tiktok_posts": result.posts,    # operator.add appends to existing list
        "agent_trace": [trace],
    }


# ── Node: tiktok_ingestor ─────────────────────────────────────────────────────

async def tiktok_ingestor_node(state: CaseState) -> dict:
    """
    Converts TikTokPost objects from the last search into IncomingPost
    objects and appends them to a temporary list that claim_extractor_node
    will process.

    This is the adapter between TikTok-specific data and the platform-
    agnostic pipeline. After this node, claim_extractor_node doesn't
    know or care whether a post came from TikTok, Reddit, or Twitter.
    """
    last_search: TikTokSearchResult | None = state.get("last_tiktok_search")
    if not last_search or not last_search.posts:
        return {"agent_trace": [_trace(
            "tiktok_ingestor", "no search results", "skipped", "Nothing to ingest"
        )]}

    case_id = state["case_id"]
    normalized_posts: list[IncomingPost] = []

    for post in last_search.posts:
        if not post.text or not post.text.strip():
            continue

        # Bot-score heuristic for TikTok
        # Very low follower count + high plays = potential coordinated amplification
        bot_score = 0.0
        if post.author_followers < 10 and post.plays > 10000:
            bot_score = 0.6
        elif post.author_followers < 100 and post.plays > 100000:
            bot_score = 0.4

        normalized_posts.append(IncomingPost(
            event_id=f"tiktok_{post.post_id}_{int(time.time())}",
            case_id=case_id,
            source="tiktok",
            post_id=post.post_id,
            normalized_text=post.text,
            detected_language="unknown",   # LLM will handle multilingual
            bot_score=bot_score,
            is_duplicate=False,
            author_id=post.author_id,
            engagement_score=post.engagement_score,
            posted_at=None,
            media=[{"type": "thumbnail", "url": post.thumbnail_url}]
                if post.thumbnail_url else [],
        ))

    trace = _trace(
        agent="tiktok_ingestor",
        input_summary=f"raw_posts={len(last_search.posts)}",
        decision=f"normalized={len(normalized_posts)} posts",
        reasoning=f"Dropped {len(last_search.posts) - len(normalized_posts)} empty/invalid posts",
    )

    # We store normalized tiktok posts in a dedicated field so
    # claim_extractor_node can process them alongside the main incoming_post
    return {
        "tiktok_normalized_posts_this_run": normalized_posts,
        "agent_trace": [trace],
    }


# ── Node: claim_extractor ─────────────────────────────────────────────────────

async def claim_extractor_node(state: CaseState) -> dict:
    """
    Extracts structured claims from:
      1. The main incoming_post (from Redis Streams)
      2. Any TikTok posts ingested this run

    Stub implementation — replace with LLM call.
    See agent/prompts.py for the extraction prompt.
    """
    posts_to_process: list[dict] = []

    incoming = state.get("incoming_post")
    if incoming:
        posts_to_process.append(incoming)

    # Include TikTok posts from this run
    tiktok_this_run = state.get("tiktok_normalized_posts_this_run", [])
    posts_to_process.extend(tiktok_this_run)

    claims: list[ExtractedClaim] = []
    for post in posts_to_process:
        # TODO: replace with actual LLM call using prompts.CLAIM_EXTRACTION_PROMPT
        claims.append(ExtractedClaim(
            claim_id=f"clm_{uuid.uuid4().hex[:12]}",
            source_event_id=post.get("event_id", ""),
            case_id=state["case_id"],
            type="sighting",
            statement=post.get("normalized_text", "")[:120],
            location_mentioned=None,
            time_mentioned=None,
            extraction_confidence=0.5,
            embedding_vector=[],
        ))

    trace = _trace(
        agent="claim_extractor",
        input_summary=f"posts={len(posts_to_process)}",
        decision=f"extracted={len(claims)} claims",
        reasoning="Extracted one claim per post (stub — replace with LLM)",
    )

    return {
        "all_claims": claims,             # operator.add appends to accumulated list
        "extracted_claims_this_run": claims,
        "agent_trace": [trace],
    }


# ── Node stubs (to be implemented in next sprint) ─────────────────────────────

async def clustering_node(state: CaseState) -> dict:
    logger.info(f"[clustering] {len(state.get('extracted_claims_this_run', []))} claims")
    return {"agent_trace": [_trace("clustering", "stub", "pass-through", "Not yet implemented")]}


async def scoring_node(state: CaseState) -> dict:
    logger.info("[scoring] computing crowd scores")
    return {
        "needs_verification": [],
        "scores_this_run": {},
        "agent_trace": [_trace("scoring", "stub", "pass-through", "Not yet implemented")],
    }


async def verification_node(state: CaseState) -> dict:
    logger.info("[verifier] running AI verification")
    return {"agent_trace": [_trace("verifier", "stub", "pass-through", "Not yet implemented")]}


async def misinfo_filter_node(state: CaseState) -> dict:
    logger.info("[misinfo_filter] checking for misinformation")
    return {
        "needs_human_review": False,
        "misinfo_flags_this_run": [],
        "agent_trace": [_trace("misinfo_filter", "stub", "pass-through", "Not yet implemented")],
    }


async def lead_generator_node(state: CaseState) -> dict:
    logger.info("[lead_generator] generating leads")
    return {"agent_trace": [_trace("lead_generator", "stub", "pass-through", "Not yet implemented")]}


async def graph_updater_node(state: CaseState) -> dict:
    logger.info("[graph_updater] updating Neo4j + pushing WebSocket event")
    return {"agent_trace": [_trace("graph_updater", "stub", "pass-through", "Not yet implemented")]}
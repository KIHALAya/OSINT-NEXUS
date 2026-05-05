"""
agent/nodes.py

Every node function in the investigation graph.
Each function receives CaseState and returns a dict of state updates.
LangGraph merges the returned dict into the existing state.
"""

import hashlib
import logging
import time
import uuid
from typing import Any

from agent.state import CaseState, ExtractedClaim, AgentStep, IncomingPost
from tools.tiktok_search import search_tiktok, TikTokPost, TikTokSearchResult
from tools.video_analysis import analyze_video, VideoSignals

logger = logging.getLogger(__name__)

# A post must exceed AT LEAST ONE of these to be worth video analysis
VIDEO_ANALYSIS_MIN_PLAYS  = 5_000
VIDEO_ANALYSIS_MIN_SHARES = 50
 
# Never analyze more than this many videos per agent run
MAX_VIDEOS_PER_RUN = 5
 
# Bot score must be below this threshold
BOT_SCORE_MAX = 0.4


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_trace(agent: str, input_summary: str, decision: str, reasoning: str) -> AgentStep:
    return AgentStep(
        agent=agent,
        input_summary=input_summary,
        decision=decision,
        reasoning=reasoning,
        timestamp=int(time.time() * 1000),
    )


def _build_tiktok_keywords(state: CaseState) -> list[str]:
    """
    Build TikTok search keywords from the case context.
    Prioritizes subject name and last known location.
    """
    keywords = []

    name = state.get("subject_name", "")
    location = state.get("last_known_location", "")

    if name:
        keywords.append(name)
        if location:
            keywords.append(f"{name} {location}")

    # Fallback to incoming post text if available
    post = state.get("incoming_post")
    if post:
        text = post.get("normalized_text", "")
        if text and len(text) > 5:
            keywords.append(text[:60].strip())

    # Deduplicate and limit
    seen = set()
    result = []
    for k in keywords:
        if k and k.lower() not in seen:
            seen.add(k.lower())
            result.append(k)
    
    return result[:5]


# ── Node: bootstrap ───────────────────────────────────────────────────────────

async def bootstrap_node(state: CaseState) -> dict:
    """
    Initializes the investigation run. 
    In the proactive model, we always trigger an initial ingestion
    if this is a new run or a direct user request.
    """
    case_id = state.get("case_id", "UNKNOWN")
    subject = state.get("subject_name", "Unknown Subject")
    
    logger.info(f"[bootstrap] starting investigation for case={case_id} subject={subject}")

    trace = _make_trace(
        agent="bootstrap",
        input_summary=f"case_id={case_id} subject={subject}",
        decision="trigger_ingestion=True",
        reasoning="Proactive flow: Ingestion is mandatory for initial data acquisition.",
    )

    return {
        "needs_tiktok_search": True,
        "agent_trace": [trace],
    }


# ── Node: tiktok_search ───────────────────────────────────────────────────────

async def tiktok_search_node(state: CaseState) -> dict:
    """
    Calls the search_tiktok @tool.
    """
    case_id = state["case_id"]
    keywords = _build_tiktok_keywords(state)

    if not keywords:
        logger.warning(f"No TikTok keywords for case={case_id}, skipping search")
        return {
            "last_tiktok_search": None,
            "agent_trace": [_make_trace(
                "tiktok_search", "no keywords", "skipped", "Could not derive search keywords"
            )],
        }

    logger.info(f"TikTok search case={case_id} keywords={keywords}")

    result: TikTokSearchResult = await search_tiktok.ainvoke({
        "case_id": case_id,
        "keywords": keywords,
        "max_results": 50,
    })

    trace = _make_trace(
        agent="tiktok_search",
        input_summary=f"keywords={keywords}",
        decision=f"found={result.total_found} posts",
        reasoning=f"Retrieved viral TikTok content for subject: {state.get('subject_name')}",
    )

    return {
        "last_tiktok_search": result,
        "tiktok_posts": result.posts,
        "agent_trace": [trace],
    }


# ── Node: tiktok_ingestor ─────────────────────────────────────────────────────

async def tiktok_ingestor_node(state: CaseState) -> dict:
    """
    Normalizes TikTok results for the platform-agnostic pipeline.
    """
    last_search = state.get("last_tiktok_search")
    if not last_search or not last_search.posts:
        return {"agent_trace": [_make_trace(
            "tiktok_ingestor", "no results", "skipped", "Nothing to ingest"
        )]}

    normalized_posts: list[IncomingPost] = []
    for post in last_search.posts:
        if not post.text or not post.text.strip():
            continue

        bot_score = _estimate_bot_score(post)

        normalized_posts.append(IncomingPost(
            event_id=f"tiktok_{post.post_id}_{int(time.time())}",
            case_id=state["case_id"],
            source="tiktok",
            post_id=post.post_id,
            normalized_text=post.text,
            detected_language="unknown",
            bot_score=bot_score,
            is_duplicate=False,
            author_id=post.author_id,
            engagement_score=post.engagement_score,
            posted_at=None,
            media=[{"type": "thumbnail", "url": post.thumbnail_url}] if post.thumbnail_url else [],
        ))

    trace = _make_trace(
        agent="tiktok_ingestor",
        input_summary=f"raw_posts={len(last_search.posts)}",
        decision=f"normalized={len(normalized_posts)} posts",
        reasoning="Converted platform-specific TikTok data to internal NormalizedPost format.",
    )

    return {
        "tiktok_normalized_posts_this_run": normalized_posts,
        "agent_trace": [trace],
    }


def _estimate_bot_score(post) -> float:
    """Bot heuristic used across ingestion and selection."""
    score = 0.0
    followers = getattr(post, "author_followers", 0) or 0
    plays = getattr(post, "plays", 0) or 0
    if followers < 50 and plays > 100_000:
        score += 0.5
    elif followers < 200 and plays > 500_000:
        score += 0.3
    return min(score, 1.0)


# ── Node: video_selector ──────────────────────────────────────────────────────

async def video_selector_node(state: CaseState) -> dict:
    """
    Queues high-signal videos for multimodal analysis.
    """
    tiktok_posts = state.get("tiktok_posts", [])
    already_analyzed = set(state.get("analyzed_post_ids", []))
 
    queue = []
    for post in tiktok_posts:
        video_url = getattr(post, "video_url", None) or getattr(post, "url", None)
        if not video_url or post.post_id in already_analyzed:
            continue
 
        if post.plays >= VIDEO_ANALYSIS_MIN_PLAYS or post.shares >= VIDEO_ANALYSIS_MIN_SHARES:
            if _estimate_bot_score(post) < BOT_SCORE_MAX:
                queue.append({
                    "post_id": post.post_id,
                    "video_url": video_url,
                    "engagement_score": post.engagement_score,
                })
 
        if len(queue) >= MAX_VIDEOS_PER_RUN:
            break
 
    queue.sort(key=lambda x: x["engagement_score"], reverse=True)
 
    trace = _make_trace(
        agent="video_selector",
        input_summary=f"posts_checked={len(tiktok_posts)}",
        decision=f"queued={len(queue)} videos",
        reasoning="Selected high-engagement videos from credible accounts for Gemini analysis.",
    )
 
    return {
        "video_analysis_queue": queue,
        "needs_video_analysis": len(queue) > 0,
        "agent_trace": [trace],
    }


# ── Node: video_analysis ──────────────────────────────────────────────────────

async def video_analysis_node(state: CaseState) -> dict:
    """
    Sequential analysis of queued videos using Gemini 1.5.
    """
    queue = state.get("video_analysis_queue", [])
    subject_desc = state.get("subject_description", "")
    case_id = state["case_id"]
 
    if not queue or not subject_desc:
        return {"agent_trace": [_make_trace("video_analysis", "missing data", "skipped", "Queue or description empty")]}
 
    results: list[VideoSignals] = []
    new_ids: list[str] = []
    video_claims: list[ExtractedClaim] = []
 
    for item in queue:
        signals: VideoSignals = await analyze_video.ainvoke({
            "post_id": item["post_id"],
            "video_url": item["video_url"],
            "case_id": case_id,
            "subject_description": subject_desc,
        })
        results.append(signals)
        new_ids.append(item["post_id"])
 
        if signals.case_relevant:
            for claim in signals.spoken_claims:
                video_claims.append(ExtractedClaim(
                    claim_id=f"vid_clm_{uuid.uuid4().hex[:8]}",
                    source_event_id=f"tiktok_{item['post_id']}",
                    case_id=case_id,
                    type=claim.claim_type,
                    statement=claim.quote,
                    location_mentioned=None,
                    time_mentioned=None,
                    extraction_confidence=claim.confidence,
                    embedding_vector=[],
                    video_post_id=item["post_id"]
                ))

    trace = _make_trace(
        agent="video_analysis",
        input_summary=f"analyzed={len(results)}",
        decision=f"extracted={len(video_claims)} video-claims",
        reasoning="Multimodal analysis completed. Extracted sightings and location signals from video/audio.",
    )
 
    return {
        "video_analyses": results,
        "analyzed_post_ids": new_ids,
        "all_claims": video_claims,
        "extracted_claims_this_run": video_claims,
        "agent_trace": [trace],
    }


# ── Node: claim_extractor ─────────────────────────────────────────────────────

async def claim_extractor_node(state: CaseState) -> dict:
    """
    Extracts structured claims from normalized text posts.
    """
    posts = state.get("tiktok_normalized_posts_this_run", [])
    if state.get("incoming_post"):
        posts.append(state.get("incoming_post"))

    claims: list[ExtractedClaim] = []
    # TODO: Implement real LLM extraction with prompts.CLAIM_EXTRACTION_PROMPT
    for post in posts:
        claims.append(ExtractedClaim(
            claim_id=f"txt_clm_{uuid.uuid4().hex[:8]}",
            source_event_id=post.get("event_id", ""),
            case_id=state["case_id"],
            type="sighting",
            statement=post.get("normalized_text", "")[:200],
            location_mentioned=None,
            time_mentioned=None,
            extraction_confidence=0.6,
            embedding_vector=[],
            video_post_id=None
        ))

    trace = _make_trace(
        agent="claim_extractor",
        input_summary=f"posts={len(posts)}",
        decision=f"extracted={len(claims)} text-claims",
        reasoning="Extracted potential sightings and leads from post captions and descriptions.",
    )

    return {
        "all_claims": claims,
        "extracted_claims_this_run": claims,
        "agent_trace": [trace],
    }


# ── Stubs for future implementation ───────────────────────────────────────────

async def clustering_node(state: CaseState) -> dict:
    return {"agent_trace": [_make_trace("clustering", "stub", "skipped", "Next sprint")]}

async def scoring_node(state: CaseState) -> dict:
    return {"agent_trace": [_make_trace("scoring", "stub", "skipped", "Next sprint")]}

async def verification_node(state: CaseState) -> dict:
    return {"agent_trace": [_make_trace("verifier", "stub", "skipped", "Next sprint")]}

async def misinfo_filter_node(state: CaseState) -> dict:
    return {"agent_trace": [_make_trace("misinfo_filter", "stub", "skipped", "Next sprint")]}

async def lead_generator_node(state: CaseState) -> dict:
    return {"agent_trace": [_make_trace("lead_generator", "stub", "skipped", "Next sprint")]}

async def graph_updater_node(state: CaseState) -> dict:
    return {"agent_trace": [_make_trace("graph_updater", "stub", "skipped", "Next sprint")]}

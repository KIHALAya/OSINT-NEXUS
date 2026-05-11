"""
agent/nodes.py

All node implementations for the OSINT-NEXUS investigation graph.

Previously stubbed nodes now fully implemented:
  - claim_extractor_node   LLM extracts structured claims + generates embeddings
  - clustering_node        Qdrant similarity search → assigns/creates clusters
  - scoring_node           Computes crowd_score per cluster
  - graph_updater_node     Persists everything to PostgreSQL

Nodes that were already implemented remain unchanged:
  - bootstrap_node
  - tiktok_search_node
  - tiktok_ingestor_node
  - video_selector_node
  - video_analysis_node
  - lead_generator_node
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from agent.state import (
    AgentStep, CaseState, ClusterState, ExtractedClaim,
    IncomingPost, LeadState,
)
from core.config import get_settings
from db.database import get_db_ctx
from db.models import Case, ExtractedClaimModel, Lead, RawPost
from tools.embeddings import (
    embed_text,
    ensure_collection,
    find_similar_claims,
    upsert_claim,
)
from tools.local_llm import call_local_llm_json
from tools.tiktok_search import search_tiktok
from tools.video_analysis import analyze_video

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_trace(
    agent: str, input_summary: str, decision: str, reasoning: str
) -> AgentStep:
    return AgentStep(
        agent=agent,
        input_summary=input_summary,
        decision=decision,
        reasoning=reasoning,
        timestamp=int(time.time() * 1000),
    )


def _claim_id() -> str:
    return f"clm_{uuid.uuid4().hex[:12]}"


def _cluster_id() -> str:
    return f"clust_{uuid.uuid4().hex[:10]}"


def _lead_id() -> str:
    return f"lead_{uuid.uuid4().hex[:10]}"


# ── Node 1: bootstrap ─────────────────────────────────────────────────────────

async def bootstrap_node(state: CaseState) -> dict:
    """
    Entry point for every run. Uses Gemma 4 to generate search keywords.
    Per architecture doc: every run begins with data acquisition.
    """
    subject = state["subject_name"]
    description = state.get("subject_description", "")

    # ── Keyword Generation via Gemma 4 ───────────────────────────────────────
    prompt = f"""
    You are an OSINT expert. Generate 5 highly effective search keywords/phrases 
    for finding social media posts (TikTok/Twitter/Reddit) about this missing person.
    
    Subject Name: {subject}
    Description: {description}
    
    Include:
    - Variations of the name
    - The specific city, state, and region in the US
    - US-specific missing person hashtags (#MissingPerson, #SilverAlert, #AmberAlert)
    - Search terms local communities in that US area might use
    
    Return ONLY JSON: {{"keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"]}}
    """
    
    try:
        res = await call_local_llm_json(prompt, system_prompt="You are a US-based OSINT investigator.")
        keywords = res.get("keywords", [subject])
    except Exception as e:
        logger.warning(f"Gemma keyword generation failed, using fallback: {e}")
        keywords = [subject]

    # Clean keywords (strip # and @)
    keywords = [k.replace("#", "").replace("@", "").strip() for k in keywords if k]
    keywords = list(dict.fromkeys(keywords))[:5]

    trace = _make_trace(
        agent="bootstrap",
        input_summary=f"case={state['case_id']} subject={subject}",
        decision=f"generated_keywords={keywords}",
        reasoning="Gemma 4 generated context-aware search terms for multi-platform ingestion",
    )
    
    return {
        "needs_tiktok_search": True,
        "current_search_keywords": keywords,
        "agent_trace": [trace],
    }


# ── Node 2: tiktok_search ─────────────────────────────────────────────────────

async def tiktok_search_node(state: CaseState) -> dict:
    """Calls Apify TikTok scraper using generated keywords."""
    case_id = state["case_id"]
    keywords = state.get("current_search_keywords", [state["subject_name"]])

    logger.info(f"[tiktok_search] case={case_id} keywords={keywords}")

    try:
        raw_result = await search_tiktok.ainvoke({
            "case_id": case_id,
            "keywords": keywords,
            "max_results": 100,
        })
        result = raw_result.model_dump()
        decision = f"found={result.get('total_found', 0)} posts"
        reasoning = f"Apify search completed for keywords: {keywords}. Found {result.get('total_found', 0)} potential leads."
    except Exception as e:
        logger.error(f"TikTok search node failed: {e}")
        decision = "failed"
        reasoning = f"Search error: {str(e)}"
        result = None

    trace = _make_trace(
        agent="tiktok_search",
        input_summary=f"keywords={keywords}",
        decision=decision,
        reasoning=reasoning,
    )

    return {
        "last_tiktok_result": result,
        "agent_trace": [trace],
    }


# ── Node 3: tiktok_ingestor ───────────────────────────────────────────────────

async def tiktok_ingestor_node(state: CaseState) -> dict:
    """Converts raw dict posts → platform-agnostic IncomingPost objects."""
    result = state.get("last_tiktok_result")
    if not result or not result.get("posts"):
        return {"current_posts": [], "agent_trace": [_make_trace(
            "tiktok_ingestor", "no posts", "skipped", "No TikTok results to ingest"
        )]}

    case_id = state["case_id"]
    posts: list[IncomingPost] = []

    raw_posts = result.get("posts", [])
    for p in raw_posts:
        text = p.get("text", "")
        if not text or not text.strip():
            continue

        bot_score = 0.0
        followers = p.get("author_followers", 0)
        plays = p.get("plays", 0)
        if followers < 50 and plays > 100_000:
            bot_score = 0.5
        elif followers < 200 and plays > 500_000:
            bot_score = 0.35
        if p.get("author_verified"):
            bot_score = max(0.0, bot_score - 0.2)

        posts.append(IncomingPost(
            event_id=f"tiktok_{p.get('post_id')}_{int(time.time())}",
            case_id=case_id,
            source="tiktok",
            post_id=p.get("post_id", ""),
            normalized_text=text,
            detected_language="unknown",
            bot_score=bot_score,
            is_duplicate=False,
            author_id=p.get("author_id", ""),
            author_name=p.get("author_name", ""),
            author_followers=followers,
            author_verified=bool(p.get("author_verified")),
            engagement_score=p.get("engagement_score", 0.0),
            likes=p.get("likes", 0),
            shares=p.get("shares", 0),
            plays=plays,
            posted_at=p.get("posted_at"),
            video_url=p.get("video_download_url") or p.get("url"),
            thumbnail_url=p.get("thumbnail_url"),
            hashtags=p.get("hashtags", []),
            media=[],
        ))

    # Sort by engagement score descending to prioritize high-signal content
    posts.sort(key=lambda x: x["engagement_score"], reverse=True)

    trace = _make_trace(
        agent="tiktok_ingestor",
        input_summary=f"raw={len(raw_posts)}",
        decision=f"normalized={len(posts)}",
        reasoning=f"Dropped {len(raw_posts) - len(posts)} empty posts",
    )

    return {
        "current_posts": posts,
        "all_posts": posts,         # operator.add accumulates
        "agent_trace": [trace],
    }


# ── Node 4: video_selector ────────────────────────────────────────────────────

async def video_selector_node(state: CaseState) -> dict:
    """Selects high-signal posts for video analysis using Gemma triage."""
    posts = state.get("current_posts", [])
    already_done = set(state.get("analyzed_post_ids", []))
    subject_desc = state.get("subject_description", "")
    settings = get_settings()

    eligible = [p for p in posts if p["post_id"] not in already_done and p.get("video_url") and p["bot_score"] < 0.5]
    
    if not eligible:
        return {"video_analysis_queue": [], "needs_video_analysis": False, "agent_trace": [_make_trace("video_selector", "no eligible posts", "skipped", "")]}

    # ── Investigative Triage via Gemma 4 ─────────────────────────────────────
    # Pass captions to Gemma to pick the most relevant ones
    candidates = []
    for p in eligible:
        candidates.append({
            "id": p["post_id"],
            "text": p["normalized_text"][:200],
            "plays": p["plays"]
        })

    prompt = f"""
    You are an OSINT triage officer. Review these TikTok post captions and select the 
    top {settings.VIDEO_MAX_PER_RUN} posts that are most likely to contain 
    real investigative signals about the missing person: "{subject_desc}".
    
    Priority: 
    1. Direct sighting claims ("I saw her at...")
    2. Specific location mentions
    3. New information not in the description
    
    Posts:
    {json.dumps(candidates, indent=2)}
    
    Return ONLY JSON: {{"selected_ids": ["id1", "id2", ...]}}
    """

    try:
        res = await call_local_llm_json(prompt, system_prompt="You are an expert OSINT triage agent.")
        selected_ids = res.get("selected_ids", [])
    except Exception as e:
        logger.warning(f"Gemma triage failed, falling back to engagement sort: {e}")
        selected_ids = [p["id"] for p in sorted(candidates, key=lambda x: x["plays"], reverse=True)[:settings.VIDEO_MAX_PER_RUN]]

    # Build queue from selected IDs
    queue = []
    id_to_post = {p["post_id"]: p for p in eligible}
    for sid in selected_ids:
        if sid in id_to_post:
            p = id_to_post[sid]
            queue.append({
                "post_id": p["post_id"],
                "video_url": p["video_url"],
                "engagement_score": p["engagement_score"],
            })

    trace = _make_trace(
        agent="video_selector",
        input_summary=f"eligible={len(eligible)} candidates={len(candidates)}",
        decision=f"queued={len(queue)}",
        reasoning=f"Gemma 4 triage: selected based on investigative relevance to subject description",
    )

    return {
        "video_analysis_queue": queue,
        "needs_video_analysis": len(queue) > 0,
        "agent_trace": [trace],
    }


# ── Node 5: video_analysis ────────────────────────────────────────────────────

async def video_analysis_node(state: CaseState) -> dict:
    """Calls Gemini 1.5 Flash in parallel for each queued video."""
    queue = state.get("video_analysis_queue", [])
    subject_desc = state.get("subject_description", "")
    case_id = state["case_id"]

    if not queue:
        return {"agent_trace": [_make_trace("video_analysis", "empty", "skipped", "")]}

    tasks = [
        analyze_video.ainvoke({
            "post_id": item["post_id"],
            "video_url": item["video_url"],
            "case_id": case_id,
            "subject_description": subject_desc,
        })
        for item in queue
    ]
    
    analysis_results = await asyncio.gather(*tasks)
    
    results = [r.model_dump() for r in analysis_results]
    new_ids = [item["post_id"] for item in queue]

    trace = _make_trace(
        agent="video_analysis",
        input_summary=f"queued={len(queue)}",
        decision=f"analyzed={len(results)} relevant={sum(1 for r in results if r.get('case_relevant'))}",
        reasoning=f"Parallelized Gemini calls ({len(tasks)} concurrent tasks) for performance optimization",
    )

    return {
        "video_analyses_this_run": results,
        "analyzed_post_ids": new_ids,
        "agent_trace": [trace],
    }


# ── Node 6: claim_extractor — THE KEY NODE ───────────────────────────────────

CLAIM_EXTRACTION_PROMPT = """\
You are an AI assistant for a US-based missing persons investigation.
Extract ALL claims from the following content that relate to sightings, locations, or information about the missing person.

Missing person: {subject_description}

Content to analyze:
---
{content}
---

Return ONLY valid JSON — no markdown, no explanation:
{{
  "claims": [
    {{
      "claim_type": "sighting|location|rumour|denial",
      "statement": "clear, concise statement of what was claimed",
      "location_mentioned": "specific location or null",
      "time_mentioned": "time reference or null",
      "language": "en|es|mixed",
      "confidence": 0.0
    }}
  ]
}}

Rules:
- Only extract claims directly relevant to the missing person
- If nothing relevant, return {{"claims": []}}
- confidence: 0.3=weak hint, 0.6=possible claim, 0.8=explicit claim, 1.0=certain
- Preserve the original language in the statement field
"""


async def claim_extractor_node(state: CaseState) -> dict:
    """
    Extracts structured claims from:
      1. Text posts (current_posts normalized_text)
      2. Video analysis spoken claims + location signals (video_analyses_this_run)
    """
    case_id = state["case_id"]
    subject_desc = state.get("subject_description", "")
    posts = state.get("current_posts", [])
    video_analyses = state.get("video_analyses_this_run", [])

    if not posts and not video_analyses:
        return {
            "current_claims": [],
            "agent_trace": [_make_trace("claim_extractor", "no posts or video analyses", "skipped", "No data to extract claims from")]
        }

    # ── Path A: extract from text posts (Parallelized) ────────────────────────
    tasks = []
    active_posts = []
    for post in posts:
        text = post.get("normalized_text", "").strip()
        if not text or len(text) < 10:
            continue
        active_posts.append(post)
        tasks.append(_llm_extract_claims(text, subject_desc, ""))

    results_lists = []
    if tasks:
        results_lists = await asyncio.gather(*tasks)
    
    all_new_claims: list[ExtractedClaim] = []
    for post, raw_claims in zip(active_posts, results_lists):
        for raw in raw_claims:
            statement = raw.get("statement", "").strip()
            if not statement: continue
            
            try: vector = await embed_text(statement)
            except: vector = []

            all_new_claims.append(ExtractedClaim(
                claim_id=_claim_id(),
                source_event_id=post["event_id"],
                case_id=case_id,
                claim_type=raw.get("claim_type", "rumour"),
                statement=statement,
                location_mentioned=raw.get("location_mentioned"),
                time_mentioned=raw.get("time_mentioned"),
                extraction_confidence=float(raw.get("confidence", 0.5)),
                language=raw.get("language", "unknown"),
                embedding_vector=vector,
                from_video=False,
            ))

    # ── Path B: lift claims from video analysis ───────────────────────────────
    for analysis in video_analyses:
        if analysis.get("processing_error"): continue
        post_id = analysis.get("post_id", "")

        for spoken in analysis.get("spoken_claims", []):
            statement = spoken.get("quote", "").strip()
            if not statement: continue
            try: vector = await embed_text(statement)
            except: vector = []

            all_new_claims.append(ExtractedClaim(
                claim_id=_claim_id(),
                source_event_id=f"tiktok_{post_id}",
                case_id=case_id,
                claim_type=spoken.get("claim_type", "sighting"),
                statement=statement,
                extraction_confidence=float(spoken.get("confidence", 0.5)),
                language=spoken.get("language", "unknown"),
                embedding_vector=vector,
                from_video=True,
                video_post_id=post_id,
            ))

    trace = _make_trace(
        agent="claim_extractor",
        input_summary=f"posts={len(active_posts)} videos={len(video_analyses)}",
        decision=f"extracted={len(all_new_claims)} claims",
        reasoning=f"Processed {len(active_posts)} text posts and {len(video_analyses)} video analyses. Found {len(all_new_claims)} investigative claims.",
    )

    return {
        "current_claims": all_new_claims,
        "all_claims": all_new_claims,
        "agent_trace": [trace],
    }


async def _llm_extract_claims(
    content: str,
    subject_description: str,
    api_key: str,
) -> list[dict]:
    """Call local Gemma 4 to extract structured claims from text content."""
    prompt = CLAIM_EXTRACTION_PROMPT.format(
        subject_description=subject_description,
        content=content[:3000],
    )

    try:
        parsed = await call_local_llm_json(prompt, system_prompt="You are an expert US OSINT investigator.")
        return parsed.get("claims", [])
    except Exception as e:
        logger.error(f"Gemma claim extraction failed: {e}")
        return []


# ── Node 7: clustering ────────────────────────────────────────────────────────

async def clustering_node(state: CaseState) -> dict:
    """
    Groups new claims into clusters using Qdrant similarity search.
    Cosine similarity > 0.78 for US-based location matching accuracy.
    """
    case_id = state["case_id"]
    new_claims = state.get("current_claims", [])

    if not new_claims:
        return {"current_clusters": [], "agent_trace": [_make_trace(
            "clustering", "no claims", "skipped", "No new claims to cluster"
        )]}

    await ensure_collection(case_id)

    # Build mutable cluster map from existing clusters
    cluster_map: dict[str, ClusterState] = {c["cluster_id"]: c for c in state.get("all_clusters", [])}
    point_to_cluster: dict[str, str] = {}
    for c in cluster_map.values():
        for pid in c.get("_point_ids", []):
            point_to_cluster[pid] = c["cluster_id"]

    claims_with_qdrant: list[ExtractedClaim] = []

    for claim in new_claims:
        vector = claim.get("embedding_vector", [])
        if not vector or all(v == 0.0 for v in vector):
            claims_with_qdrant.append(claim)
            continue

        point_id = await upsert_claim(
            case_id=case_id,
            claim_id=claim["claim_id"],
            vector=vector,
            payload={
                "claim_type": claim["claim_type"],
                "statement": claim["statement"],
                "location_mentioned": claim.get("location_mentioned"),
                "source_event_id": claim["source_event_id"],
            },
        )

        updated_claim = {**claim, "qdrant_point_id": point_id}
        claims_with_qdrant.append(updated_claim)

        similar = await find_similar_claims(case_id=case_id, vector=vector, limit=5)
        similar = [s for s in similar if s.id != point_id]

        assigned_cluster_id = None
        if similar:
            top_match_point_id = str(similar[0].id)
            assigned_cluster_id = point_to_cluster.get(top_match_point_id)

        if assigned_cluster_id and assigned_cluster_id in cluster_map:
            cluster = cluster_map[assigned_cluster_id]
            cluster["claim_ids"].append(claim["claim_id"])
            cluster.setdefault("_point_ids", []).append(point_id)
        else:
            new_cluster_id = _cluster_id()
            new_cluster = ClusterState(
                cluster_id=new_cluster_id,
                label=claim["statement"][:80],
                claim_ids=[claim["claim_id"]],
                platform_breakdown={"tiktok": 1 if "tiktok" in claim["source_event_id"] else 0},
                crowd_score=0.0,
                final_score=0.0,
                status="low",
            )
            new_cluster["_point_ids"] = [point_id]
            cluster_map[new_cluster_id] = new_cluster
            point_to_cluster[point_id] = new_cluster_id

    updated_clusters = [
        v for v in cluster_map.values()
        if any(cid in v["claim_ids"] for cid in [c["claim_id"] for c in new_claims])
    ]

    return {
        "current_claims": claims_with_qdrant,
        "current_clusters": updated_clusters,
        "all_clusters": list(cluster_map.values()),
        "agent_trace": [_make_trace("clustering", f"new={len(new_claims)}", f"updated={len(updated_clusters)}", "")]
    }


# ── Node 8: scoring ───────────────────────────────────────────────────────────

async def scoring_node(state: CaseState) -> dict:
    """
    Computes crowd_score for each cluster updated this run.
    """
    clusters = state.get("current_clusters", [])
    all_claims = state.get("all_claims", [])
    all_posts = state.get("all_posts", [])

    post_by_event_id = {p["event_id"]: p for p in all_posts}
    claim_by_id = {c["claim_id"]: c for c in all_claims}

    scored_clusters = []
    high_signal = []

    for cluster in clusters:
        claim_ids = cluster.get("claim_ids", [])
        if not claim_ids: continue

        source_events = set()
        bot_scores = []
        for cid in claim_ids:
            claim = claim_by_id.get(cid)
            if not claim: continue
            source_events.add(claim["source_event_id"])
            if post := post_by_event_id.get(claim["source_event_id"]):
                bot_scores.append(post.get("bot_score", 0.0))

        freq = min(len(claim_ids) / 20.0, 1.0)
        div = min(len(source_events) / 5.0, 1.0)
        bot = sum(bot_scores) / len(bot_scores) if bot_scores else 0.0
        
        score = round((freq * 0.4) + (div * 0.4) - (bot * 0.2) + 0.1, 3)
        score = max(0.0, min(1.0, score))

        scored = {**cluster, "crowd_score": score, "final_score": score, "status": "high-signal" if score >= 0.6 else "medium" if score >= 0.35 else "low"}
        scored_clusters.append(scored)
        if score >= 0.6: high_signal.append(cluster["cluster_id"])

    return {
        "current_clusters": scored_clusters,
        "needs_verification": high_signal,
        "agent_trace": [_make_trace("scoring", f"scored={len(scored_clusters)}", f"high={len(high_signal)}", "")]
    }


# ── Node 9: lead_generator ────────────────────────────────────────────────────

async def lead_generator_node(state: CaseState) -> dict:
    """
    Generates Lead objects from high-signal clusters.
    """
    clusters = state.get("current_clusters", [])
    all_claims = state.get("all_claims", [])
    claim_by_id = {c["claim_id"]: c for c in all_claims}

    new_leads = []
    existing_cluster_ids = {l["cluster_id"] for l in state.get("all_leads", [])}

    for cluster in clusters:
        if cluster["final_score"] < 0.5 or cluster["cluster_id"] in existing_cluster_ids:
            continue

        unique_sources = {claim_by_id[cid]["source_event_id"] for cid in cluster["claim_ids"] if cid in claim_by_id}
        
        lead = LeadState(
            lead_id=_lead_id(),
            cluster_id=cluster["cluster_id"],
            title=cluster["label"][:100],
            confidence=cluster["final_score"],
            crowd_score=cluster["crowd_score"],
            final_score=cluster["final_score"],
            claim_count=len(cluster["claim_ids"]),
            unique_sources=len(unique_sources),
            evidence=[claim_by_id[cid]["statement"] for cid in cluster["claim_ids"][:5] if cid in claim_by_id],
            action_required=_suggest_action(cluster),
            priority="urgent" if cluster["final_score"] >= 0.8 else "high" if cluster["final_score"] >= 0.65 else "medium",
        )
        new_leads.append(lead)

    all_leads = list(state.get("all_leads", []))
    all_leads.extend(new_leads)

    return {
        "current_leads": new_leads,
        "all_leads": all_leads,
        "agent_trace": [_make_trace("lead_generator", f"new={len(new_leads)}", "leads generated", "")]
    }


def _suggest_action(cluster: ClusterState) -> str:
    label_lower = cluster["label"].lower()
    if "mall" in label_lower:
        return "Request CCTV footage from mall security for the specified time window"
    if "station" in label_lower or "train" in label_lower:
        return "Contact transit police to review station surveillance and ticketing logs"
    if "beach" in label_lower or "park" in label_lower:
        return "Coordinate with local US Park Police or local law enforcement for area sweep"
    return f"Investigate cluster '{cluster['label'][:60]}' — cross-reference with local reports"


# ── Node 10: graph_updater — DB WRITE NODE ───────────────────────────────────

async def graph_updater_node(state: CaseState) -> dict:
    """
    Persists results and prunes transient state to prevent bloat.
    Uses batch insertion (upsert) for performance.
    """
    case_id = state["case_id"]
    posts = state.get("current_posts", [])
    claims = state.get("current_claims", [])
    leads = state.get("current_leads", [])

    try:
        async with get_db_ctx() as db:
            # 1. Batch insert Posts
            if posts:
                post_values = []
                for p in posts:
                    post_values.append({
                        "id": p["event_id"],
                        "case_id": case_id,
                        "source": p["source"],
                        "post_id": p["post_id"],
                        "normalized_text": p["normalized_text"],
                        "detected_language": p.get("detected_language", "unknown"),
                        "bot_score": p.get("bot_score", 0.0),
                        "is_duplicate": p.get("is_duplicate", False),
                        "engagement_score": p.get("engagement_score", 0.0),
                        "author_id": p.get("author_id"),
                        "author_name": p.get("author_name", ""),
                        "author_followers": p.get("author_followers", 0),
                        "author_verified": p.get("author_verified", False),
                        "likes": p.get("likes", 0),
                        "shares": p.get("shares", 0),
                        "plays": p.get("plays", 0),
                        "posted_at": p.get("posted_at"),
                        "video_url": p.get("video_url"),
                        "thumbnail_url": p.get("thumbnail_url"),
                        "hashtags": p.get("hashtags", []),
                    })
                stmt = insert(RawPost).values(post_values)
                stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                await db.execute(stmt)

            # 2. Batch insert Claims
            if claims:
                claim_values = []
                for c in claims:
                    claim_values.append({
                        "id": c["claim_id"],
                        "case_id": case_id,
                        "source_post_id": c["source_event_id"],
                        "claim_type": c["claim_type"],
                        "statement": c["statement"],
                        "location_mentioned": c.get("location_mentioned"),
                        "time_mentioned": c.get("time_mentioned"),
                        "extraction_confidence": c.get("extraction_confidence", 0.0),
                        "language": c.get("language", "unknown"),
                        "qdrant_point_id": c.get("qdrant_point_id"),
                        "from_video": c.get("from_video", False),
                        "video_post_id": c.get("video_post_id"),
                    })
                stmt = insert(ExtractedClaimModel).values(claim_values)
                stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                await db.execute(stmt)

            # 3. Batch insert Leads
            if leads:
                lead_values = []
                for l in leads:
                    lead_values.append({
                        "id": l["lead_id"],
                        "case_id": case_id,
                        "cluster_id": l["cluster_id"],
                        "title": l["title"],
                        "confidence": l["confidence"],
                        "crowd_score": l.get("crowd_score", 0.0),
                        "final_score": l.get("final_score", 0.0),
                        "claim_count": l.get("claim_count", 0),
                        "unique_sources": l.get("unique_sources", 0),
                        "evidence": l.get("evidence", []),
                        "action_required": l.get("action_required"),
                        "priority": l.get("priority", "medium"),
                    })
                stmt = insert(Lead).values(lead_values)
                stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                await db.execute(stmt)

            await db.commit()

        # Prune state
        return {
            "current_posts": [],
            "current_claims": [],
            "current_leads": [],
            "video_analyses_this_run": [],
            "agent_trace": [_make_trace(
                "graph_updater", 
                f"p={len(posts)} c={len(claims)} l={len(leads)}", 
                "Batch persist successful", 
                "Transient lists cleared"
            )]
        }

    except Exception as e:
        logger.error(f"DB batch write failed: {e}", exc_info=True)
        return {"agent_trace": [_make_trace("graph_updater", "error", str(e)[:50], "Batch persist failed")]}
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
    STATION 1: bootstrap_node
    Deterministic hashtag-first bootstrap. No LLM query generation.
    """
    case_id = state["case_id"]
    subject = state["subject_name"]

    logger.info(f"[STATION 1: bootstrap] Starting deterministic bootstrap for case={case_id} subject={subject}")

    # ── Deterministic Normalization ──────────────────────────────────────────
    # Exact Name
    search_queries = [subject]

    # Normalized Hashtag
    # lowercase, remove spaces, remove punctuation
    normalized_tag = "".join(e for e in subject.lower() if e.isalnum())
    hashtags = [normalized_tag]

    logger.info(f"[STATION 1: bootstrap] Generated search_queries={search_queries}, hashtags={hashtags}")

    trace = _make_trace(
        agent="bootstrap",
        input_summary=f"case={case_id} subject={subject}",
        decision=f"queries={search_queries} hashtags={hashtags}",
        reasoning="Deterministic hashtag-first bootstrap (normalized name) for high-relevance investigation",
    )
    
    return {
        "needs_tiktok_search": True,
        "current_search_queries": search_queries,
        "current_hashtags": hashtags,
        "agent_trace": [trace],
    }


# ── Node 2: tiktok_search ─────────────────────────────────────────────────────

async def tiktok_search_node(state: CaseState) -> dict:
    """STATION 2: tiktok_search_node - Calls Apify TikTok scraper."""
    case_id = state["case_id"]
    search_queries = state.get("current_search_queries", [state["subject_name"]])
    hashtags = state.get("current_hashtags", [])

    logger.info(f"[STATION 2: tiktok_search] Triggering Apify for case={case_id} queries={search_queries} hashtags={hashtags}")

    try:
        raw_result = await search_tiktok.ainvoke({
            "case_id": case_id,
            "search_queries": search_queries,
            "hashtags": hashtags,
            "max_results": 100,
        })
        result = raw_result.model_dump()
        count = result.get('total_found', 0)
        logger.info(f"[STATION 2: tiktok_search] Search completed. Found {count} posts.")
        decision = f"found={count} posts"
        reasoning = f"Apify search completed for queries={search_queries} hashtags={hashtags}. Found {count} posts."
    except Exception as e:
        logger.error(f"[STATION 2: tiktok_search] Node failed: {e}")
        decision = "failed"
        reasoning = f"Search error: {str(e)}"
        result = None

    trace = _make_trace(
        agent="tiktok_search",
        input_summary=f"queries={search_queries} hashtags={hashtags}",
        decision=decision,
        reasoning=reasoning,
    )

    return {
        "last_tiktok_result": result,
        "agent_trace": [trace],
    }


# ── Node 3: tiktok_ingestor ───────────────────────────────────────────────────

async def tiktok_ingestor_node(state: CaseState) -> dict:
    """STATION 3: tiktok_ingestor_node - Normalizes raw dict posts."""
    result = state.get("last_tiktok_result")
    if not result or not result.get("posts"):
        logger.warning(f"[STATION 3: tiktok_ingestor] No results to ingest for case={state['case_id']}")
        return {"current_posts": [], "agent_trace": [_make_trace(
            "tiktok_ingestor", "no posts", "skipped", "No TikTok results to ingest"
        )]}

    case_id = state["case_id"]
    posts: list[IncomingPost] = []
    raw_posts = result.get("posts", [])
    
    logger.info(f"[STATION 3: tiktok_ingestor] Normalizing {len(raw_posts)} raw posts")

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

    # Sort by engagement score descending
    posts.sort(key=lambda x: x["engagement_score"], reverse=True)
    
    logger.info(f"[STATION 3: tiktok_ingestor] Successfully ingested {len(posts)} posts (dropped {len(raw_posts) - len(posts)} empty)")

    trace = _make_trace(
        agent="tiktok_ingestor",
        input_summary=f"raw={len(raw_posts)}",
        decision=f"normalized={len(posts)}",
        reasoning=f"Dropped {len(raw_posts) - len(posts)} empty posts",
    )

    return {
        "current_posts": posts,
        "all_posts": posts,
        "agent_trace": [trace],
    }


# ── Node 4: video_selector ────────────────────────────────────────────────────

async def video_selector_node(state: CaseState) -> dict:
    """STATION 4: video_selector_node - Triage high-signal posts."""
    posts = state.get("current_posts", [])
    case_id = state["case_id"]
    already_done = set(state.get("analyzed_post_ids", []))
    subject_desc = state.get("subject_description", "")
    settings = get_settings()

    eligible = [p for p in posts if p["post_id"] not in already_done and p.get("video_url") and p["bot_score"] < 0.5]
    
    logger.info(f"[STATION 4: video_selector] Reviewing {len(eligible)} eligible posts for video analysis")

    if not eligible:
        logger.info(f"[STATION 4: video_selector] No eligible posts found for analysis")
        return {"video_analysis_queue": [], "needs_video_analysis": False, "agent_trace": [_make_trace("video_selector", "no eligible posts", "skipped", "")]}

    # ── Investigative Triage via Gemma 4 ─────────────────────────────────────
    candidates = [{"id": p["post_id"], "text": p["normalized_text"][:200], "plays": p["plays"]} for p in eligible]

    prompt = f"""
    You are an OSINT triage officer. Review these TikTok post captions and select the 
    top {settings.VIDEO_MAX_PER_RUN} posts that are most likely to contain 
    real investigative signals about the missing person: "{subject_desc}".
    
    Priority: 1. Sighting claims, 2. Locations, 3. Novel info.
    Posts: {json.dumps(candidates, indent=2)}
    Return ONLY JSON: {{"selected_ids": ["id1", "id2", ...]}}
    """

    try:
        res = await call_local_llm_json(prompt, system_prompt="You are an expert OSINT triage agent.")
        selected_ids = res.get("selected_ids", [])
        logger.info(f"[STATION 4: video_selector] Gemma selected {len(selected_ids)} IDs for deep analysis")
    except Exception as e:
        logger.warning(f"[STATION 4: video_selector] Gemma triage failed, falling back to engagement: {e}")
        selected_ids = [p["id"] for p in sorted(candidates, key=lambda x: x["plays"], reverse=True)[:settings.VIDEO_MAX_PER_RUN]]

    queue = []
    id_to_post = {p["post_id"]: p for p in eligible}
    for sid in selected_ids:
        if sid in id_to_post:
            p = id_to_post[sid]
            queue.append({"post_id": p["post_id"], "video_url": p["video_url"], "engagement_score": p["engagement_score"]})

    logger.info(f"[STATION 4: video_selector] Final queue size: {len(queue)}")

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
    """STATION 5: video_analysis_node - Parallel Gemini 1.5 Flash calls."""
    queue = state.get("video_analysis_queue", [])
    case_id = state["case_id"]

    if not queue:
        logger.info(f"[STATION 5: video_analysis] Queue empty, skipping")
        return {"agent_trace": [_make_trace("video_analysis", "empty", "skipped", "")]}

    logger.info(f"[STATION 5: video_analysis] Analyzing {len(queue)} videos in parallel via Gemini 1.5 Flash")

    tasks = [
        analyze_video.ainvoke({
            "post_id": item["post_id"],
            "video_url": item["video_url"],
            "case_id": case_id,
            "subject_description": state.get("subject_description", ""),
        })
        for item in queue
    ]
    
    analysis_results = await asyncio.gather(*tasks)
    results = [r.model_dump() for r in analysis_results]
    
    relevant = sum(1 for r in results if r.get('case_relevant'))
    logger.info(f"[STATION 5: video_analysis] Analysis complete: {len(results)} processed, {relevant} identified as case-relevant")

    trace = _make_trace(
        agent="video_analysis",
        input_summary=f"queued={len(queue)}",
        decision=f"analyzed={len(results)} relevant={relevant}",
        reasoning=f"Parallelized Gemini calls ({len(tasks)} concurrent tasks) for performance optimization",
    )

    return {
        "video_analyses_this_run": results,
        "analyzed_post_ids": [item["post_id"] for item in queue],
        "agent_trace": [trace],
    }


# ── Node 6: claim_extractor ──────────────────────────────────────────────────

async def claim_extractor_node(state: CaseState) -> dict:
    """STATION 6: claim_extractor_node - Distills facts and embeddings."""
    case_id = state["case_id"]
    posts = state.get("current_posts", [])
    video_analyses = state.get("video_analyses_this_run", [])

    logger.info(f"[STATION 6: claim_extractor] Extracting claims from {len(posts)} posts and {len(video_analyses)} video analyses")

    if not posts and not video_analyses:
        logger.warning(f"[STATION 6: claim_extractor] No data available for extraction")
        return {
            "current_claims": [],
            "agent_trace": [_make_trace("claim_extractor", "no data", "skipped", "")]
        }

    # ── Path A: extract from text posts (Parallelized) ────────────────────────
    tasks = []
    active_posts = []
    for post in posts:
        text = post.get("normalized_text", "").strip()
        if len(text) < 10: continue
        active_posts.append(post)
        tasks.append(_llm_extract_claims(text, state.get("subject_description", ""), ""))

    results_lists = await asyncio.gather(*tasks) if tasks else []
    all_new_claims: list[ExtractedClaim] = []

    for post, raw_claims in zip(active_posts, results_lists):
        for raw in raw_claims:
            stmt = raw.get("statement", "").strip()
            if not stmt: continue
            try: 
                vector = await embed_text(stmt)
            except Exception as e:
                logger.error(f"[STATION 6: claim_extractor] Embedding failed for claim: {e}")
                vector = []

            all_new_claims.append(ExtractedClaim(
                claim_id=_claim_id(),
                source_event_id=post["event_id"],
                case_id=case_id,
                claim_type=raw.get("claim_type", "rumour"),
                statement=stmt,
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
        p_id = analysis.get("post_id", "")
        for spoken in analysis.get("spoken_claims", []):
            stmt = spoken.get("quote", "").strip()
            if not stmt: continue
            try: vector = await embed_text(stmt)
            except: vector = []

            all_new_claims.append(ExtractedClaim(
                claim_id=_claim_id(),
                source_event_id=f"tiktok_{p_id}",
                case_id=case_id,
                claim_type=spoken.get("claim_type", "sighting"),
                statement=stmt,
                extraction_confidence=float(spoken.get("confidence", 0.5)),
                language=spoken.get("language", "unknown"),
                embedding_vector=vector,
                from_video=True,
                video_post_id=p_id,
            ))

    logger.info(f"[STATION 6: claim_extractor] Total claims extracted: {len(all_new_claims)}")

    trace = _make_trace(
        agent="claim_extractor",
        input_summary=f"posts={len(active_posts)} videos={len(video_analyses)}",
        decision=f"extracted={len(all_new_claims)}",
        reasoning=f"Processed text and video signals into atomic structured claims with embeddings.",
    )

    return {
        "current_claims": all_new_claims,
        "all_claims": all_new_claims,
        "agent_trace": [trace],
    }


# ── Node 7: clustering ────────────────────────────────────────────────────────

async def clustering_node(state: CaseState) -> dict:
    """STATION 7: clustering_node - Qdrant semantic grouping."""
    case_id = state["case_id"]
    new_claims = state.get("current_claims", [])

    logger.info(f"[STATION 7: clustering] Processing {len(new_claims)} new claims into clusters")

    if not new_claims:
        logger.info(f"[STATION 7: clustering] No claims to cluster")
        return {"current_clusters": [], "agent_trace": [_make_trace("clustering", "none", "skipped", "")]}

    await ensure_collection(case_id)
    cluster_map = {c["cluster_id"]: c for c in state.get("all_clusters", [])}
    point_to_cluster = {pid: c["cluster_id"] for c in cluster_map.values() for pid in c.get("_point_ids", [])}
    
    claims_with_qdrant = []

    for claim in new_claims:
        vector = claim.get("embedding_vector", [])
        if not vector or all(v == 0.0 for v in vector):
            claims_with_qdrant.append(claim)
            continue

        point_id = await upsert_claim(
            case_id=case_id,
            claim_id=claim["claim_id"],
            vector=vector,
            payload={"statement": claim["statement"], "case_id": case_id}
        )

        updated_claim = {**claim, "qdrant_point_id": point_id}
        claims_with_qdrant.append(updated_claim)

        similar = await find_similar_claims(case_id=case_id, vector=vector, limit=5)
        assigned_id = None
        for s in similar:
            if str(s.id) != point_id and str(s.id) in point_to_cluster:
                assigned_id = point_to_cluster[str(s.id)]
                break

        if assigned_id:
            cluster_map[assigned_id]["claim_ids"].append(claim["claim_id"])
            cluster_map[assigned_id].setdefault("_point_ids", []).append(point_id)
            logger.debug(f"[STATION 7: clustering] Claim {claim['claim_id']} added to cluster {assigned_id}")
        else:
            new_id = _cluster_id()
            cluster_map[new_id] = ClusterState(
                cluster_id=new_id,
                label=claim["statement"][:80],
                claim_ids=[claim["claim_id"]],
                platform_breakdown={},
                crowd_score=0.0,
                final_score=0.0,
                status="low",
            )
            cluster_map[new_id]["_point_ids"] = [point_id]
            point_to_cluster[point_id] = new_id
            logger.info(f"[STATION 7: clustering] Created NEW cluster {new_id} for claim")

    updated_clusters = [v for v in cluster_map.values() if any(cid in v["claim_ids"] for cid in [c["claim_id"] for c in new_claims])]
    logger.info(f"[STATION 7: clustering] Final state: {len(cluster_map)} total clusters, {len(updated_clusters)} updated this run")

    return {
        "current_claims": claims_with_qdrant,
        "current_clusters": updated_clusters,
        "all_clusters": list(cluster_map.values()),
        "agent_trace": [_make_trace("clustering", f"new={len(new_claims)}", f"updated={len(updated_clusters)}", "")]
    }


# ── Node 8: scoring ───────────────────────────────────────────────────────────

async def scoring_node(state: CaseState) -> dict:
    """STATION 8: scoring_node - Credibility assessment."""
    clusters = state.get("current_clusters", [])
    logger.info(f"[STATION 8: scoring] Calculating scores for {len(clusters)} updated clusters")

    all_claims = {c["claim_id"]: c for c in state.get("all_claims", [])}
    all_posts = {p["event_id"]: p for p in state.get("all_posts", [])}

    scored_clusters = []
    high_signal_ids = []

    for cluster in clusters:
        c_ids = cluster.get("claim_ids", [])
        sources = set()
        bots = []
        for cid in c_ids:
            if claim := all_claims.get(cid):
                sources.add(claim["source_event_id"])
                if post := all_posts.get(claim["source_event_id"]):
                    bots.append(post.get("bot_score", 0.0))

        freq = min(len(c_ids) / 10.0, 1.0)
        div = min(len(sources) / 5.0, 1.0)
        bot_p = sum(bots) / len(bots) if bots else 0.0
        
        score = round((freq * 0.4) + (div * 0.4) - (bot_p * 0.2) + 0.1, 3)
        score = max(0.0, min(1.0, score))

        scored = {**cluster, "crowd_score": score, "final_score": score, "status": "high" if score >= 0.6 else "medium" if score >= 0.35 else "low"}
        scored_clusters.append(scored)
        if score >= 0.6: high_signal_ids.append(cluster["cluster_id"])
        logger.debug(f"[STATION 8: scoring] Cluster {cluster['cluster_id']} scored {score}")

    logger.info(f"[STATION 8: scoring] Scored {len(scored_clusters)} clusters. High signal: {len(high_signal_ids)}")

    return {
        "current_clusters": scored_clusters,
        "needs_verification": high_signal_ids,
        "agent_trace": [_make_trace("scoring", f"scored={len(scored_clusters)}", f"high={len(high_signal_ids)}", "")]
    }


# ── Node 9: lead_generator ────────────────────────────────────────────────────

async def lead_generator_node(state: CaseState) -> dict:
    """STATION 9: lead_generator_node - Synthesize investigator leads."""
    clusters = state.get("current_clusters", [])
    all_claims = {c["claim_id"]: c for c in state.get("all_claims", [])}
    existing_ids = {l["cluster_id"] for l in state.get("all_leads", [])}

    logger.info(f"[STATION 9: lead_generator] Evaluating {len(clusters)} clusters for lead promotion")

    new_leads = []
    for cluster in clusters:
        if cluster["final_score"] < 0.5 or cluster["cluster_id"] in existing_ids:
            continue

        unique_srcs = {all_claims[cid]["source_event_id"] for cid in cluster["claim_ids"] if cid in all_claims}
        
        lead = LeadState(
            lead_id=_lead_id(),
            cluster_id=cluster["cluster_id"],
            title=cluster["label"][:100],
            confidence=cluster["final_score"],
            crowd_score=cluster["crowd_score"],
            final_score=cluster["final_score"],
            claim_count=len(cluster["claim_ids"]),
            unique_sources=len(unique_srcs),
            evidence=[all_claims[cid]["statement"] for cid in cluster["claim_ids"][:5] if cid in all_claims],
            action_required=_suggest_action(cluster),
            priority="urgent" if cluster["final_score"] >= 0.8 else "high" if cluster["final_score"] >= 0.65 else "medium",
        )
        new_leads.append(lead)
        logger.info(f"[STATION 9: lead_generator] PROMOTED cluster {cluster['cluster_id']} to LEAD: {lead['title']}")

    all_leads = list(state.get("all_leads", []))
    all_leads.extend(new_leads)

    return {
        "current_leads": new_leads,
        "all_leads": all_leads,
        "agent_trace": [_make_trace("lead_generator", f"new={len(new_leads)}", "leads generated", "")]
    }


# ── Node 10: graph_updater ────────────────────────────────────────────────────

async def graph_updater_node(state: CaseState) -> dict:
    """STATION 10: graph_updater_node - Batch persistence to DB."""
    case_id = state["case_id"]
    posts = state.get("current_posts", [])
    claims = state.get("current_claims", [])
    leads = state.get("current_leads", [])

    logger.info(f"[STATION 10: graph_updater] Committing cycle results: {len(posts)} posts, {len(claims)} claims, {len(leads)} leads")

    try:
        async with get_db_ctx() as db:
            if posts:
                p_vals = [{"id": p["event_id"], "case_id": case_id, "source": p["source"], "post_id": p["post_id"], "normalized_text": p["normalized_text"], "bot_score": p["bot_score"], "engagement_score": p["engagement_score"], "video_url": p.get("video_url")} for p in posts]
                await db.execute(insert(RawPost).values(p_vals).on_conflict_do_nothing(index_elements=["id"]))

            if claims:
                c_vals = [{"id": c["claim_id"], "case_id": case_id, "source_post_id": c["source_event_id"], "claim_type": c["claim_type"], "statement": c["statement"], "qdrant_point_id": c.get("qdrant_point_id"), "from_video": c.get("from_video", False)} for c in claims]
                await db.execute(insert(ExtractedClaimModel).values(c_vals).on_conflict_do_nothing(index_elements=["id"]))

            if leads:
                l_vals = [{"id": l["lead_id"], "case_id": case_id, "cluster_id": l["cluster_id"], "title": l["title"], "confidence": l["confidence"], "priority": l["priority"]} for l in leads]
                await db.execute(insert(Lead).values(l_vals).on_conflict_do_nothing(index_elements=["id"]))

            await db.commit()
            logger.info(f"[STATION 10: graph_updater] Database commit successful for case={case_id}")

        return {
            "current_posts": [], "current_claims": [], "current_leads": [], "video_analyses_this_run": [],
            "agent_trace": [_make_trace("graph_updater", f"p={len(posts)} c={len(claims)} l={len(leads)}", "Persisted", "")]
        }

    except Exception as e:
        logger.error(f"[STATION 10: graph_updater] DB write FAILED: {e}", exc_info=True)
        return {"agent_trace": [_make_trace("graph_updater", "error", str(e)[:50], "")]}
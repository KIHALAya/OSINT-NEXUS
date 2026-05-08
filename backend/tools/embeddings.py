"""
tools/embeddings.py

Two responsibilities:
  1. Generate text embeddings via Google's embedding API (free, no quota issues)
  2. Upsert / search Qdrant for claim clustering

Why Google's embedding model instead of sentence-transformers?
  - No GPU or model download needed — pure API call
  - `text-embedding-004` handles Arabic, French, Darija natively
  - Free tier: 1,500 req/min for the embedding API
  - Dimension: 768 (good balance of quality and Qdrant storage cost)

Qdrant collection per case:
  - Collection name: f"claims_{case_id}"  (e.g. "claims_CASE-2024-0847")
  - Each point: { id: UUID, vector: [768 floats], payload: claim metadata }
  - Cosine similarity threshold for same-cluster: 0.78
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    ScoredPoint,
)

from core.config import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768
SIMILARITY_THRESHOLD = 0.78         # cosine similarity — claims above this merge into same cluster
GEMINI_EMBED_BASE = "https://generativelanguage.googleapis.com/v1beta"


# ── Embedding generation ──────────────────────────────────────────────────────

async def embed_text(text: str, client: httpx.AsyncClient | None = None) -> list[float]:
    """
    Generate a 768-dim embedding for `text` using Google text-embedding-004.
    Returns a list of 768 floats.

    The model handles Arabic (MSA + Darija), French, and English without
    any preprocessing — critical for multilingual claim clustering.
    """
    settings = get_settings()
    api_key = settings.gemini_api_key

    if not api_key:
        raise ValueError("GEMINI_API_KEY required for embeddings")

    text = text[:2000].strip()
    if not text:
        return [0.0] * EMBEDDING_DIM

    if client is None:
        async with httpx.AsyncClient(timeout=15) as c:
            return await _embed_call(text, c, api_key)
    else:
        return await _embed_call(text, client, api_key)


async def _embed_call(text: str, client: httpx.AsyncClient, api_key: str) -> list[float]:
    resp = await client.post(
        f"{GEMINI_EMBED_BASE}/models/text-embedding-004:embedContent",
        params={"key": api_key},
        json={
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text}]},
            "taskType": "SEMANTIC_SIMILARITY",
        },
    )

    if resp.status_code == 429:
        raise RuntimeError("Embedding API rate limit — wait 1 minute")
    resp.raise_for_status()

    values = resp.json().get("embedding", {}).get("values", [])
    if not values:
        logger.warning(f"Empty embedding returned for text: {text[:50]}")
        return [0.0] * EMBEDDING_DIM

    return values


async def embed_texts_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts in parallel with a semaphore to respect rate limits.
    """
    if not texts:
        return []

    sem = asyncio.BoundedSemaphore(20)

    async def _safe_embed(text: str, client: httpx.AsyncClient) -> list[float]:
        async with sem:
            try:
                return await embed_text(text, client=client)
            except Exception as e:
                logger.warning(f"Embedding failed for text '{text[:40]}': {e} — using zero vector")
                return [0.0] * EMBEDDING_DIM

    async with httpx.AsyncClient(timeout=15) as client:
        tasks = [_safe_embed(t, client) for t in texts]
        return list(await asyncio.gather(*tasks))


# ── Qdrant operations ─────────────────────────────────────────────────────────

def _get_qdrant() -> AsyncQdrantClient:
    settings = get_settings()
    return AsyncQdrantClient(url=settings.qdrant_url)


async def ensure_collection(case_id: str):
    """
    Create the Qdrant collection for a case if it doesn't exist.
    Safe to call on every run — is a no-op if collection exists.
    """
    client = _get_qdrant()
    collection_name = f"claims_{case_id}"
    try:
        await client.get_collection(collection_name)
    except Exception:
        # Collection doesn't exist — create it
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection: {collection_name}")
    finally:
        await client.close()


async def upsert_claim(
    case_id: str,
    claim_id: str,
    vector: list[float],
    payload: dict[str, Any],
) -> str:
    """
    Upsert a single claim into Qdrant.
    Returns the point_id (UUID string) used for retrieval.

    payload should contain: claim_type, statement, location_mentioned,
    extraction_confidence — stored alongside the vector for retrieval.
    """
    client = _get_qdrant()
    collection_name = f"claims_{case_id}"
    point_id = str(uuid.uuid4())

    try:
        await client.upsert(
            collection_name=collection_name,
            points=[PointStruct(
                id=point_id,
                vector=vector,
                payload={**payload, "claim_id": claim_id},
            )],
        )
    finally:
        await client.close()

    return point_id


async def find_similar_claims(
    case_id: str,
    vector: list[float],
    limit: int = 10,
    score_threshold: float = SIMILARITY_THRESHOLD,
) -> list[ScoredPoint]:
    """
    Find existing claims in this case's collection that are semantically
    similar to the given vector.

    Returns ScoredPoint list ordered by similarity (highest first).
    Each point's payload contains the original claim metadata.
    """
    client = _get_qdrant()
    collection_name = f"claims_{case_id}"

    try:
        results = await client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
    except Exception as e:
        logger.warning(f"Qdrant search failed for {collection_name}: {e}")
        results = []
    finally:
        await client.close()

    return results
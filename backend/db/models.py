"""
db/models.py

SQLAlchemy ORM — single source of truth for persistence.
Three core tables that map directly to Phase 3 of the architecture:

  raw_posts        → every ingested post (text + TikTok)
  extracted_claims → every claim produced by claim_extractor_node
  leads            → high-confidence clusters surfaced to investigators

Qdrant stores the embedding vectors; these tables store everything else.
A claim row carries a qdrant_point_id so you can join across both stores.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float,
    ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from db.database import Base


# ── Cases ─────────────────────────────────────────────────────────────────────

class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True)           # "CASE-2024-0847"
    subject_name = Column(String, nullable=False)
    subject_description = Column(Text)              # fed into video analysis prompt
    age = Column(Integer)
    location = Column(String)
    last_seen_date = Column(String)
    priority = Column(String, default="high")
    status = Column(String, default="active")       # active | monitoring | closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    raw_posts = relationship("RawPost", back_populates="case", lazy="select")
    extracted_claims = relationship("ExtractedClaimModel", back_populates="case", lazy="select")
    leads = relationship("Lead", back_populates="case", lazy="select")


# ── Raw posts ─────────────────────────────────────────────────────────────────

class RawPost(Base):
    """
    Every post that passes the normalizer lands here.
    Written by: graph_updater_node (or directly by tiktok_ingestor_node).
    Source-agnostic: source field distinguishes tiktok / reddit / twitter.
    """
    __tablename__ = "raw_posts"

    id = Column(String, primary_key=True)           # event_id
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    source = Column(String, nullable=False)         # "tiktok" | "reddit" | "twitter"
    post_id = Column(String, nullable=False)        # platform-native ID
    normalized_text = Column(Text)
    detected_language = Column(String(8))
    bot_score = Column(Float, default=0.0)
    is_duplicate = Column(Boolean, default=False)
    engagement_score = Column(Float, default=0.0)
    author_id = Column(String)
    author_name = Column(String)
    author_followers = Column(Integer, default=0)
    author_verified = Column(Boolean, default=False)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    plays = Column(Integer, default=0)
    posted_at = Column(String)
    video_url = Column(String)                      # populated for TikTok posts
    thumbnail_url = Column(String)
    hashtags = Column(JSONB, default=list)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="raw_posts")
    claims = relationship("ExtractedClaimModel", back_populates="source_post", lazy="select")

    __table_args__ = (
        UniqueConstraint("source", "post_id", "case_id", name="uq_raw_posts"),
        Index("ix_raw_posts_case_source", "case_id", "source"),
        Index("ix_raw_posts_engagement", "case_id", "engagement_score"),
    )


# ── Extracted claims ──────────────────────────────────────────────────────────

class ExtractedClaimModel(Base):
    """
    One row per structured claim extracted by claim_extractor_node.
    Written by: graph_updater_node after each run.

    qdrant_point_id links this row to its embedding vector in Qdrant.
    cluster_id is populated by clustering_node once the claim is assigned.
    """
    __tablename__ = "extracted_claims"

    id = Column(String, primary_key=True)           # claim_id
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    source_post_id = Column(String, ForeignKey("raw_posts.id"), nullable=True)

    claim_type = Column(String)                     # sighting | location | rumour | denial
    statement = Column(Text, nullable=False)
    location_mentioned = Column(String)
    time_mentioned = Column(String)
    extraction_confidence = Column(Float, default=0.0)
    language = Column(String(8))

    # Clustering
    cluster_id = Column(String, nullable=True, index=True)
    qdrant_point_id = Column(String, nullable=True)  # UUID in Qdrant collection

    # Source tracing
    from_video = Column(Boolean, default=False)
    video_post_id = Column(String, nullable=True)

    extracted_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="extracted_claims")
    source_post = relationship("RawPost", back_populates="claims")

    __table_args__ = (
        Index("ix_claims_case_cluster", "case_id", "cluster_id"),
        Index("ix_claims_case_type", "case_id", "claim_type"),
    )


# ── Leads ─────────────────────────────────────────────────────────────────────

class Lead(Base):
    """
    High-confidence cluster surfaced to human investigators.
    Written by: graph_updater_node when a cluster crosses the lead threshold.
    """
    __tablename__ = "leads"

    id = Column(String, primary_key=True)           # lead_id
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    cluster_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)

    # Score breakdown
    crowd_score = Column(Float, default=0.0)
    ai_verification_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)

    # Content
    claim_count = Column(Integer, default=0)
    unique_sources = Column(Integer, default=0)
    evidence = Column(JSONB, default=list)           # list[str] of evidence strings
    action_required = Column(Text)

    priority = Column(String, default="medium")     # urgent | high | medium | low
    status = Column(String, default="open")         # open | assigned | closed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = relationship("Case", back_populates="leads")

    __table_args__ = (
        Index("ix_leads_case_priority", "case_id", "priority"),
        Index("ix_leads_case_score", "case_id", "final_score"),
    )
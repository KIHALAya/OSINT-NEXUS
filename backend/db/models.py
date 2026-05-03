"""
db/models.py

SQLAlchemy ORM models.

TikTok posts get their own table (tiktok_posts) rather than being
folded into a generic "posts" table. This lets us:
  - Query TikTok-specific fields (engagement_score, hashtags)
  - Run platform-specific analytics without EAV gymnastics
  - Add TikTok-specific indexes efficiently

The raw_posts table holds the generic normalized form
shared by all platforms.
"""

from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float,
    ForeignKey, Index, Integer, String, Text, JSON,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Cases ─────────────────────────────────────────────────────────────────────

class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True)       # "CASE-2024-0847"
    subject_name = Column(String, nullable=False)
    age = Column(Integer)
    location = Column(String)
    last_seen_date = Column(String)
    description = Column(Text)
    priority = Column(String, default="medium")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tiktok_posts = relationship("TikTokPostModel", back_populates="case")
    raw_posts = relationship("RawPostModel", back_populates="case")
    leads = relationship("LeadModel", back_populates="case")


# ── Raw posts (platform-agnostic) ─────────────────────────────────────────────

class RawPostModel(Base):
    __tablename__ = "raw_posts"

    id = Column(String, primary_key=True)       # event_id
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    source = Column(String, nullable=False)     # "tiktok" | "reddit" | ...
    post_id = Column(String, nullable=False)
    normalized_text = Column(Text)
    detected_language = Column(String(8))
    bot_score = Column(Float, default=0.0)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(String, nullable=True)
    engagement_score = Column(Float, default=0.0)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    posted_at = Column(DateTime, nullable=True)
    author_id = Column(String)
    raw_metadata = Column(JSON, default=dict)

    case = relationship("Case", back_populates="raw_posts")

    __table_args__ = (
        UniqueConstraint("source", "post_id", name="uq_raw_posts_source_post_id"),
        Index("ix_raw_posts_case_source", "case_id", "source"),
    )


# ── TikTok posts (platform-specific) ─────────────────────────────────────────

class TikTokPostModel(Base):
    """
    TikTok-specific post storage.
    Persisted by the graph_updater_node after the investigation run.
    Also used by the API layer to serve TikTok-specific analytics.
    """
    __tablename__ = "tiktok_posts"

    id = Column(String, primary_key=True)           # tiktok post_id
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)

    # Content
    url = Column(String)
    text = Column(Text)
    content_hash = Column(String(16), index=True)   # for cross-platform dedup

    # Author
    author_id = Column(String, index=True)
    author_name = Column(String)
    author_followers = Column(Integer, default=0)
    author_verified = Column(Boolean, default=False)

    # Engagement
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    plays = Column(Integer, default=0)
    engagement_score = Column(Float, default=0.0)

    # Metadata
    posted_at = Column(String, nullable=True)
    hashtags = Column(ARRAY(String), default=list)
    mentions = Column(ARRAY(String), default=list)
    music_title = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    # Processing state
    bot_score = Column(Float, default=0.0)
    is_misinformation = Column(Boolean, default=False)
    misinfo_reason = Column(Text, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="tiktok_posts")

    __table_args__ = (
        UniqueConstraint("id", "case_id", name="uq_tiktok_posts_id_case"),
        Index("ix_tiktok_posts_engagement", "case_id", "engagement_score"),
        Index("ix_tiktok_posts_content_hash", "content_hash"),
    )


# ── Leads ─────────────────────────────────────────────────────────────────────

class LeadModel(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    cluster_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    priority = Column(String, default="medium")
    evidence = Column(JSON, default=list)
    action_required = Column(Text)
    status = Column(String, default="open")     # "open" | "assigned" | "closed"
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="leads")

    __table_args__ = (
        Index("ix_leads_case_priority", "case_id", "priority"),
    )
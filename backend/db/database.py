"""
db/database.py

Async SQLAlchemy session management.
Two helpers:
  - get_db()      FastAPI dependency (request-scoped session)
  - get_db_ctx()  async context manager for use inside nodes/services
                  (not inside a request)

Nodes use get_db_ctx() because they run inside the LangGraph executor,
not inside a FastAPI request handler.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )


# Module-level singletons — created once at import time
_engine = _make_engine()
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session


# Node / service usage
@asynccontextmanager
async def get_db_ctx() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session


async def create_tables():
    """Call once at startup to create all tables."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
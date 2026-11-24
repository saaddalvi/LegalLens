"""Postgres on Neon: the users table and the connection to it.

Only the Contract explainer uses the database. `/ask` works with DATABASE_URL unset
(ADR 0005), so everything here is optional at the edges: `Database.from_env()` is None
when no database is configured.
"""

from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import DateTime, Text, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # The Clerk user id. Later tables reference it with ON DELETE CASCADE.
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def driver_url(url: str) -> str:
    """Neon hands out `postgresql://` (or `postgres://`) URLs; SQLAlchemy needs the psycopg driver named."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Database:
    def __init__(self, url: str, *, pooled: bool = True):
        # pooled=False opens a connection per use, for tests that drive the app from
        # a fresh event loop on each request.
        self.engine: AsyncEngine = create_async_engine(
            driver_url(url),
            pool_pre_ping=True,  # Neon suspends idle computes and drops their connections
            **({} if pooled else {"poolclass": NullPool}),
        )
        self._known: set[str] = set()

    @classmethod
    def from_env(cls) -> Database | None:
        url = os.environ.get("DATABASE_URL", "").strip()
        return cls(url) if url else None

    async def ensure_user(self, user_id: str) -> None:
        """Creates the users row the first time a user is seen; a no-op after that."""
        if user_id in self._known:
            return
        async with self.engine.begin() as conn:
            await conn.execute(insert(User).values(id=user_id).on_conflict_do_nothing())
        self._known.add(user_id)

    async def delete_user(self, user_id: str) -> None:
        """Deletes the user; foreign keys cascade to everything of theirs."""
        self._known.discard(user_id)
        async with self.engine.begin() as conn:
            await conn.execute(delete(User).where(User.id == user_id))

    async def dispose(self) -> None:
        await self.engine.dispose()

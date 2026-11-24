"""Postgres on Neon: the users table and the connection to it.

Only the Contract explainer uses the database. `/ask` works with DATABASE_URL unset
(ADR 0005), so everything here is optional at the edges: `Database.from_env()` is None
when no database is configured.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Text,
    Uuid,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from .clauses import ClausePiece
from .models import (
    ClauseOut,
    ContractAnswer,
    ContractBrief,
    ContractDetail,
    ContractSummary,
    ConversationTurn,
)

EMBEDDING_DIMENSIONS = 1024  # Qwen3-Embedding-0.6B (ADR 0003)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # The Clerk user id. Later tables reference it with ON DELETE CASCADE.
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(
        Text
    )  # the extracted text; the file is never kept
    page_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Clause(Base):
    """One piece of one Clause: a long Clause is several rows with the same number."""

    __tablename__ = "clauses"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    contract_id: Mapped[str] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[str] = mapped_column(Text)
    heading: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    piece: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))


class ContractMessage(Base):
    """One message of a Contract conversation. The first is the Contract brief."""

    __tablename__ = "contract_messages"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    contract_id: Mapped[str] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Usage(Base):
    """What one user has used on one UTC day, for the daily caps."""

    __tablename__ = "usage"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    contracts: Mapped[int] = mapped_column(Integer, server_default="0")
    queries: Mapped[int] = mapped_column(Integer, server_default="0")


def _turns(rows) -> list[ConversationTurn]:
    """The Queries and answers among a Contract's messages, oldest answer first. A Query and
    its answer share a `turn` id, so two Queries saved at once are never mixed up."""
    queries: dict[str, str] = {}
    answered: list[tuple[str, dict]] = []
    for role, payload in rows:
        if role == "user":
            queries[payload["turn"]] = payload["text"]
        else:
            answered.append((payload["turn"], payload["response"]))
    return [
        ConversationTurn(
            query=queries[turn], response=ContractAnswer.model_validate(response)
        )
        for turn, response in answered
        if turn in queries
    ]


@dataclass(frozen=True)
class ClauseHit:
    """A stored piece of a Clause found by similarity search."""

    number: str
    heading: str
    text: str
    piece: int


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

    async def add_contract(
        self,
        user_id: str,
        *,
        title: str,
        text: str,
        page_count: int,
        pieces: list[ClausePiece],
        vectors: list[list[float]],
        brief: ContractBrief,
    ) -> str:
        """Stores a Contract, all its Clause pieces and its brief (the first message of its
        Contract conversation) in one transaction; returns its id."""
        contract_id = str(uuid.uuid4())
        async with self.engine.begin() as conn:
            await conn.execute(
                insert(Contract).values(
                    id=contract_id,
                    user_id=user_id,
                    title=title,
                    text=text,
                    page_count=page_count,
                )
            )
            await conn.execute(
                insert(Clause),
                [
                    {
                        "contract_id": contract_id,
                        "number": p.number,
                        "heading": p.heading,
                        "text": p.text,
                        "piece": p.piece,
                        "embedding": v,
                    }
                    for p, v in zip(pieces, vectors, strict=True)
                ],
            )
            await conn.execute(
                insert(ContractMessage).values(
                    contract_id=contract_id,
                    role="assistant",
                    payload={"type": "brief", **brief.model_dump(mode="json")},
                )
            )
        return contract_id

    async def list_contracts(self, user_id: str) -> list[ContractSummary]:
        """The user's own Contracts, newest first."""
        clause_count = (
            select(func.count(func.distinct(Clause.number)))
            .where(Clause.contract_id == Contract.id)
            .scalar_subquery()
        )
        async with self.engine.connect() as conn:
            rows = await conn.execute(
                select(
                    Contract.id,
                    Contract.title,
                    Contract.created_at,
                    Contract.page_count,
                    clause_count.label("clause_count"),
                )
                .where(Contract.user_id == user_id)
                .order_by(Contract.created_at.desc())
            )
            return [ContractSummary(**r._mapping) for r in rows]

    async def get_contract(
        self, user_id: str, contract_id: str
    ) -> ContractDetail | None:
        """A Contract with its Clauses, or None when it does not exist or is not the user's."""
        async with self.engine.connect() as conn:
            head = (
                await conn.execute(
                    select(Contract).where(
                        Contract.id == contract_id, Contract.user_id == user_id
                    )
                )
            ).one_or_none()
            if head is None:
                return None
            pieces = await conn.execute(
                select(Clause.number, Clause.heading, Clause.text)
                .where(Clause.contract_id == contract_id)
                .order_by(Clause.id)
            )
            messages = await conn.execute(
                select(ContractMessage.role, ContractMessage.payload)
                .where(
                    ContractMessage.contract_id == contract_id,
                    ContractMessage.payload["type"].astext.in_(["query", "answer"]),
                )
                .order_by(ContractMessage.id)
            )
            conversation = _turns(messages)
            stored = (
                await conn.execute(
                    select(ContractMessage.payload)
                    .where(
                        ContractMessage.contract_id == contract_id,
                        ContractMessage.payload["type"].astext == "brief",
                    )
                    .order_by(ContractMessage.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
        clauses: dict[str, ClauseOut] = {}
        for number, heading, text in pieces:
            if number in clauses:  # a later piece of the same Clause
                clauses[number].text += text
            else:
                clauses[number] = ClauseOut(number=number, heading=heading, text=text)
        return ContractDetail(
            id=head.id,
            title=head.title,
            created_at=head.created_at,
            page_count=head.page_count,
            clause_count=len(clauses),
            clauses=list(clauses.values()),
            brief=ContractBrief.model_validate(stored) if stored else None,
            conversation=conversation,
        )

    async def search_clauses(
        self, user_id: str, contract_id: str, vector: list[float], k: int = 5
    ) -> list[ClauseHit]:
        """The k Clause pieces of one Contract closest to `vector`. Only that Contract's
        pieces, and only if it is the user's, are ever searched."""
        async with self.engine.connect() as conn:
            rows = await conn.execute(
                select(Clause.number, Clause.heading, Clause.text, Clause.piece)
                .join(Contract, Contract.id == Clause.contract_id)
                .where(Contract.id == contract_id, Contract.user_id == user_id)
                .order_by(Clause.embedding.cosine_distance(vector))
                .limit(k)
            )
            return [ClauseHit(*r) for r in rows]

    async def owns_contract(self, user_id: str, contract_id: str) -> bool:
        async with self.engine.connect() as conn:
            found = await conn.execute(
                select(Contract.id).where(
                    Contract.id == contract_id, Contract.user_id == user_id
                )
            )
            return found.first() is not None

    async def get_clauses(self, user_id: str, contract_id: str) -> dict[str, str]:
        """Every Clause of the user's Contract with its whole verbatim text, in order. Empty
        when the Contract does not exist or is not the user's."""
        async with self.engine.connect() as conn:
            rows = await conn.execute(
                select(Clause.number, Clause.text)
                .join(Contract, Contract.id == Clause.contract_id)
                .where(Contract.id == contract_id, Contract.user_id == user_id)
                .order_by(Clause.id)
            )
            clauses: dict[str, str] = {}
            for number, text in rows:
                clauses[number] = clauses.get(number, "") + text
            return clauses

    async def recent_turns(
        self, user_id: str, contract_id: str, count: int
    ) -> list[ConversationTurn]:
        """The last `count` Queries of this Contract's conversation with their answers, oldest
        first. Never another Contract's, and never someone else's."""
        async with self.engine.connect() as conn:
            rows = await conn.execute(
                select(ContractMessage.role, ContractMessage.payload)
                .join(Contract, Contract.id == ContractMessage.contract_id)
                .where(
                    Contract.id == contract_id,
                    Contract.user_id == user_id,
                    ContractMessage.payload["type"].astext.in_(["query", "answer"]),
                )
                .order_by(ContractMessage.id)
            )
            return _turns(rows)[-count:] if count > 0 else []

    async def add_turn(
        self,
        user_id: str,
        contract_id: str,
        query: str,
        response: ContractAnswer,
    ) -> None:
        """Appends a Query and its answer to the Contract's conversation, together or not at
        all. Raises LookupError when the Contract is not the user's (or was just deleted)."""
        turn = str(uuid.uuid4())
        async with self.engine.begin() as conn:
            owned = await conn.execute(
                select(Contract.id).where(
                    Contract.id == contract_id, Contract.user_id == user_id
                )
            )
            if owned.first() is None:
                raise LookupError("no such Contract")
            await conn.execute(
                insert(ContractMessage),
                [
                    {
                        "contract_id": contract_id,
                        "role": "user",
                        "payload": {"type": "query", "turn": turn, "text": query},
                    },
                    {
                        "contract_id": contract_id,
                        "role": "assistant",
                        "payload": {
                            "type": "answer",
                            "turn": turn,
                            "response": response.model_dump(mode="json"),
                        },
                    },
                ],
            )

    async def delete_contract(self, user_id: str, contract_id: str) -> bool:
        """Deletes the user's Contract; foreign keys cascade to its Clauses, vectors and
        messages. False when it does not exist or is not the user's."""
        async with self.engine.begin() as conn:
            deleted = await conn.execute(
                delete(Contract)
                .where(Contract.id == contract_id, Contract.user_id == user_id)
                .returning(Contract.id)
            )
            return deleted.first() is not None

    async def reserve(self, user_id: str, kind: str, day: date, cap: int) -> bool:
        """Counts one more `kind` ("contracts" or "queries") for the user on `day` unless they
        are at `cap`. One atomic statement, so concurrent requests cannot pass the cap."""
        column = Usage.contracts if kind == "contracts" else Usage.queries
        async with self.engine.begin() as conn:
            row = await conn.execute(
                insert(Usage)
                .values(user_id=user_id, day=day, **{kind: 1})
                .on_conflict_do_update(
                    index_elements=[Usage.user_id, Usage.day],
                    set_={kind: column + 1},
                    where=column < cap,
                )
                .returning(column)
            )
            return row.first() is not None

    async def release(self, user_id: str, kind: str, day: date) -> None:
        """Gives back one `reserve`, for an upload that was refused."""
        column = Usage.contracts if kind == "contracts" else Usage.queries
        async with self.engine.begin() as conn:
            await conn.execute(
                update(Usage)
                .where(Usage.user_id == user_id, Usage.day == day)
                .values({kind: func.greatest(column - 1, 0)})
            )

    async def dispose(self) -> None:
        await self.engine.dispose()

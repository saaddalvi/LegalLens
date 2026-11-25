"""contract_conversations: several per Contract; the brief moves to the Contract

A Contract's saved Queries and answers become its first Contract conversation. A Contract with
none gets no conversation.

Revision ID: 0005
Revises: 0004
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from legallens.db import conversation_title

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_conversations",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "contract_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_contract_conversations_contract_id",
        "contract_conversations",
        ["contract_id"],
    )
    op.add_column("contracts", sa.Column("brief", JSONB()))
    op.add_column(
        "contract_messages",
        sa.Column(
            "conversation_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("contract_conversations.id", ondelete="CASCADE"),
        ),
    )
    op.create_index(
        "ix_contract_messages_conversation_id",
        "contract_messages",
        ["conversation_id"],
    )
    _move_the_brief()
    _start_first_conversations()
    op.alter_column("contract_messages", "conversation_id", nullable=False)


def _move_the_brief() -> None:
    op.execute(
        """
        UPDATE contracts SET brief = (
            SELECT payload - 'type' FROM contract_messages
            WHERE contract_id = contracts.id AND payload->>'type' = 'brief'
            ORDER BY id LIMIT 1
        )
        """
    )
    op.execute("DELETE FROM contract_messages WHERE payload->>'type' = 'brief'")


def _start_first_conversations() -> None:
    """One conversation for each Contract that has messages left, dated from its first and
    last, and every message pointed at it."""
    bind = op.get_bind()
    contracts = bind.execute(
        sa.text(
            """
            SELECT contract_id,
                   min(created_at) AS created_at,
                   max(created_at) AS updated_at,
                   (array_agg(payload->>'text' ORDER BY id)
                    FILTER (WHERE payload->>'type' = 'query'))[1] AS first_query
            FROM contract_messages GROUP BY contract_id
            """
        )
    ).all()
    for row in contracts:
        conversation_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO contract_conversations
                    (id, contract_id, title, created_at, updated_at)
                VALUES (:id, :contract_id, :title, :created_at, :updated_at)
                """
            ),
            {
                "id": conversation_id,
                "contract_id": row.contract_id,
                "title": conversation_title(row.first_query),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            },
        )
        bind.execute(
            sa.text(
                "UPDATE contract_messages SET conversation_id = :id "
                "WHERE contract_id = :contract_id"
            ),
            {"id": conversation_id, "contract_id": row.contract_id},
        )


def downgrade() -> None:
    """Back to one conversation per Contract: every conversation's messages run together
    again, and the brief returns as a message."""
    op.drop_column("contract_messages", "conversation_id")
    op.drop_table("contract_conversations")
    op.execute(
        """
        INSERT INTO contract_messages (contract_id, role, payload, created_at)
        SELECT id, 'assistant', brief || '{"type": "brief"}', created_at
        FROM contracts WHERE brief IS NOT NULL
        """
    )
    op.drop_column("contracts", "brief")

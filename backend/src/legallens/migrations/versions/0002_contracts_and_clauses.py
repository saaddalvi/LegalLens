"""contracts and clauses (with 1024-dimension Clause vectors)

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            sa.Text(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_contracts_user_id", "contracts", ["user_id"])
    op.create_table(
        "clauses",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "contract_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("piece", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
    )
    op.create_index("ix_clauses_contract_id", "clauses", ["contract_id"])


def downgrade() -> None:
    op.drop_table("clauses")
    op.drop_table("contracts")

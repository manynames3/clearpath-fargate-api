"""Add lead lifecycle outcomes.

Revision ID: 20260514_0005
Revises: 20260512_0004
Create Date: 2026-05-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260514_0005"
down_revision: str | None = "20260512_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("dead_reason", sa.String(length=255)),
        sa.Column("notes", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_lead_outcomes_lead_id", "lead_outcomes", ["lead_id"])
    op.create_index("idx_lead_outcomes_stage", "lead_outcomes", ["stage"])
    op.create_index("idx_lead_outcomes_occurred_at", "lead_outcomes", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("idx_lead_outcomes_occurred_at", table_name="lead_outcomes")
    op.drop_index("idx_lead_outcomes_stage", table_name="lead_outcomes")
    op.drop_index("idx_lead_outcomes_lead_id", table_name="lead_outcomes")
    op.drop_table("lead_outcomes")

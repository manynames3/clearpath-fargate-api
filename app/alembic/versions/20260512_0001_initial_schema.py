"""Initial Clearpath lead schema.

Revision ID: 20260512_0001
Revises:
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ghl_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("first_name", sa.String(length=255)),
        sa.Column("last_name", sa.String(length=255)),
        sa.Column("phone", sa.String(length=20)),
        sa.Column("email", sa.String(length=255)),
        sa.Column("status", sa.String(length=50), server_default="new"),
        sa.Column("source", sa.String(length=100)),
        sa.Column("county", sa.String(length=100)),
        sa.Column("state", sa.String(length=2), server_default="GA"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("leads.id", ondelete="CASCADE")),
        sa.Column("address", sa.Text()),
        sa.Column("city", sa.String(length=100)),
        sa.Column("county", sa.String(length=100)),
        sa.Column("state", sa.String(length=2)),
        sa.Column("zip", sa.String(length=10)),
        sa.Column("estimated_value", sa.Integer()),
        sa.Column("situation", sa.String(length=100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("leads.id", ondelete="CASCADE")),
        sa.Column("contacted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("method", sa.String(length=50)),
        sa.Column("notes", sa.Text()),
        sa.Column("next_follow_up", sa.Date()),
    )

    op.create_table(
        "market_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("county", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("median_price", sa.Integer()),
        sa.Column("avg_dom", sa.Integer()),
        sa.Column("snapshot_date", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("county", "state", "snapshot_date"),
    )

    op.create_index("idx_leads_county", "leads", ["county"])
    op.create_index("idx_leads_status", "leads", ["status"])
    op.create_index("idx_follow_ups_lead_id", "follow_ups", ["lead_id"])
    op.create_index("idx_follow_ups_next", "follow_ups", ["next_follow_up"])


def downgrade() -> None:
    op.drop_index("idx_follow_ups_next", table_name="follow_ups")
    op.drop_index("idx_follow_ups_lead_id", table_name="follow_ups")
    op.drop_index("idx_leads_status", table_name="leads")
    op.drop_index("idx_leads_county", table_name="leads")
    op.drop_table("market_snapshots")
    op.drop_table("follow_ups")
    op.drop_table("properties")
    op.drop_table("leads")

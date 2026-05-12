"""Add Phase 7 lead intelligence tables.

Revision ID: 20260512_0002
Revises: 20260512_0001
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0002"
down_revision: str | None = "20260512_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_sources",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("vendor_name", sa.String(length=255)),
        sa.Column("channel", sa.String(length=100)),
        sa.Column("cost_per_lead_cents", sa.Integer()),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("leads", sa.Column("source_id", postgresql.UUID(as_uuid=False), nullable=True))
    op.create_foreign_key("fk_leads_source_id", "leads", "lead_sources", ["source_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_leads_source_id", "leads", ["source_id"])

    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(length=100), server_default="gohighlevel", nullable=False),
        sa.Column("external_id", sa.String(length=255)),
        sa.Column("lead_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("leads.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(length=100), server_default="contact", nullable=False),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_webhook_events_lead_id", "webhook_events", ["lead_id"])
    op.create_index("idx_webhook_events_external_id", "webhook_events", ["external_id"])

    op.create_table(
        "lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("leads.id", ondelete="CASCADE"), unique=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("needs_review", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_lead_scores_score", "lead_scores", ["score"])
    op.create_index("idx_lead_scores_needs_review", "lead_scores", ["needs_review"])

    op.create_table(
        "duplicate_leads",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "duplicate_lead_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("lead_id", "duplicate_lead_id", "match_type"),
    )
    op.create_index("idx_duplicate_leads_lead_id", "duplicate_leads", ["lead_id"])
    op.create_index("idx_duplicate_leads_duplicate_id", "duplicate_leads", ["duplicate_lead_id"])


def downgrade() -> None:
    op.drop_index("idx_duplicate_leads_duplicate_id", table_name="duplicate_leads")
    op.drop_index("idx_duplicate_leads_lead_id", table_name="duplicate_leads")
    op.drop_table("duplicate_leads")
    op.drop_index("idx_lead_scores_needs_review", table_name="lead_scores")
    op.drop_index("idx_lead_scores_score", table_name="lead_scores")
    op.drop_table("lead_scores")
    op.drop_index("idx_webhook_events_external_id", table_name="webhook_events")
    op.drop_index("idx_webhook_events_lead_id", table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_index("idx_leads_source_id", table_name="leads")
    op.drop_constraint("fk_leads_source_id", "leads", type_="foreignkey")
    op.drop_column("leads", "source_id")
    op.drop_table("lead_sources")

"""Add provider lead detail fields.

Revision ID: 20260512_0003
Revises: 20260512_0002
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_0003"
down_revision: str | None = "20260512_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("occupancy", sa.String(length=100)))
    op.add_column("properties", sa.Column("selling_urgency", sa.String(length=100)))
    op.add_column("properties", sa.Column("seller_type", sa.String(length=100)))
    op.add_column("properties", sa.Column("listing_status", sa.String(length=100)))
    op.add_column("properties", sa.Column("repair_scope", sa.String(length=255)))
    op.add_column("properties", sa.Column("property_type", sa.String(length=100)))
    op.add_column("properties", sa.Column("years_owned", sa.String(length=100)))
    op.add_column("properties", sa.Column("apn", sa.String(length=100)))


def downgrade() -> None:
    op.drop_column("properties", "apn")
    op.drop_column("properties", "years_owned")
    op.drop_column("properties", "property_type")
    op.drop_column("properties", "repair_scope")
    op.drop_column("properties", "listing_status")
    op.drop_column("properties", "seller_type")
    op.drop_column("properties", "selling_urgency")
    op.drop_column("properties", "occupancy")

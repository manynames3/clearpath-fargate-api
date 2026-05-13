"""Add county resolution metadata.

Revision ID: 20260512_0004
Revises: 20260512_0003
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_0004"
down_revision: str | None = "20260512_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("county_resolution_method", sa.String(length=50)))
    op.add_column("properties", sa.Column("county_resolution_confidence", sa.Integer()))


def downgrade() -> None:
    op.drop_column("properties", "county_resolution_confidence")
    op.drop_column("properties", "county_resolution_method")

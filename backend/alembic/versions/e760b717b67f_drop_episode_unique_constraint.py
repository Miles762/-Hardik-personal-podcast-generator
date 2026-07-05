"""drop episode unique constraint

Revision ID: e760b717b67f
Revises: dadb4a25fb1d
Create Date: 2026-07-05 15:37:30.015655
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e760b717b67f'
down_revision: str | None = 'dadb4a25fb1d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Multiple episodes per day are allowed (user-requested); drop the unique
    # constraint on (user_id, episode_date). IF EXISTS keeps it idempotent.
    op.execute("ALTER TABLE episodes DROP CONSTRAINT IF EXISTS uq_episode_user_date")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_episode_user_date", "episodes", ["user_id", "episode_date"]
    )

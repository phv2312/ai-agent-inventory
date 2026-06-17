"""drop alerts table

Revision ID: 003_drop_alerts
Revises: 002_drop_is_tracked
Create Date: 2026-06-14

"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_drop_alerts"
down_revision: Union[str, None] = "002_drop_is_tracked"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("alerts")


def downgrade() -> None:
    raise NotImplementedError("Alerts table removal is not reversible")

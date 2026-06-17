"""drop is_tracked from assets

Revision ID: 002_drop_is_tracked
Revises: 001_initial
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_drop_is_tracked"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_column("is_tracked")


def downgrade() -> None:
    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_tracked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

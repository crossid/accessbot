"""adds active to rules

Revision ID: 75a1807159c8
Revises: bd921dc0747d
Create Date: 2024-07-11 13:11:33.717628

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "75a1807159c8"
down_revision: Union[str, None] = "bd921dc0747d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rules", sa.Column("active", sa.Boolean(), nullable=False, default=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column("rules", "active")
    # ### end Alembic commands ###

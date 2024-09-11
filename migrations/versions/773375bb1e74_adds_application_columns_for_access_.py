"""adds application columns for access prediction

Revision ID: 773375bb1e74
Revises: ad280954d50d
Create Date: 2024-09-11 12:17:35.274283

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "773375bb1e74"
down_revision: Union[str, None] = "ad280954d50d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("read_directory_id", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("write_directory_id", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "applications", sa.Column("business_instructions", sa.TEXT(), nullable=True)
    )
    op.create_foreign_key(
        None, "applications", "directories", ["write_directory_id"], ["id"]
    )
    op.create_foreign_key(
        None, "applications", "directories", ["read_directory_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(None, "applications", type_="foreignkey")
    op.drop_constraint(None, "applications", type_="foreignkey")
    op.drop_column("applications", "business_instructions")
    op.drop_column("applications", "write_directory_id")
    op.drop_column("applications", "read_directory_id")

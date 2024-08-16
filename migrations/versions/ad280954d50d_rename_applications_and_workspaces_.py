"""rename applications and workspaces column unique_name to name

Revision ID: ad280954d50d
Revises: 802c0e0c8f3f
Create Date: 2024-08-16 12:45:38.413387

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ad280954d50d"
down_revision: Union[str, None] = "802c0e0c8f3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # rename column in workspaces table from unique_name to name
    op.alter_column("workspaces", "unique_name", new_column_name="name")

    # rename column in application table from unique_name to name
    op.alter_column("applications", "unique_name", new_column_name="name")


def downgrade() -> None:
    op.alter_column("workspaces", "name", new_column_name="unique_name")
    op.alter_column("applications", "name", new_column_name="unique_name")

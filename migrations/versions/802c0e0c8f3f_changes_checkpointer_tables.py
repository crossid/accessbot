"""changes checkpointer tables

Revision ID: 802c0e0c8f3f
Revises: 75a1807159c8
Create Date: 2024-08-07 18:24:53.211230

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "802c0e0c8f3f"
down_revision: Union[str, None] = "75a1807159c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "checkpoints_writes",
        sa.Column("workspace_id", sa.String(length=10), nullable=False),
        sa.Column("thread_id", sa.String(length=10), nullable=False),
        sa.Column("checkpoint_ns", sa.String(), nullable=False),
        sa.Column("checkpoint_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("blob", sa.LargeBinary(), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
        ),
        sa.PrimaryKeyConstraint(
            "workspace_id",
            "thread_id",
            "checkpoint_ns",
            "checkpoint_id",
            "task_id",
            "idx",
        ),
    )
    op.add_column(
        "checkpoints", sa.Column("checkpoint_ns", sa.String(), nullable=False)
    )
    op.add_column(
        "checkpoints", sa.Column("checkpoint_id", sa.String(), nullable=False)
    )
    op.add_column(
        "checkpoints", sa.Column("parent_checkpoint_id", sa.String(), nullable=True)
    )
    op.drop_column("checkpoints", "parent_ts")
    op.drop_column("checkpoints", "thread_ts")
    # ### end Alembic commands ###


def downgrade() -> None:
    op.add_column(
        "checkpoints",
        sa.Column(
            "thread_ts", postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "checkpoints",
        sa.Column(
            "parent_ts", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
    )
    op.drop_column("checkpoints", "parent_checkpoint_id")
    op.drop_column("checkpoints", "checkpoint_id")
    op.drop_column("checkpoints", "checkpoint_ns")
    op.drop_table("checkpoints_writes")
    # ### end Alembic commands ###

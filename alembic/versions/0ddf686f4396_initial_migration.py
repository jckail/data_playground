"""Initial migration

Revision ID: 0ddf686f4396
Revises: 78e0f95dd6e8
Create Date: 2024-08-17 03:19:44.323735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ddf686f4396'
down_revision: Union[str, None] = '78e0f95dd6e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the request_response_logs table
    op.drop_table('request_response_logs')


def downgrade() -> None:
    # Recreate the table in the downgrade step if needed, using the original definition
    op.create_table('request_response_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('method', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('request_body', sa.Text(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('partition_key', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'partition_key'),
        postgresql_partition_by='RANGE (partition_key)'  # original partitioning strategy
    )
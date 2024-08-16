"""Initial migration

Revision ID: 4927d8d093c9
Revises: 9f9eed7f86e8
Create Date: 2024-08-16 23:23:26.319490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4927d8d093c9'
down_revision: Union[str, None] = '9f9eed7f86e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users_p_2024_08_13')
    op.drop_table('users_p_2024_08_11')
    op.drop_table('users_p_2024_08_10')
    op.drop_table('users_p_2024_08_12')
    op.drop_table('users_p_2024_08_16')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users_p_2024_08_16',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('status', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('created_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('deactivated_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('event_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('partition_key', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', 'partition_key', name='users_p_2024_08_16_pkey')
    )
    op.create_table('users_p_2024_08_12',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('status', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('created_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('deactivated_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('event_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('partition_key', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', 'partition_key', name='users_p_2024_08_12_pkey')
    )
    op.create_table('users_p_2024_08_10',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('status', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('created_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('deactivated_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('event_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('partition_key', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', 'partition_key', name='users_p_2024_08_10_pkey')
    )
    op.create_table('users_p_2024_08_11',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('status', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('created_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('deactivated_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('event_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('partition_key', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', 'partition_key', name='users_p_2024_08_11_pkey')
    )
    op.create_table('users_p_2024_08_13',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('status', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('created_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('deactivated_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('event_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('partition_key', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', 'partition_key', name='users_p_2024_08_13_pkey')
    )
    # ### end Alembic commands ###

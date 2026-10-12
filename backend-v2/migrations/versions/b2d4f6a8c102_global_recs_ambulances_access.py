"""global recommendations/alerts, ambulances, access requests, must_change_password

Revision ID: b2d4f6a8c102
Revises: a1c3d5e7f901
Create Date: 2026-10-12 11:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d4f6a8c102'
down_revision: Union[str, None] = 'a1c3d5e7f901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('recommendations') as batch:
        batch.add_column(sa.Column('is_global', sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table('alerts') as batch:
        batch.add_column(sa.Column('is_global', sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()))

    # Backfill: incident-wide agent outputs created before this migration.
    op.execute("UPDATE recommendations SET is_global = TRUE WHERE agent_id IN ('AG-1','AG-2','AG-8')"
               if op.get_bind().dialect.name == 'postgresql'
               else "UPDATE recommendations SET is_global = 1 WHERE agent_id IN ('AG-1','AG-2','AG-8')")

    op.create_table(
        'ambulances',
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('hospital_id', sa.Uuid(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('AVAILABLE', 'DISPATCHED', 'OFFLINE', name='ambulancestatusenum', native_enum=False, length=20), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id']),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ambulances_agency_id'), 'ambulances', ['agency_id'], unique=False)

    op.create_table(
        'access_requests',
        sa.Column('kind', sa.Enum('SIGNUP', 'RESET', name='accessrequestkind', native_enum=False, length=20), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='accessrequeststatus', native_enum=False, length=20), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=True),
        sa.Column('agency_text', sa.String(length=200), nullable=True),
        sa.Column('requested_role', sa.String(length=20), nullable=True),
        sa.Column('decided_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_access_requests_kind'), 'access_requests', ['kind'], unique=False)
    op.create_index(op.f('ix_access_requests_status'), 'access_requests', ['status'], unique=False)
    op.create_index(op.f('ix_access_requests_email'), 'access_requests', ['email'], unique=False)


def downgrade() -> None:
    op.drop_table('access_requests')
    op.drop_table('ambulances')
    with op.batch_alter_table('users') as batch:
        batch.drop_column('must_change_password')
    with op.batch_alter_table('alerts') as batch:
        batch.drop_column('is_global')
    with op.batch_alter_table('recommendations') as batch:
        batch.drop_column('is_global')

"""console fields: recommendation severity/evidence/details, citizen report verification fields

Revision ID: a1c3d5e7f901
Revises: e7f4e236fb70
Create Date: 2026-10-12 10:40:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c3d5e7f901'
down_revision: Union[str, None] = 'e7f4e236fb70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('recommendations') as batch:
        batch.add_column(sa.Column('severity', sa.Float(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('evidence_json', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch.add_column(sa.Column('details_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    with op.batch_alter_table('citizen_reports') as batch:
        batch.add_column(sa.Column('claimed_severity', sa.Float(), nullable=False, server_default='0.5'))
        batch.add_column(sa.Column('flagged_for_review', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('event_id', sa.Uuid(), nullable=True))
        batch.create_foreign_key('fk_citizen_reports_event_id', 'events', ['event_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('citizen_reports') as batch:
        batch.drop_constraint('fk_citizen_reports_event_id', type_='foreignkey')
        batch.drop_column('event_id')
        batch.drop_column('flagged_for_review')
        batch.drop_column('claimed_severity')
    with op.batch_alter_table('recommendations') as batch:
        batch.drop_column('details_json')
        batch.drop_column('evidence_json')
        batch.drop_column('severity')

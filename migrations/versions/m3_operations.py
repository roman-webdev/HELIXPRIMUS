"""Separate internal notes from customer messages."""
from alembic import op
import sqlalchemy as sa
revision = 'm3_operations'
down_revision = 'm2_workspace'
branch_labels = None
depends_on = None
def upgrade():
    op.create_table('internal_notes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_internal_notes_conversation_id', 'internal_notes', ['conversation_id'])
def downgrade():
    op.drop_table('internal_notes')

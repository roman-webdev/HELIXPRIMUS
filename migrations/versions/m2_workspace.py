"""M2 conversation workspace fields."""
from alembic import op
import sqlalchemy as sa
revision = 'm2_workspace'
down_revision = '3d4132740c4e'
branch_labels = None
depends_on = None
def upgrade():
    with op.batch_alter_table('conversations') as batch:
        batch.add_column(sa.Column('status', sa.String(20), nullable=False, server_default='New'))
        batch.add_column(sa.Column('priority', sa.String(20), nullable=False, server_default='Medium'))
        batch.add_column(sa.Column('assignee', sa.String(100), nullable=False, server_default='Unassigned'))
        batch.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.execute('UPDATE conversations SET updated_at = created_at')
    with op.batch_alter_table('conversations') as batch:
        batch.alter_column('updated_at', existing_type=sa.DateTime(timezone=True), nullable=False)
def downgrade():
    with op.batch_alter_table('conversations') as batch:
        for name in ('status', 'priority', 'assignee', 'updated_at', 'resolved_at'):
            batch.drop_column(name)

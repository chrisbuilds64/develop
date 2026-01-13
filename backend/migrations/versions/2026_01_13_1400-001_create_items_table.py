"""create_items_table

Revision ID: 001
Revises:
Create Date: 2026-01-13 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create items table"""
    op.create_table(
        'items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for common queries
    op.create_index(op.f('ix_items_id'), 'items', ['id'], unique=False)
    op.create_index(op.f('ix_items_owner_id'), 'items', ['owner_id'], unique=False)
    op.create_index(op.f('ix_items_content_type'), 'items', ['content_type'], unique=False)
    op.create_index(op.f('ix_items_deleted_at'), 'items', ['deleted_at'], unique=False)


def downgrade() -> None:
    """Drop items table"""
    op.drop_index(op.f('ix_items_deleted_at'), table_name='items')
    op.drop_index(op.f('ix_items_content_type'), table_name='items')
    op.drop_index(op.f('ix_items_owner_id'), table_name='items')
    op.drop_index(op.f('ix_items_id'), table_name='items')
    op.drop_table('items')

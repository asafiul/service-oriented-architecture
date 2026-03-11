"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-03-08 22:16:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=4000), nullable=True),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'ARCHIVED', name='productstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_products_status', 'products', ['status'], unique=False)

    op.create_table('promo_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('discount_type', sa.Enum('PERCENTAGE', 'FIXED_AMOUNT', name='discounttype'), nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('min_order_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=False),
        sa.Column('current_uses', sa.Integer(), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )


def downgrade() -> None:
    op.drop_table('promo_codes')
    op.drop_index('idx_products_status', table_name='products')
    op.drop_table('products')
    op.execute('DROP TYPE IF EXISTS discounttype')
    op.execute('DROP TYPE IF EXISTS productstatus')

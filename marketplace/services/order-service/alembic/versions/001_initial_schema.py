"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-03-08 22:19:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('CREATED', 'PAYMENT_PENDING', 'PAID', 'SHIPPED', 'COMPLETED', 'CANCELED', name='orderstatus'), nullable=False),
        sa.Column('promo_code_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price_at_order', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('user_operations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation_type', sa.Enum('CREATE_ORDER', 'UPDATE_ORDER', name='operationtype'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_operations_user_type', 'user_operations', ['user_id', 'operation_type'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_user_operations_user_type', table_name='user_operations')
    op.drop_table('user_operations')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.execute('DROP TYPE IF EXISTS operationtype')
    op.execute('DROP TYPE IF EXISTS orderstatus')

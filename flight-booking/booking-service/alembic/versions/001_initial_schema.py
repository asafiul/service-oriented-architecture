"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-03-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bookings table
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('flight_id', sa.Integer(), nullable=False),
        sa.Column('passenger_name', sa.String(length=200), nullable=False),
        sa.Column('passenger_email', sa.String(length=200), nullable=False),
        sa.Column('seat_count', sa.Integer(), nullable=False),
        sa.Column('total_price', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('CONFIRMED', 'CANCELLED', name='bookingstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('seat_count > 0', name='check_seat_count_positive'),
        sa.CheckConstraint('total_price > 0', name='check_total_price_positive'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)
    op.create_index(op.f('ix_bookings_user_id'), 'bookings', ['user_id'], unique=False)
    op.create_index(op.f('ix_bookings_flight_id'), 'bookings', ['flight_id'], unique=False)
    op.create_index(op.f('ix_bookings_status'), 'bookings', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bookings_status'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_flight_id'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_user_id'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_id'), table_name='bookings')
    op.drop_table('bookings')
    op.execute('DROP TYPE IF EXISTS bookingstatus')

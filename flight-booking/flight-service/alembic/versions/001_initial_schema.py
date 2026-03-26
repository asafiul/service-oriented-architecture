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
    # Create flights table
    op.create_table(
        'flights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flight_number', sa.String(length=10), nullable=False),
        sa.Column('airline', sa.String(length=100), nullable=False),
        sa.Column('origin', sa.String(length=3), nullable=False),
        sa.Column('destination', sa.String(length=3), nullable=False),
        sa.Column('departure_time', sa.DateTime(), nullable=False),
        sa.Column('arrival_time', sa.DateTime(), nullable=False),
        sa.Column('total_seats', sa.Integer(), nullable=False),
        sa.Column('available_seats', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('SCHEDULED', 'DEPARTED', 'CANCELLED', 'COMPLETED', name='flightstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('total_seats > 0', name='check_total_seats_positive'),
        sa.CheckConstraint('available_seats >= 0', name='check_available_seats_non_negative'),
        sa.CheckConstraint('available_seats <= total_seats', name='check_available_seats_lte_total'),
        sa.CheckConstraint('price > 0', name='check_price_positive'),
        sa.CheckConstraint('arrival_time > departure_time', name='check_arrival_after_departure'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flight_number', 'departure_time', name='uq_flight_number_departure')
    )
    op.create_index(op.f('ix_flights_id'), 'flights', ['id'], unique=False)
    op.create_index(op.f('ix_flights_flight_number'), 'flights', ['flight_number'], unique=False)
    op.create_index(op.f('ix_flights_origin'), 'flights', ['origin'], unique=False)
    op.create_index(op.f('ix_flights_destination'), 'flights', ['destination'], unique=False)
    op.create_index(op.f('ix_flights_departure_time'), 'flights', ['departure_time'], unique=False)
    op.create_index(op.f('ix_flights_status'), 'flights', ['status'], unique=False)

    # Create seat_reservations table
    op.create_table(
        'seat_reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flight_id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.String(length=100), nullable=False),
        sa.Column('seat_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'RELEASED', 'EXPIRED', name='reservationstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('seat_count > 0', name='check_seat_count_positive'),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id')
    )
    op.create_index(op.f('ix_seat_reservations_id'), 'seat_reservations', ['id'], unique=False)
    op.create_index(op.f('ix_seat_reservations_flight_id'), 'seat_reservations', ['flight_id'], unique=False)
    op.create_index(op.f('ix_seat_reservations_booking_id'), 'seat_reservations', ['booking_id'], unique=False)
    op.create_index(op.f('ix_seat_reservations_status'), 'seat_reservations', ['status'], unique=False)

    # Insert sample data
    op.execute("""
        INSERT INTO flights (flight_number, airline, origin, destination, departure_time, arrival_time, total_seats, available_seats, price, status, created_at, updated_at)
        VALUES 
        ('SU1234', 'Aeroflot', 'SVO', 'LED', '2026-04-01 10:00:00', '2026-04-01 11:30:00', 180, 180, 5000.0, 'SCHEDULED', NOW(), NOW()),
        ('SU5678', 'Aeroflot', 'SVO', 'LED', '2026-04-01 14:00:00', '2026-04-01 15:30:00', 180, 150, 5500.0, 'SCHEDULED', NOW(), NOW()),
        ('S71001', 'S7 Airlines', 'VKO', 'LED', '2026-04-01 09:00:00', '2026-04-01 10:30:00', 150, 120, 4500.0, 'SCHEDULED', NOW(), NOW()),
        ('SU2345', 'Aeroflot', 'LED', 'SVO', '2026-04-02 12:00:00', '2026-04-02 13:30:00', 180, 180, 5000.0, 'SCHEDULED', NOW(), NOW()),
        ('UT100', 'UTair', 'SVO', 'KZN', '2026-04-01 08:00:00', '2026-04-01 09:30:00', 120, 100, 3500.0, 'SCHEDULED', NOW(), NOW())
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_seat_reservations_status'), table_name='seat_reservations')
    op.drop_index(op.f('ix_seat_reservations_booking_id'), table_name='seat_reservations')
    op.drop_index(op.f('ix_seat_reservations_flight_id'), table_name='seat_reservations')
    op.drop_index(op.f('ix_seat_reservations_id'), table_name='seat_reservations')
    op.drop_table('seat_reservations')
    
    op.drop_index(op.f('ix_flights_status'), table_name='flights')
    op.drop_index(op.f('ix_flights_departure_time'), table_name='flights')
    op.drop_index(op.f('ix_flights_destination'), table_name='flights')
    op.drop_index(op.f('ix_flights_origin'), table_name='flights')
    op.drop_index(op.f('ix_flights_flight_number'), table_name='flights')
    op.drop_index(op.f('ix_flights_id'), table_name='flights')
    op.drop_table('flights')
    
    op.execute('DROP TYPE IF EXISTS reservationstatus')
    op.execute('DROP TYPE IF EXISTS flightstatus')

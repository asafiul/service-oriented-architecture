from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base


class FlightStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    DEPARTED = "DEPARTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class Flight(Base):
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String(10), nullable=False, index=True)
    airline = Column(String(100), nullable=False)
    origin = Column(String(3), nullable=False, index=True)  # IATA код
    destination = Column(String(3), nullable=False, index=True)  # IATA код
    departure_time = Column(DateTime, nullable=False, index=True)
    arrival_time = Column(DateTime, nullable=False)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(Enum(FlightStatus), nullable=False, default=FlightStatus.SCHEDULED, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reservations = relationship("SeatReservation", back_populates="flight")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('total_seats > 0', name='check_total_seats_positive'),
        CheckConstraint('available_seats >= 0', name='check_available_seats_non_negative'),
        CheckConstraint('available_seats <= total_seats', name='check_available_seats_lte_total'),
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('arrival_time > departure_time', name='check_arrival_after_departure'),
        UniqueConstraint('flight_number', 'departure_time', name='uq_flight_number_departure'),
    )


class SeatReservation(Base):
    __tablename__ = "seat_reservations"
    
    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False, index=True)
    booking_id = Column(String(100), nullable=False, unique=True, index=True)  # ID из Booking Service
    seat_count = Column(Integer, nullable=False)
    status = Column(Enum(ReservationStatus), nullable=False, default=ReservationStatus.ACTIVE, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    flight = relationship("Flight", back_populates="reservations")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('seat_count > 0', name='check_seat_count_positive'),
    )

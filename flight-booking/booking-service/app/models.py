from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, CheckConstraint
from datetime import datetime
import enum
from .database import Base


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    flight_id = Column(Integer, nullable=False, index=True)  # Reference to Flight Service
    passenger_name = Column(String(200), nullable=False)
    passenger_email = Column(String(200), nullable=False)
    seat_count = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)  # Snapshot at booking time
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.CONFIRMED, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('seat_count > 0', name='check_seat_count_positive'),
        CheckConstraint('total_price > 0', name='check_total_price_positive'),
    )

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class FlightCreate(BaseModel):
    flight_number: str = Field(..., min_length=2, max_length=10, description="Номер рейса (например, SU1234)")
    airline: str = Field(..., min_length=1, max_length=100, description="Авиакомпания")
    origin: str = Field(..., min_length=3, max_length=3, description="Аэропорт вылета (IATA код)")
    destination: str = Field(..., min_length=3, max_length=3, description="Аэропорт прилета (IATA код)")
    departure_time: datetime = Field(..., description="Время вылета")
    arrival_time: datetime = Field(..., description="Время прилета")
    total_seats: int = Field(..., gt=0, description="Общее количество мест")
    price: float = Field(..., gt=0, description="Цена билета")


class FlightResponse(BaseModel):
    id: int
    flight_number: str
    airline: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    price: float
    status: str


class BookingCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    flight_id: int = Field(..., gt=0)
    passenger_name: str = Field(..., min_length=1, max_length=200)
    passenger_email: EmailStr
    seat_count: int = Field(..., gt=0)


class BookingResponse(BaseModel):
    id: int
    user_id: int
    flight_id: int
    passenger_name: str
    passenger_email: str
    seat_count: int
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

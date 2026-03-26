from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import grpc
import logging
import sys

from .database import get_db
from .models import Booking, BookingStatus
from .schemas import BookingCreate, BookingResponse, FlightResponse, FlightCreate
from .flight_client import flight_client
from .circuit_breaker import flight_service_circuit_breaker
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Flight Booking Service",
    description="REST API for flight booking system",
    version="1.0.0"
)


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "service": "Booking Service",
        "status": "running",
        "circuit_breaker_state": flight_service_circuit_breaker.get_state()
    }


@app.get("/flights", response_model=List[FlightResponse])
def search_flights(
    origin: str = Query(..., description="Origin airport IATA code"),
    destination: str = Query(..., description="Destination airport IATA code"),
    date: Optional[str] = Query(None, description="Flight date (YYYY-MM-DD)")
):
    """
    Search flights by route and optional date
    Proxies to Flight Service SearchFlights
    """
    try:
        # Parse date if provided
        flight_date = None
        if date:
            try:
                flight_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Call Flight Service
        flights = flight_client.search_flights(origin, destination, flight_date)
        return flights
        
    except grpc.RpcError as e:
        logger.error(f"gRPC error: {e.code()} - {e.details()}")
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            raise HTTPException(status_code=500, detail="Service authentication failed")
        raise HTTPException(status_code=500, detail=f"Flight service error: {e.details()}")
    except Exception as e:
        logger.error(f"Error searching flights: {e}")
        if "503" in str(e):
            raise HTTPException(status_code=503, detail="Flight Service temporarily unavailable")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flights/{flight_id}", response_model=FlightResponse)
def get_flight(flight_id: int):
    """
    Get flight by ID
    Proxies to Flight Service GetFlight
    """
    try:
        flight = flight_client.get_flight(flight_id)
        return flight
        
    except grpc.RpcError as e:
        logger.error(f"gRPC error: {e.code()} - {e.details()}")
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found")
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            raise HTTPException(status_code=500, detail="Service authentication failed")
        raise HTTPException(status_code=500, detail=f"Flight service error: {e.details()}")
    except Exception as e:
        logger.error(f"Error getting flight: {e}")
        if "503" in str(e):
            raise HTTPException(status_code=503, detail="Flight Service temporarily unavailable")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flights", response_model=dict, status_code=201)
def create_flight(flight_data: FlightCreate):
    """
    Create a new flight (Admin operation)
    
    Создает новый рейс в Flight Service.
    Доступно для администраторов для добавления новых рейсов в систему.
    """
    try:
        # Validate times
        if flight_data.arrival_time <= flight_data.departure_time:
            raise HTTPException(
                status_code=400,
                detail="Arrival time must be after departure time"
            )
        
        # Create flight
        flight_id = flight_client.create_flight({
            'flight_number': flight_data.flight_number,
            'airline': flight_data.airline,
            'origin': flight_data.origin.upper(),
            'destination': flight_data.destination.upper(),
            'departure_time': flight_data.departure_time,
            'arrival_time': flight_data.arrival_time,
            'total_seats': flight_data.total_seats,
            'price': flight_data.price
        })
        
        logger.info(f"Flight created: {flight_id}")
        
        return {
            "id": flight_id,
            "message": f"Flight {flight_data.flight_number} created successfully",
            "flight_number": flight_data.flight_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating flight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/flights/{flight_id}/status")
def update_flight_status(
    flight_id: int,
    status: str = Query(..., description="Новый статус: SCHEDULED, DEPARTED, CANCELLED, COMPLETED")
):
    """
    Изменить статус рейса (Admin operation)
    
    Доступные статусы:
    - SCHEDULED - Запланирован
    - DEPARTED - Вылетел
    - CANCELLED - Отменен
    - COMPLETED - Завершен
    
    После изменения статуса кеш автоматически инвалидируется.
    """
    import psycopg2
    
    # Валидация статуса
    valid_statuses = ['SCHEDULED', 'DEPARTED', 'CANCELLED', 'COMPLETED']
    if status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    try:
        conn = psycopg2.connect(
            host="flight-db",
            database="flight_db",
            user="flight_user",
            password="flight_pass"
        )
        
        cur = conn.cursor()
        
        # Проверить существование рейса
        cur.execute("SELECT id, flight_number, status FROM flights WHERE id = %s", (flight_id,))
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found")
        
        old_status = result[2]
        
        # Обновить статус
        cur.execute(
            "UPDATE flights SET status = %s, updated_at = NOW() WHERE id = %s",
            (status.upper(), flight_id)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Flight {flight_id} status changed: {old_status} → {status.upper()}")
        
        return {
            "id": flight_id,
            "old_status": old_status,
            "new_status": status.upper(),
            "message": f"Flight status updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flight status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(booking_data: BookingCreate, db: Session = Depends(get_db)):
    """
    Create a new booking
    
    Flow:
    1. Get flight information (price)
    2. Reserve seats via Flight Service
    3. Create booking record
    """
    try:
        # Step 1: Get flight information
        logger.info(f"Creating booking for flight {booking_data.flight_id}")
        flight = flight_client.get_flight(booking_data.flight_id)
        
        # Step 2: Reserve seats (idempotent with booking_id)
        # Generate booking_id before reservation for idempotency
        temp_booking_id = f"temp_{booking_data.user_id}_{booking_data.flight_id}_{int(datetime.utcnow().timestamp())}"
        
        try:
            success = flight_client.reserve_seats(
                flight_id=booking_data.flight_id,
                seat_count=booking_data.seat_count,
                booking_id=temp_booking_id
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to reserve seats")
                
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
                raise HTTPException(status_code=400, detail="Not enough available seats")
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(status_code=404, detail=f"Flight {booking_data.flight_id} not found")
            raise
        
        # Step 3: Calculate price and create booking
        total_price = booking_data.seat_count * flight.price
        
        booking = Booking(
            user_id=booking_data.user_id,
            flight_id=booking_data.flight_id,
            passenger_name=booking_data.passenger_name,
            passenger_email=booking_data.passenger_email,
            seat_count=booking_data.seat_count,
            total_price=total_price,
            status=BookingStatus.CONFIRMED
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Update reservation with actual booking ID
        # Note: In production, you might want to update the reservation
        # For now, we use temp_booking_id which is already unique
        
        logger.info(f"Booking created: {booking.id}")
        return booking
        
    except HTTPException:
        raise
    except grpc.RpcError as e:
        db.rollback()
        logger.error(f"gRPC error during booking: {e.code()} - {e.details()}")
        raise HTTPException(status_code=500, detail=f"Flight service error: {e.details()}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating booking: {e}")
        if "503" in str(e):
            raise HTTPException(status_code=503, detail="Flight Service temporarily unavailable")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Get booking by ID"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found")
    
    return booking


@app.get("/bookings", response_model=List[BookingResponse])
def list_bookings(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db)
):
    """List bookings, optionally filtered by user_id"""
    query = db.query(Booking)
    
    if user_id:
        query = query.filter(Booking.user_id == user_id)
    
    bookings = query.order_by(Booking.created_at.desc()).all()
    return bookings


@app.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    """
    Cancel a booking
    
    Flow:
    1. Check booking exists and is CONFIRMED
    2. Release reservation via Flight Service
    3. Update booking status to CANCELLED
    """
    try:
        # Step 1: Get booking
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found")
        
        if booking.status != BookingStatus.CONFIRMED:
            raise HTTPException(status_code=400, detail=f"Booking is already {booking.status}")
        
        # Step 2: Release reservation
        temp_booking_id = f"temp_{booking.user_id}_{booking.flight_id}_{int(booking.created_at.timestamp())}"
        
        try:
            flight_client.release_reservation(temp_booking_id)
        except grpc.RpcError as e:
            logger.warning(f"Failed to release reservation: {e.details()}")
            # Continue with cancellation even if release fails
        
        # Step 3: Update booking status
        booking.status = BookingStatus.CANCELLED
        db.commit()
        db.refresh(booking)
        
        logger.info(f"Booking cancelled: {booking_id}")
        return booking
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelling booking: {e}")
        if "503" in str(e):
            raise HTTPException(status_code=503, detail="Flight Service temporarily unavailable")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "Booking Service",
        "circuit_breaker": {
            "state": flight_service_circuit_breaker.get_state(),
            "failure_threshold": settings.circuit_breaker_failure_threshold,
            "timeout": settings.circuit_breaker_timeout
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

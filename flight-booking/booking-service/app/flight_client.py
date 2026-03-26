import grpc
import logging
from datetime import datetime
from typing import List, Optional
from google.protobuf.timestamp_pb2 import Timestamp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

import flight_service_pb2
import flight_service_pb2_grpc
from .config import settings
from .circuit_breaker import flight_service_circuit_breaker, CircuitBreakerError
from .schemas import FlightResponse

logger = logging.getLogger(__name__)


class FlightServiceClient:
    """Client for Flight Service with retry and circuit breaker"""
    
    def __init__(self):
        self.host = settings.flight_service_host
        self.port = settings.flight_service_port
        self.api_key = settings.flight_service_api_key
        self.channel = None
        self.stub = None
        self._connect()
    
    def _connect(self):
        """Establish gRPC connection"""
        address = f"{self.host}:{self.port}"
        self.channel = grpc.insecure_channel(address)
        self.stub = flight_service_pb2_grpc.FlightServiceStub(self.channel)
        logger.info(f"Connected to Flight Service at {address}")
    
    def _get_metadata(self):
        """Get metadata with API key for authentication"""
        return [('x-api-key', self.api_key)]
    
    def _should_retry(self, exception):
        """Determine if exception should trigger retry"""
        if isinstance(exception, grpc.RpcError):
            code = exception.code()
            # Retry only for transient errors
            return code in [
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.DEADLINE_EXCEEDED
            ]
        return False
    
    def _proto_to_flight_response(self, proto_flight) -> FlightResponse:
        """Convert protobuf Flight to FlightResponse"""
        status_map = {
            flight_service_pb2.SCHEDULED: "SCHEDULED",
            flight_service_pb2.DEPARTED: "DEPARTED",
            flight_service_pb2.CANCELLED: "CANCELLED",
            flight_service_pb2.COMPLETED: "COMPLETED",
        }
        
        return FlightResponse(
            id=proto_flight.id,
            flight_number=proto_flight.flight_number,
            airline=proto_flight.airline,
            origin=proto_flight.origin,
            destination=proto_flight.destination,
            departure_time=proto_flight.departure_time.ToDatetime(),
            arrival_time=proto_flight.arrival_time.ToDatetime(),
            total_seats=proto_flight.total_seats,
            available_seats=proto_flight.available_seats,
            price=proto_flight.price,
            status=status_map.get(proto_flight.status, "SCHEDULED")
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=0.1, max=0.4),
        retry=retry_if_exception_type(grpc.RpcError),
        before_sleep=lambda retry_state: logger.info(
            f"Retrying Flight Service call (attempt {retry_state.attempt_number})..."
        )
    )
    def _search_flights_with_retry(self, request, metadata):
        """Search flights with retry logic"""
        try:
            return self.stub.SearchFlights(request, metadata=metadata, timeout=5)
        except grpc.RpcError as e:
            if self._should_retry(e):
                logger.warning(f"Retryable error: {e.code()}")
                raise
            else:
                logger.error(f"Non-retryable error: {e.code()} - {e.details()}")
                raise
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        date: Optional[datetime] = None
    ) -> List[FlightResponse]:
        """Search flights by route and optional date"""
        logger.info(f"Searching flights: {origin} -> {destination}")
        
        def _call():
            request = flight_service_pb2.SearchFlightsRequest(
                origin=origin,
                destination=destination
            )
            
            if date:
                ts = Timestamp()
                ts.FromDatetime(date)
                request.date.CopyFrom(ts)
            
            try:
                response = self._search_flights_with_retry(request, self._get_metadata())
                return [self._proto_to_flight_response(f) for f in response.flights]
            except RetryError as e:
                logger.error(f"All retry attempts failed: {e}")
                raise e.last_attempt.exception()
        
        try:
            return flight_service_circuit_breaker.call(_call)
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker prevented call: {e}")
            raise Exception("Flight Service temporarily unavailable (503)")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=0.1, max=0.4),
        retry=retry_if_exception_type(grpc.RpcError),
        before_sleep=lambda retry_state: logger.info(
            f"Retrying GetFlight (attempt {retry_state.attempt_number})..."
        )
    )
    def _get_flight_with_retry(self, request, metadata):
        """Get flight with retry logic"""
        try:
            return self.stub.GetFlight(request, metadata=metadata, timeout=5)
        except grpc.RpcError as e:
            if self._should_retry(e):
                logger.warning(f"Retryable error: {e.code()}")
                raise
            else:
                logger.error(f"Non-retryable error: {e.code()} - {e.details()}")
                raise
    
    def get_flight(self, flight_id: int) -> FlightResponse:
        """Get flight by ID"""
        logger.info(f"Getting flight: {flight_id}")
        
        def _call():
            request = flight_service_pb2.GetFlightRequest(flight_id=flight_id)
            
            try:
                response = self._get_flight_with_retry(request, self._get_metadata())
                return self._proto_to_flight_response(response)
            except RetryError as e:
                logger.error(f"All retry attempts failed: {e}")
                raise e.last_attempt.exception()
        
        try:
            return flight_service_circuit_breaker.call(_call)
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker prevented call: {e}")
            raise Exception("Flight Service temporarily unavailable (503)")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=0.1, max=0.4),
        retry=retry_if_exception_type(grpc.RpcError),
        before_sleep=lambda retry_state: logger.info(
            f"Retrying ReserveSeats (attempt {retry_state.attempt_number})..."
        )
    )
    def _reserve_seats_with_retry(self, request, metadata):
        """Reserve seats with retry logic (idempotent)"""
        try:
            return self.stub.ReserveSeats(request, metadata=metadata, timeout=5)
        except grpc.RpcError as e:
            if self._should_retry(e):
                logger.warning(f"Retryable error: {e.code()}")
                raise
            else:
                logger.error(f"Non-retryable error: {e.code()} - {e.details()}")
                raise
    
    def reserve_seats(self, flight_id: int, seat_count: int, booking_id: str) -> bool:
        """Reserve seats (idempotent operation)"""
        logger.info(f"Reserving {seat_count} seats on flight {flight_id} for booking {booking_id}")
        
        def _call():
            request = flight_service_pb2.ReserveSeatsRequest(
                flight_id=flight_id,
                seat_count=seat_count,
                booking_id=booking_id
            )
            
            try:
                response = self._reserve_seats_with_retry(request, self._get_metadata())
                return response.success
            except RetryError as e:
                logger.error(f"All retry attempts failed: {e}")
                raise e.last_attempt.exception()
        
        try:
            return flight_service_circuit_breaker.call(_call)
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker prevented call: {e}")
            raise Exception("Flight Service temporarily unavailable (503)")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=0.1, max=0.4),
        retry=retry_if_exception_type(grpc.RpcError),
        before_sleep=lambda retry_state: logger.info(
            f"Retrying ReleaseReservation (attempt {retry_state.attempt_number})..."
        )
    )
    def _release_reservation_with_retry(self, request, metadata):
        """Release reservation with retry logic"""
        try:
            return self.stub.ReleaseReservation(request, metadata=metadata, timeout=5)
        except grpc.RpcError as e:
            if self._should_retry(e):
                logger.warning(f"Retryable error: {e.code()}")
                raise
            else:
                logger.error(f"Non-retryable error: {e.code()} - {e.details()}")
                raise
    
    def release_reservation(self, booking_id: str):
        """Release reservation and return seats"""
        logger.info(f"Releasing reservation for booking {booking_id}")
        
        def _call():
            request = flight_service_pb2.ReleaseReservationRequest(booking_id=booking_id)
            
            try:
                self._release_reservation_with_retry(request, self._get_metadata())
            except RetryError as e:
                logger.error(f"All retry attempts failed: {e}")
                raise e.last_attempt.exception()
        
        try:
            flight_service_circuit_breaker.call(_call)
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker prevented call: {e}")
            raise Exception("Flight Service temporarily unavailable (503)")
    
    def create_flight(self, flight_data: dict) -> int:
        """Create a new flight (admin operation)"""
        logger.info(f"Creating flight: {flight_data['flight_number']}")
        
        # Напрямую вставляем в БД Flight Service через SQL
        # В реальной системе это был бы отдельный gRPC метод CreateFlight
        # Для демонстрации используем прямой доступ к БД
        import psycopg2
        
        conn = psycopg2.connect(
            host="flight-db",
            database="flight_db",
            user="flight_user",
            password="flight_pass"
        )
        
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO flights
                (flight_number, airline, origin, destination, departure_time, arrival_time,
                 total_seats, available_seats, price, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'SCHEDULED', NOW(), NOW())
                RETURNING id
            """, (
                flight_data['flight_number'],
                flight_data['airline'],
                flight_data['origin'],
                flight_data['destination'],
                flight_data['departure_time'],
                flight_data['arrival_time'],
                flight_data['total_seats'],
                flight_data['total_seats'],  # available_seats = total_seats initially
                flight_data['price']
            ))
            
            flight_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            
            logger.info(f"Flight created with ID: {flight_id}")
            return flight_id
            
        finally:
            conn.close()
    
    def close(self):
        """Close gRPC channel"""
        if self.channel:
            self.channel.close()
            logger.info("Flight Service connection closed")


# Global client instance
flight_client = FlightServiceClient()

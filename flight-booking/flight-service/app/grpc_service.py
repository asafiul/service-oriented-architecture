import grpc
import json
import logging
from datetime import datetime
from concurrent import futures
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from google.protobuf import empty_pb2
from google.protobuf.timestamp_pb2 import Timestamp

import flight_service_pb2
import flight_service_pb2_grpc
from .database import SessionLocal
from .models import Flight, SeatReservation, FlightStatus, ReservationStatus
from .redis_client import cache
from .config import settings

logger = logging.getLogger(__name__)


class AuthInterceptor(grpc.ServerInterceptor):
    """Interceptor for API Key authentication"""
    
    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        api_key = metadata.get('x-api-key', '')
        
        if api_key != settings.api_key:
            logger.warning(f"Unauthorized access attempt with key: {api_key}")
            return grpc.unary_unary_rpc_method_handler(
                lambda request, context: self._unauthenticated(context)
            )
        
        return continuation(handler_call_details)
    
    def _unauthenticated(self, context):
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid API key")


class FlightServiceServicer(flight_service_pb2_grpc.FlightServiceServicer):
    
    def _flight_to_proto(self, flight: Flight) -> flight_service_pb2.Flight:
        """Convert SQLAlchemy Flight model to protobuf Flight"""
        departure_ts = Timestamp()
        departure_ts.FromDatetime(flight.departure_time)
        
        arrival_ts = Timestamp()
        arrival_ts.FromDatetime(flight.arrival_time)
        
        # Map status
        status_map = {
            FlightStatus.SCHEDULED: flight_service_pb2.SCHEDULED,
            FlightStatus.DEPARTED: flight_service_pb2.DEPARTED,
            FlightStatus.CANCELLED: flight_service_pb2.CANCELLED,
            FlightStatus.COMPLETED: flight_service_pb2.COMPLETED,
        }
        
        return flight_service_pb2.Flight(
            id=flight.id,
            flight_number=flight.flight_number,
            airline=flight.airline,
            origin=flight.origin,
            destination=flight.destination,
            departure_time=departure_ts,
            arrival_time=arrival_ts,
            total_seats=flight.total_seats,
            available_seats=flight.available_seats,
            price=flight.price,
            status=status_map.get(flight.status, flight_service_pb2.SCHEDULED)
        )
    
    def SearchFlights(self, request, context):
        """Search flights by route and optional date"""
        logger.info(f"SearchFlights: {request.origin} -> {request.destination}")
        
        # Build cache key
        date_str = ""
        if request.HasField('date'):
            date_str = request.date.ToDatetime().strftime('%Y-%m-%d')
        cache_key = f"search:{request.origin}:{request.destination}:{date_str}"
        
        # Try cache first
        cached = cache.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                response = flight_service_pb2.SearchFlightsResponse()
                for flight_data in data:
                    flight = flight_service_pb2.Flight()
                    # Reconstruct flight from cached data
                    flight.id = flight_data['id']
                    flight.flight_number = flight_data['flight_number']
                    flight.airline = flight_data['airline']
                    flight.origin = flight_data['origin']
                    flight.destination = flight_data['destination']
                    flight.total_seats = flight_data['total_seats']
                    flight.available_seats = flight_data['available_seats']
                    flight.price = flight_data['price']
                    flight.status = flight_data['status']
                    
                    dep_ts = Timestamp()
                    dep_ts.FromJsonString(flight_data['departure_time'])
                    flight.departure_time.CopyFrom(dep_ts)
                    
                    arr_ts = Timestamp()
                    arr_ts.FromJsonString(flight_data['arrival_time'])
                    flight.arrival_time.CopyFrom(arr_ts)
                    
                    response.flights.append(flight)
                
                return response
            except Exception as e:
                logger.error(f"Cache deserialization error: {e}")
        
        # Query database
        db = SessionLocal()
        try:
            query = db.query(Flight).filter(
                and_(
                    Flight.origin == request.origin,
                    Flight.destination == request.destination,
                    Flight.status == FlightStatus.SCHEDULED
                )
            )
            
            if request.HasField('date'):
                search_date = request.date.ToDatetime().date()
                query = query.filter(
                    func.date(Flight.departure_time) == search_date
                )
            
            flights = query.all()
            
            # Build response
            response = flight_service_pb2.SearchFlightsResponse()
            cache_data = []
            
            for flight in flights:
                proto_flight = self._flight_to_proto(flight)
                response.flights.append(proto_flight)
                
                # Prepare for cache
                cache_data.append({
                    'id': flight.id,
                    'flight_number': flight.flight_number,
                    'airline': flight.airline,
                    'origin': flight.origin,
                    'destination': flight.destination,
                    'departure_time': proto_flight.departure_time.ToJsonString(),
                    'arrival_time': proto_flight.arrival_time.ToJsonString(),
                    'total_seats': flight.total_seats,
                    'available_seats': flight.available_seats,
                    'price': flight.price,
                    'status': proto_flight.status
                })
            
            # Cache results
            cache.set(cache_key, json.dumps(cache_data), settings.cache_ttl_search)
            
            logger.info(f"Found {len(flights)} flights")
            return response
            
        finally:
            db.close()
    
    def GetFlight(self, request, context):
        """Get flight by ID"""
        logger.info(f"GetFlight: {request.flight_id}")
        
        # Try cache first
        cache_key = f"flight:{request.flight_id}"
        cached = cache.get(cache_key)
        
        if cached:
            try:
                data = json.loads(cached)
                flight = flight_service_pb2.Flight()
                flight.id = data['id']
                flight.flight_number = data['flight_number']
                flight.airline = data['airline']
                flight.origin = data['origin']
                flight.destination = data['destination']
                flight.total_seats = data['total_seats']
                flight.available_seats = data['available_seats']
                flight.price = data['price']
                flight.status = data['status']
                
                dep_ts = Timestamp()
                dep_ts.FromJsonString(data['departure_time'])
                flight.departure_time.CopyFrom(dep_ts)
                
                arr_ts = Timestamp()
                arr_ts.FromJsonString(data['arrival_time'])
                flight.arrival_time.CopyFrom(arr_ts)
                
                return flight
            except Exception as e:
                logger.error(f"Cache deserialization error: {e}")
        
        # Query database
        db = SessionLocal()
        try:
            flight = db.query(Flight).filter(Flight.id == request.flight_id).first()
            
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Flight {request.flight_id} not found")
            
            proto_flight = self._flight_to_proto(flight)
            
            # Cache the result
            cache_data = {
                'id': flight.id,
                'flight_number': flight.flight_number,
                'airline': flight.airline,
                'origin': flight.origin,
                'destination': flight.destination,
                'departure_time': proto_flight.departure_time.ToJsonString(),
                'arrival_time': proto_flight.arrival_time.ToJsonString(),
                'total_seats': flight.total_seats,
                'available_seats': flight.available_seats,
                'price': flight.price,
                'status': proto_flight.status
            }
            cache.set(cache_key, json.dumps(cache_data), settings.cache_ttl_flight)
            
            return proto_flight
            
        finally:
            db.close()
    
    def ReserveSeats(self, request, context):
        """Reserve seats atomically with idempotency"""
        logger.info(f"ReserveSeats: flight={request.flight_id}, seats={request.seat_count}, booking={request.booking_id}")
        
        db = SessionLocal()
        try:
            # Check for existing reservation (idempotency)
            existing = db.query(SeatReservation).filter(
                SeatReservation.booking_id == request.booking_id
            ).first()
            
            if existing:
                logger.info(f"Reservation already exists for booking {request.booking_id}")
                return flight_service_pb2.ReserveSeatsResponse(
                    reservation_id=existing.id,
                    success=True,
                    message="Reservation already exists (idempotent)"
                )
            
            # Lock the flight row for update
            flight = db.query(Flight).filter(Flight.id == request.flight_id).with_for_update().first()
            
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Flight {request.flight_id} not found")
            
            # Check availability
            if flight.available_seats < request.seat_count:
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"Not enough seats. Available: {flight.available_seats}, Requested: {request.seat_count}"
                )
            
            # Update available seats
            flight.available_seats -= request.seat_count
            
            # Create reservation
            reservation = SeatReservation(
                flight_id=request.flight_id,
                booking_id=request.booking_id,
                seat_count=request.seat_count,
                status=ReservationStatus.ACTIVE
            )
            db.add(reservation)
            
            # Commit transaction
            db.commit()
            db.refresh(reservation)
            
            # Invalidate cache
            cache.delete(f"flight:{request.flight_id}")
            cache.delete_pattern(f"search:{flight.origin}:{flight.destination}:*")
            
            logger.info(f"Reservation created: {reservation.id}")
            
            return flight_service_pb2.ReserveSeatsResponse(
                reservation_id=reservation.id,
                success=True,
                message="Seats reserved successfully"
            )
            
        except grpc.RpcError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"ReserveSeats error: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()
    
    def ReleaseReservation(self, request, context):
        """Release reservation and return seats"""
        logger.info(f"ReleaseReservation: booking={request.booking_id}")
        
        db = SessionLocal()
        try:
            # Find active reservation
            reservation = db.query(SeatReservation).filter(
                and_(
                    SeatReservation.booking_id == request.booking_id,
                    SeatReservation.status == ReservationStatus.ACTIVE
                )
            ).with_for_update().first()
            
            if not reservation:
                logger.warning(f"No active reservation found for booking {request.booking_id}")
                return empty_pb2.Empty()
            
            # Lock flight for update
            flight = db.query(Flight).filter(Flight.id == reservation.flight_id).with_for_update().first()
            
            if flight:
                # Return seats
                flight.available_seats += reservation.seat_count
            
            # Update reservation status
            reservation.status = ReservationStatus.RELEASED
            
            # Commit transaction
            db.commit()
            
            # Invalidate cache
            if flight:
                cache.delete(f"flight:{flight.id}")
                cache.delete_pattern(f"search:{flight.origin}:{flight.destination}:*")
            
            logger.info(f"Reservation released: {reservation.id}")
            
            return empty_pb2.Empty()
            
        except Exception as e:
            db.rollback()
            logger.error(f"ReleaseReservation error: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()
    
    def UpdateFlight(self, request, context):
        """Update flight information (admin operation)"""
        logger.info(f"UpdateFlight: {request.flight_id}")
        
        db = SessionLocal()
        try:
            flight = db.query(Flight).filter(Flight.id == request.flight_id).first()
            
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Flight {request.flight_id} not found")
            
            # Update fields if provided
            if request.HasField('available_seats'):
                flight.available_seats = request.available_seats
            
            if request.HasField('price'):
                flight.price = request.price
            
            if request.HasField('status'):
                status_map = {
                    flight_service_pb2.SCHEDULED: FlightStatus.SCHEDULED,
                    flight_service_pb2.DEPARTED: FlightStatus.DEPARTED,
                    flight_service_pb2.CANCELLED: FlightStatus.CANCELLED,
                    flight_service_pb2.COMPLETED: FlightStatus.COMPLETED,
                }
                flight.status = status_map.get(request.status, FlightStatus.SCHEDULED)
            
            db.commit()
            db.refresh(flight)
            
            # Invalidate cache
            cache.delete(f"flight:{request.flight_id}")
            cache.delete_pattern(f"search:{flight.origin}:{flight.destination}:*")
            
            return self._flight_to_proto(flight)
            
        except grpc.RpcError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"UpdateFlight error: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()


def serve():
    """Start gRPC server"""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[AuthInterceptor()]
    )
    
    flight_service_pb2_grpc.add_FlightServiceServicer_to_server(
        FlightServiceServicer(), server
    )
    
    server.add_insecure_port(f'[::]:{settings.grpc_port}')
    server.start()
    
    logger.info(f"gRPC server started on port {settings.grpc_port}")
    server.wait_for_termination()

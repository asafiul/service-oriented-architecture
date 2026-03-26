from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://booking_user:booking_pass@booking-db:5432/booking_db"
    
    # Flight Service gRPC
    flight_service_host: str = "flight-service"
    flight_service_port: int = 50051
    flight_service_api_key: str = "flight-service-secret-key-12345"
    
    # Retry settings
    retry_max_attempts: int = 3
    retry_initial_wait: float = 0.1  # 100ms
    retry_max_wait: float = 0.4      # 400ms
    
    # Circuit Breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 30  # seconds
    circuit_breaker_half_open_max_calls: int = 1
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    class Config:
        env_file = ".env"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://flight_user:flight_pass@flight-db:5432/flight_db"
    
    # Redis Sentinel
    redis_sentinels: str = "redis-sentinel-1:26379,redis-sentinel-2:26380,redis-sentinel-3:26381"
    redis_master_name: str = "mymaster"
    redis_password: str = ""
    
    # Cache TTL (seconds)
    cache_ttl_flight: int = 300  # 5 minutes
    cache_ttl_search: int = 300  # 5 minutes
    
    # gRPC
    grpc_port: int = 50051
    
    # Authentication
    api_key: str = "flight-service-secret-key-12345"
    
    class Config:
        env_file = ".env"


settings = Settings()

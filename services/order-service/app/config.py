from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://marketplace:marketplace@postgres-orders:5432/marketplace_orders"
    port: int = 8003
    rate_limit_minutes: int = 5
    product_service_url: str = "http://product-service:8002"
    kafka_bootstrap_servers: str = "kafka:9092"
    
    class Config:
        env_file = ".env"

settings = Settings()

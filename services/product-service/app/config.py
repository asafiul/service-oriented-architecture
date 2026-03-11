from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://marketplace:marketplace@postgres:5432/marketplace"
    port: int = 8002
    rate_limit_minutes: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()

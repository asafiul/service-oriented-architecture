from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from contextlib import asynccontextmanager
import logging
import json
from app.routers import orders
from app.exceptions import MarketplaceException
from app.kafka_producer import kafka_producer
from app.config import settings
from app.middleware.logging_middleware import LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_producer.start()
    yield
    await kafka_producer.stop()

app = FastAPI(
    title="Order Service API",
    description="Сервис управления заказами",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(LoggingMiddleware)

app.include_router(orders.router)

@app.exception_handler(MarketplaceException)
async def marketplace_exception_handler(request: Request, exc: MarketplaceException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = {}
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"][1:])
        errors[field] = error["msg"]
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Ошибка валидации входных данных",
            "details": errors
        }
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    errors = {}
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        errors[field] = error["msg"]
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Ошибка валидации входных данных",
            "details": errors
        }
    )

@app.get("/health")
async def health_check():
    return {
        "status": "OK",
        "service": "Order Service"
    }

@app.get("/")
async def root():
    return {
        "service": "Order Service",
        "version": "1.0.0",
        "description": "Сервис управления заказами"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)

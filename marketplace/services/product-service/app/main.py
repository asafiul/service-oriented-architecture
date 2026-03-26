from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import json
from app.routers import products, promo_codes
from app.exceptions import MarketplaceException
from app.config import settings
from app.middleware.logging_middleware import LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

app = FastAPI(
    title="Product Service API",
    description="Сервис управления товарами и промокодами",
    version="1.0.0"
)

app.add_middleware(LoggingMiddleware)

app.include_router(products.router)
app.include_router(promo_codes.router)

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
        "service": "Product Service"
    }

@app.get("/")
async def root():
    return {
        "service": "Product Service",
        "version": "1.0.0",
        "description": "Сервис управления товарами и промокодами"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(..., ge=1, le=999)

class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1, max_length=50)
    promo_code: Optional[str] = Field(None, pattern=r'^[A-Z0-9_]{4,20}$')

class OrderUpdate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1, max_length=50)

class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    price_at_order: Decimal

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    items: List[OrderItemResponse]
    promo_code_id: Optional[UUID]
    total_amount: Decimal
    discount_amount: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None

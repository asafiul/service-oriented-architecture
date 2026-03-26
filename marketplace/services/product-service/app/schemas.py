from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import re

class ProductStatus(str):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"

class OrderStatus(str):
    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"

class DiscountType(str):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    price: Decimal = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    category: str = Field(..., min_length=1, max_length=100)
    status: str

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Цена должна быть больше 0')
        return v

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = None

class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    price: Decimal
    stock: int
    category: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total_elements: int
    page: int
    size: int

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

class PromoCodeCreate(BaseModel):
    code: str = Field(..., pattern=r'^[A-Z0-9_]{4,20}$')
    discount_type: str
    discount_value: Decimal = Field(..., gt=0)
    min_order_amount: Decimal = Field(..., ge=0)
    max_uses: int = Field(..., ge=1)
    valid_from: datetime
    valid_until: datetime
    active: bool = True

class PromoCodeResponse(BaseModel):
    id: UUID
    code: str
    discount_type: str
    discount_value: Decimal
    min_order_amount: Decimal
    max_uses: int
    current_uses: int
    valid_from: datetime
    valid_until: datetime
    active: bool

    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None

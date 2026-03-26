from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.database import get_db
from app.generated import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    service = ProductService(db)
    product = await service.create_product(product_data)
    return ProductResponse.model_validate(product)

@router.get("", response_model=ProductListResponse)
async def get_products(
    page: int = 0,
    size: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    service = ProductService(db)
    return await service.get_products(page, size, status, category)

@router.get("/{id}", response_model=ProductResponse)
async def get_product(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ProductService(db)
    product = await service.get_product(id)
    return ProductResponse.model_validate(product)

@router.put("/{id}", response_model=ProductResponse)
async def update_product(
    id: UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = ProductService(db)
    product = await service.update_product(id, product_data)
    return ProductResponse.model_validate(product)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = ProductService(db)
    await service.delete_product(id)

@router.post("/{id}/reserve", status_code=status.HTTP_200_OK)
async def reserve_stock(
    id: UUID,
    quantity: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    service = ProductService(db)
    await service.reserve_stock(id, quantity)
    return {"status": "ok"}

@router.post("/{id}/release", status_code=status.HTTP_200_OK)
async def release_stock(
    id: UUID,
    quantity: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    service = ProductService(db)
    await service.release_stock(id, quantity)
    return {"status": "ok"}

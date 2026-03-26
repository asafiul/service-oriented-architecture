from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from app.models import Product, ProductStatus
from app.schemas import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from app.exceptions import ProductNotFoundException

class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_product(self, product_data: ProductCreate) -> Product:
        data = product_data.model_dump()
        if 'status' in data:
            status_value = data['status'].value if hasattr(data['status'], 'value') else data['status']
            data['status'] = ProductStatus(status_value)
        product = Product(**data)
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def get_product(self, product_id: UUID) -> Product:
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise ProductNotFoundException(str(product_id))
        return product

    async def get_products(
        self, 
        page: int = 0, 
        size: int = 20, 
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> ProductListResponse:
        query = select(Product)
        
        if status:
            query = query.where(Product.status == status)
        if category:
            query = query.where(Product.category == category)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total_elements = total_result.scalar()
        
        query = query.offset(page * size).limit(size)
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        return ProductListResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total_elements=total_elements,
            page=page,
            size=size
        )

    async def update_product(self, product_id: UUID, product_data: ProductUpdate) -> Product:
        product = await self.get_product(product_id)
        
        update_data = product_data.model_dump(exclude_unset=True)
        if 'status' in update_data:
            status_value = update_data['status'].value if hasattr(update_data['status'], 'value') else update_data['status']
            update_data['status'] = ProductStatus(status_value)
        
        for field, value in update_data.items():
            setattr(product, field, value)
        
        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def delete_product(self, product_id: UUID) -> None:
        product = await self.get_product(product_id)
        product.status = ProductStatus.ARCHIVED
        await self.db.commit()
    
    async def reserve_stock(self, product_id: UUID, quantity: int) -> None:
        product = await self.get_product(product_id)
        if product.stock < quantity:
            raise Exception(f"Недостаточно товара на складе")
        product.stock -= quantity
        await self.db.commit()
    
    async def release_stock(self, product_id: UUID, quantity: int) -> None:
        product = await self.get_product(product_id)
        product.stock += quantity
        await self.db.commit()

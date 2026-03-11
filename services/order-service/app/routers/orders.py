from fastapi import APIRouter, Depends, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.generated import OrderCreate, OrderResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])

def get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    order = await service.create_order(user_id, order_data)
    return OrderResponse.model_validate(order)

@router.get("/{id}", response_model=OrderResponse)
async def get_order(
    id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    order = await service.get_order(id, user_id)
    return OrderResponse.model_validate(order)

@router.post("/{id}/cancel", response_model=OrderResponse)
async def cancel_order(
    id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    order = await service.cancel_order(id, user_id)
    return OrderResponse.model_validate(order)

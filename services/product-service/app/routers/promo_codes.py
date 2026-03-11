from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.generated import PromoCodeCreate, PromoCodeResponse
from app.services.promo_service import PromoCodeService

router = APIRouter(prefix="/promo-codes", tags=["Promo Codes"])

@router.post("", response_model=PromoCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_promo_code(
    promo_data: PromoCodeCreate,
    db: AsyncSession = Depends(get_db)
):
    service = PromoCodeService(db)
    promo_code = await service.create_promo_code(promo_data)
    return PromoCodeResponse.model_validate(promo_code)

@router.get("/{code}", response_model=PromoCodeResponse)
async def get_promo_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    service = PromoCodeService(db)
    promo_code = await service.get_promo_code_by_code(code)
    return PromoCodeResponse.model_validate(promo_code)

@router.post("/{id}/increment", status_code=status.HTTP_200_OK)
async def increment_promo_usage(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = PromoCodeService(db)
    await service.increment_usage(id)
    return {"status": "ok"}

@router.post("/{id}/decrement", status_code=status.HTTP_200_OK)
async def decrement_promo_usage(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = PromoCodeService(db)
    await service.decrement_usage(id)
    return {"status": "ok"}

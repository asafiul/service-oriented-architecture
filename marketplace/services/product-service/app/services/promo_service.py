from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models import PromoCode, DiscountType
from app.generated import PromoCodeCreate

class PromoCodeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_promo_code(self, promo_data: PromoCodeCreate) -> PromoCode:
        data = promo_data.model_dump()
        if 'discount_type' in data:
            discount_value = data['discount_type'].value if hasattr(data['discount_type'], 'value') else data['discount_type']
            data['discount_type'] = DiscountType(discount_value)
        promo_code = PromoCode(**data)
        self.db.add(promo_code)
        await self.db.commit()
        await self.db.refresh(promo_code)
        return promo_code
    
    async def get_promo_code_by_code(self, code: str) -> PromoCode:
        result = await self.db.execute(
            select(PromoCode).where(PromoCode.code == code)
        )
        promo_code = result.scalar_one_or_none()
        if not promo_code:
            raise Exception(f"Промокод {code} не найден")
        return promo_code
    
    async def get_promo_code_by_id(self, promo_id: UUID) -> PromoCode:
        result = await self.db.execute(
            select(PromoCode).where(PromoCode.id == promo_id)
        )
        promo_code = result.scalar_one_or_none()
        if not promo_code:
            raise Exception(f"Промокод с ID {promo_id} не найден")
        return promo_code
    
    async def increment_usage(self, promo_id: UUID) -> None:
        result = await self.db.execute(
            select(PromoCode).where(PromoCode.id == promo_id)
        )
        promo_code = result.scalar_one_or_none()
        if promo_code:
            promo_code.current_uses += 1
            await self.db.commit()
    
    async def decrement_usage(self, promo_id: UUID) -> None:
        result = await self.db.execute(
            select(PromoCode).where(PromoCode.id == promo_id)
        )
        promo_code = result.scalar_one_or_none()
        if promo_code and promo_code.current_uses > 0:
            promo_code.current_uses -= 1
            await self.db.commit()

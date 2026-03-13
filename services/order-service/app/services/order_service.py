from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from app.models import Order, OrderItem, UserOperation, OrderStatus, OperationType
from app.generated import OrderCreate, OrderUpdate, OrderResponse
from app.exceptions import (
    OrderNotFoundException, OrderLimitExceededException, OrderHasActiveException,
    InvalidStateTransitionException, OrderOwnershipViolationException
)
from app.clients.product_client import ProductClient
from app.kafka_producer import kafka_producer
from app.config import settings

class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_client = ProductClient()

    async def _check_rate_limit(self, user_id: UUID, operation_type: OperationType) -> None:
        result = await self.db.execute(
            select(UserOperation)
            .where(
                and_(
                    UserOperation.user_id == user_id,
                    UserOperation.operation_type == operation_type
                )
            )
            .order_by(UserOperation.created_at.desc())
            .limit(1)
        )
        last_operation = result.scalar_one_or_none()
        
        if last_operation:
            time_diff = datetime.now() - last_operation.created_at.replace(tzinfo=None)
            if time_diff < timedelta(minutes=settings.rate_limit_minutes):
                raise OrderLimitExceededException(settings.rate_limit_minutes)

    async def _check_active_orders(self, user_id: UUID) -> None:
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.user_id == user_id,
                    Order.status.in_([OrderStatus.CREATED, OrderStatus.PAYMENT_PENDING])
                )
            )
        )
        active_order = result.scalar_one_or_none()
        if active_order:
            raise OrderHasActiveException()

    async def create_order(self, user_id: UUID, order_data: OrderCreate) -> Order:
        await self._check_rate_limit(user_id, OperationType.CREATE_ORDER)
        await self._check_active_orders(user_id)
        
        total_amount = Decimal(0)
        order_items_data = []
        
        for item in order_data.items:
            product = await self.product_client.get_product(item.product_id)
            
            if product['status'] != 'ACTIVE':
                raise Exception(f"Товар {item.product_id} неактивен")
            
            if product['stock'] < item.quantity:
                raise Exception(f"Недостаточно товара {item.product_id} на складе")
            
            await self.product_client.reserve_stock(item.product_id, item.quantity)
            
            price = Decimal(str(product['price']))
            total_amount += price * item.quantity
            
            order_items_data.append({
                'product_id': item.product_id,
                'quantity': item.quantity,
                'price_at_order': price
            })
        
        promo_code_id = None
        discount_amount = Decimal(0)
        
        if order_data.promo_code:
            promo = await self.product_client.get_promo_code(order_data.promo_code)
            if promo:
                if Decimal(str(promo['min_order_amount'])) <= total_amount:
                    promo_code_id = UUID(promo['id'])
                    
                    if promo['discount_type'] == 'PERCENTAGE':
                        discount = total_amount * Decimal(str(promo['discount_value'])) / Decimal(100)
                        discount_amount = min(discount, total_amount * Decimal('0.7'))
                    else:
                        discount_amount = min(Decimal(str(promo['discount_value'])), total_amount)
                    
                    total_amount -= discount_amount
                    await self.product_client.increment_promo_usage(promo_code_id)
        
        order = Order(
            user_id=user_id,
            status=OrderStatus.CREATED,
            promo_code_id=promo_code_id,
            total_amount=total_amount,
            discount_amount=discount_amount
        )
        self.db.add(order)
        await self.db.flush()
        
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                **item_data
            )
            self.db.add(order_item)
        
        operation = UserOperation(
            user_id=user_id,
            operation_type=OperationType.CREATE_ORDER
        )
        self.db.add(operation)
        
        await self.db.commit()
        await self.db.refresh(order, ['items'])
        
        await kafka_producer.send_event('order.created', {
            'order_id': str(order.id),
            'user_id': str(user_id),
            'total_amount': float(total_amount),
            'items_count': len(order_items_data)
        })
        
        return order

    async def get_order(self, order_id: UUID, user_id: UUID) -> Order:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise OrderNotFoundException(str(order_id))
        
        if order.user_id != user_id:
            raise OrderOwnershipViolationException()
        
        return order

    async def cancel_order(self, order_id: UUID, user_id: UUID) -> Order:
        order = await self.get_order(order_id, user_id)
        
        if order.status not in [OrderStatus.CREATED, OrderStatus.PAYMENT_PENDING]:
            raise InvalidStateTransitionException(order.status.value, OrderStatus.CANCELED.value)
        
        for item in order.items:
            await self.product_client.release_stock(item.product_id, item.quantity)
        
        if order.promo_code_id:
            await self.product_client.decrement_promo_usage(order.promo_code_id)
        
        order.status = OrderStatus.CANCELED
        
        await self.db.commit()
        await self.db.refresh(order)
        
        await kafka_producer.send_event('order.canceled', {
            'order_id': str(order.id),
            'user_id': str(user_id)
        })
        
        return order

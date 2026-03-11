from fastapi import HTTPException, status

class MarketplaceException(HTTPException):
    def __init__(self, error_code: str, message: str, status_code: int, details: dict = None):
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail={"error_code": error_code, "message": message, "details": details})

class ProductNotFoundException(MarketplaceException):
    def __init__(self, product_id: str):
        super().__init__(
            error_code="PRODUCT_NOT_FOUND",
            message=f"Товар с ID {product_id} не найден",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ProductInactiveException(MarketplaceException):
    def __init__(self, product_id: str):
        super().__init__(
            error_code="PRODUCT_INACTIVE",
            message=f"Товар с ID {product_id} неактивен",
            status_code=status.HTTP_409_CONFLICT
        )

class OrderNotFoundException(MarketplaceException):
    def __init__(self, order_id: str):
        super().__init__(
            error_code="ORDER_NOT_FOUND",
            message=f"Заказ с ID {order_id} не найден",
            status_code=status.HTTP_404_NOT_FOUND
        )

class OrderLimitExceededException(MarketplaceException):
    def __init__(self, minutes: int):
        super().__init__(
            error_code="ORDER_LIMIT_EXCEEDED",
            message=f"Превышен лимит частоты создания/обновления заказа. Попробуйте через {minutes} минут",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

class OrderHasActiveException(MarketplaceException):
    def __init__(self):
        super().__init__(
            error_code="ORDER_HAS_ACTIVE",
            message="У пользователя уже есть активный заказ",
            status_code=status.HTTP_409_CONFLICT
        )

class InvalidStateTransitionException(MarketplaceException):
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            error_code="INVALID_STATE_TRANSITION",
            message=f"Недопустимый переход состояния заказа из {current_status} в {target_status}",
            status_code=status.HTTP_409_CONFLICT
        )

class InsufficientStockException(MarketplaceException):
    def __init__(self, details: dict):
        super().__init__(
            error_code="INSUFFICIENT_STOCK",
            message="Недостаточно товара на складе",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )

class PromoCodeInvalidException(MarketplaceException):
    def __init__(self, reason: str):
        super().__init__(
            error_code="PROMO_CODE_INVALID",
            message=f"Промокод недействителен: {reason}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class PromoCodeMinAmountException(MarketplaceException):
    def __init__(self, min_amount: float, current_amount: float):
        super().__init__(
            error_code="PROMO_CODE_MIN_AMOUNT",
            message=f"Сумма заказа ({current_amount}) ниже минимальной для промокода ({min_amount})",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class OrderOwnershipViolationException(MarketplaceException):
    def __init__(self):
        super().__init__(
            error_code="ORDER_OWNERSHIP_VIOLATION",
            message="Заказ принадлежит другому пользователю",
            status_code=status.HTTP_403_FORBIDDEN
        )

class ValidationException(MarketplaceException):
    def __init__(self, details: dict):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message="Ошибка валидации входных данных",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )

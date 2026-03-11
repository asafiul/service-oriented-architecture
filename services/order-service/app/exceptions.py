from fastapi import HTTPException, status

class MarketplaceException(HTTPException):
    def __init__(self, error_code: str, message: str, status_code: int, details: dict = None):
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail={"error_code": error_code, "message": message, "details": details})

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

class OrderOwnershipViolationException(MarketplaceException):
    def __init__(self):
        super().__init__(
            error_code="ORDER_OWNERSHIP_VIOLATION",
            message="Заказ принадлежит другому пользователю",
            status_code=status.HTTP_403_FORBIDDEN
        )

class ProductServiceException(MarketplaceException):
    def __init__(self, message: str):
        super().__init__(
            error_code="PRODUCT_SERVICE_ERROR",
            message=f"Ошибка Product Service: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class ValidationException(MarketplaceException):
    def __init__(self, details: dict):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message="Ошибка валидации входных данных",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )

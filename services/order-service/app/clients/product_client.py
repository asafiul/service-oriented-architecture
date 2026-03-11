import httpx
from typing import Optional, Dict, Any
from uuid import UUID
from app.config import settings
from app.exceptions import ProductServiceException

class ProductClient:
    def __init__(self):
        self.base_url = settings.product_service_url
        self.timeout = 10.0
    
    async def get_product(self, product_id: UUID) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/products/{product_id}")
                if response.status_code == 404:
                    raise ProductServiceException(f"Товар {product_id} не найден")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise ProductServiceException(str(e))
    
    async def get_promo_code(self, code: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/promo-codes/{code}")
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise ProductServiceException(str(e))
    
    async def reserve_stock(self, product_id: UUID, quantity: int) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/products/{product_id}/reserve",
                    json={"quantity": quantity}
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                raise ProductServiceException(str(e))
    
    async def release_stock(self, product_id: UUID, quantity: int) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/products/{product_id}/release",
                    json={"quantity": quantity}
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                raise ProductServiceException(str(e))
    
    async def increment_promo_usage(self, promo_code_id: UUID) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/promo-codes/{promo_code_id}/increment"
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError:
                return False
    
    async def decrement_promo_usage(self, promo_code_id: UUID) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/promo-codes/{promo_code_id}/decrement"
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError:
                return False

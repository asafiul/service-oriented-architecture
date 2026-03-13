#!/bin/bash

echo "=== Тестирование Marketplace API ==="
echo ""

PRODUCT_ID=""
USER_ID="123e4567-e89b-12d3-a456-426614174000"

echo "1. Проверка health endpoint"
curl -s http://localhost:8002/health | python3 -m json.tool
echo ""

echo "2. Создание товара"
RESPONSE=$(curl -s -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Смартфон",
    "description": "Современный смартфон",
    "price": 30000.00,
    "stock": 5,
    "category": "Электроника",
    "status": "ACTIVE"
  }')
echo "$RESPONSE" | python3 -m json.tool
PRODUCT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT_ID"
echo ""

echo "3. Получение списка товаров"
curl -s "http://localhost:8002/products?page=0&size=20" | python3 -m json.tool
echo ""

echo "4. Получение товара по ID"
curl -s "http://localhost:8002/products/$PRODUCT_ID" | python3 -m json.tool
echo ""

echo "5. Создание промокода"
PROMO_RESPONSE=$(curl -s -X POST http://localhost:8002/promo-codes \
  -H "Content-Type: application/json" \
  -d '{
    "code": "SALE2024",
    "discount_type": "PERCENTAGE",
    "discount_value": 10,
    "min_order_amount": 1000,
    "max_uses": 100,
    "valid_from": "2024-01-01T00:00:00Z",
    "valid_until": "2027-12-31T23:59:59Z",
    "active": true
  }')
echo "$PROMO_RESPONSE" | python3 -m json.tool
echo ""

echo "6. Создание заказа с промокодом"
ORDER_RESPONSE=$(curl -s -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"items\": [
      {
        \"product_id\": \"$PRODUCT_ID\",
        \"quantity\": 2
      }
    ],
    \"promo_code\": \"SALE2024\"
  }")
echo "$ORDER_RESPONSE" | python3 -m json.tool
ORDER_ID=$(echo "$ORDER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
echo ""

if [ -n "$ORDER_ID" ]; then
  echo "7. Получение заказа по ID"
  curl -s "http://localhost:8002/orders/$ORDER_ID" \
    -H "X-User-Id: $USER_ID" | python3 -m json.tool
  echo ""

  echo "8. Проверка остатков товара после заказа"
  curl -s "http://localhost:8002/products/$PRODUCT_ID" | python3 -m json.tool
  echo ""

  echo "9. Отмена заказа"
  curl -s -X POST "http://localhost:8002/orders/$ORDER_ID/cancel" \
    -H "X-User-Id: $USER_ID" | python3 -m json.tool
  echo ""

  echo "10. Проверка остатков товара после отмены"
  curl -s "http://localhost:8002/products/$PRODUCT_ID" | python3 -m json.tool
  echo ""
fi

echo "11. Тест валидации - неверная цена"
curl -s -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Товар",
    "price": -100,
    "stock": 5,
    "category": "Тест",
    "status": "ACTIVE"
  }' | python3 -m json.tool
echo ""

echo "12. Тест ошибки - товар не найден"
curl -s "http://localhost:8002/products/00000000-0000-0000-0000-000000000000" | python3 -m json.tool
echo ""

echo "13. Проверка таблиц в БД"
docker-compose exec -T postgres psql -U marketplace -d marketplace -c "\dt"
echo ""

echo "=== Тестирование завершено ==="

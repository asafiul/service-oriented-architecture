# Чек-лист проверки заданий 1-7

## ✅ Задание 1: OpenAPI-спецификация CRUD (1 балл)

### Требования:
- POST /products - создание товара
- GET /products/{id} - получение товара по ID
- GET /products - список товаров с пагинацией и фильтрацией
- PUT /products/{id} - обновление товара
- DELETE /products/{id} - мягкое удаление (ARCHIVED)

### Где реализовано:
- Спецификация: [`services/product-service/openapi/marketplace-api.yaml`](services/product-service/openapi/marketplace-api.yaml)
- Роутер: [`services/product-service/app/routers/products.py`](services/product-service/app/routers/products.py)

### Проверка:
```bash
# 1. Создание товара
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый товар",
    "description": "Описание",
    "price": 1000.00,
    "stock": 10,
    "category": "Тест",
    "status": "ACTIVE"
  }'

# 2. Список товаров с пагинацией
curl "http://localhost:8002/products?page=0&size=20"

# 3. Фильтрация по статусу
curl "http://localhost:8002/products?status=ACTIVE"

# 4. Фильтрация по категории
curl "http://localhost:8002/products?category=Тест"

# 5. Получение товара по ID
curl "http://localhost:8002/products/<product-id>"

# 6. Обновление товара
curl -X PUT "http://localhost:8002/products/<product-id>" \
  -H "Content-Type: application/json" \
  -d '{"price": 1500.00}'

# 7. Мягкое удаление (архивация)
curl -X DELETE "http://localhost:8002/products/<product-id>"
```

---

## ✅ Задание 2: Описание схем данных в OpenAPI (1 балл)

### Требования:
- Поля: id, name, description, price, stock, category, status, created_at, updated_at
- format для decimal и datetime
- enum для статусов
- nullable где необходимо
- Отдельные схемы: ProductCreate, ProductUpdate, ProductResponse

### Где реализовано:
- OpenAPI: [`services/product-service/openapi/marketplace-api.yaml`](services/product-service/openapi/marketplace-api.yaml) (строки 400-550)
- Pydantic: [`services/product-service/app/schemas.py`](services/product-service/app/schemas.py)

### Проверка:
```bash
# Swagger UI покажет все схемы
open http://localhost:8002/docs

# Проверка валидации - неверная цена
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Товар","price":-100,"stock":5,"category":"Тест","status":"ACTIVE"}'

# Ожидается: VALIDATION_ERROR
```

---

## ✅ Задание 4: PostgreSQL + базовый CRUD (1 балл)

### Требования:
- PostgreSQL подключен
- Миграции через Alembic
- Индекс на поле status
- created_at/updated_at автоматически
- DELETE выполняет мягкое удаление (ARCHIVED)

### Где реализовано:
- Миграция: [`services/product-service/alembic/versions/001_initial_schema.py`](services/product-service/alembic/versions/001_initial_schema.py)
- Модели: [`services/product-service/app/models.py`](services/product-service/app/models.py)
- docker-compose: [`docker-compose.yml`](docker-compose.yml) (строки 1-15)

### Проверка:
```bash
# 1. Проверка БД
docker-compose exec postgres-products psql -U marketplace -d marketplace_products

# 2. Просмотр таблиц
\dt

# 3. Проверка индекса
\d products

# Должен быть: idx_products_status

# 4. Проверка данных
SELECT id, name, status, created_at, updated_at FROM products;

# 5. Проверка мягкого удаления
# Создать товар, удалить его, проверить что status=ARCHIVED
```

---

## ✅ Задание 5: Контрактная обработка ошибок (1 балл)

### Требования:
- Единый формат: error_code, message, details
- Все обязательные коды ошибок

### Где реализовано:
- Исключения: [`services/product-service/app/exceptions.py`](services/product-service/app/exceptions.py)
- Обработчики: [`services/product-service/app/main.py`](services/product-service/app/main.py) (строки 15-50)
- OpenAPI: [`services/product-service/openapi/marketplace-api.yaml`](services/product-service/openapi/marketplace-api.yaml) (строки 700-750)

### Проверка:
```bash
# 1. PRODUCT_NOT_FOUND (404)
curl "http://localhost:8002/products/00000000-0000-0000-0000-000000000000"

# Ожидается:
# {
#   "error_code": "PRODUCT_NOT_FOUND",
#   "message": "Товар с ID ... не найден",
#   "details": null
# }

# 2. VALIDATION_ERROR (400)
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"","price":-1,"stock":-5,"category":"","status":"INVALID"}'

# Ожидается:
# {
#   "error_code": "VALIDATION_ERROR",
#   "message": "Ошибка валидации входных данных",
#   "details": {...}
# }
```

---

## ✅ Задание 6: Контрактная валидация входных данных (1 балл)

### Требования:
- name: minLength=1, maxLength=255
- description: maxLength=4000
- price: minimum=0.01 (> 0)
- stock: minimum=0
- category: minLength=1, maxLength=100
- items: minItems=1, maxItems=50
- quantity: minimum=1, maximum=999
- promo_code: pattern=^[A-Z0-9_]{4,20}$

### Где реализовано:
- Pydantic схемы: [`services/product-service/app/schemas.py`](services/product-service/app/schemas.py)
- Order схемы: [`services/order-service/app/schemas.py`](services/order-service/app/schemas.py)

### Проверка:
```bash
# 1. Проверка name (пустое)
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"","price":100,"stock":5,"category":"Тест","status":"ACTIVE"}'
# Ожидается: VALIDATION_ERROR

# 2. Проверка price (отрицательная)
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Товар","price":-100,"stock":5,"category":"Тест","status":"ACTIVE"}'
# Ожидается: VALIDATION_ERROR

# 3. Проверка stock (отрицательный)
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Товар","price":100,"stock":-5,"category":"Тест","status":"ACTIVE"}'
# Ожидается: VALIDATION_ERROR

# 4. Проверка quantity в заказе (> 999)
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{"items":[{"product_id":"<uuid>","quantity":1000}]}'
# Ожидается: VALIDATION_ERROR

# 5. Проверка promo_code (неверный формат)
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{"items":[{"product_id":"<uuid>","quantity":1}],"promo_code":"invalid-code"}'
# Ожидается: VALIDATION_ERROR
```

---

## ✅ Задание 7: Сложная бизнес-логика для заказов (1 балл)

### Требования:
1. Ограничение частоты создания (rate limiting)
2. Проверка активных заказов
3. Проверка каталога (товары ACTIVE)
4. Проверка остатков (stock)
5. Резервирование остатков
6. Снапшот цен (price_at_order)
7. Расчёт стоимости с промокодами
8. Фиксация операции (user_operations)

### Где реализовано:
- Бизнес-логика: [`services/order-service/app/services/order_service.py`](services/order-service/app/services/order_service.py)
- Модели: [`services/order-service/app/models.py`](services/order-service/app/models.py)
- HTTP клиент: [`services/order-service/app/clients/product_client.py`](services/order-service/app/clients/product_client.py)

### Проверка:

#### 1. Создание заказа (полный flow)
```bash
# Шаг 1: Создать товар
PRODUCT_RESPONSE=$(curl -s -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый товар для заказа",
    "price": 1000.00,
    "stock": 10,
    "category": "Тест",
    "status": "ACTIVE"
  }')

PRODUCT_ID=$(echo $PRODUCT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Product ID: $PRODUCT_ID"

# Шаг 2: Создать промокод
curl -X POST http://localhost:8002/promo-codes \
  -H "Content-Type: application/json" \
  -d '{
    "code": "TEST2024",
    "discount_type": "PERCENTAGE",
    "discount_value": 10,
    "min_order_amount": 500,
    "max_uses": 100,
    "valid_from": "2024-01-01T00:00:00Z",
    "valid_until": "2027-12-31T23:59:59Z",
    "active": true
  }'

# Шаг 3: Создать заказ
USER_ID="123e4567-e89b-12d3-a456-426614174000"

ORDER_RESPONSE=$(curl -s -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"items\": [{
      \"product_id\": \"$PRODUCT_ID\",
      \"quantity\": 2
    }],
    \"promo_code\": \"TEST2024\"
  }")

echo $ORDER_RESPONSE | python3 -m json.tool

# Проверить:
# - total_amount = 2000 * 0.9 = 1800 (скидка 10%)
# - discount_amount = 200
# - status = CREATED
```

#### 2. Проверка резервирования stock
```bash
# Проверить stock до заказа
curl "http://localhost:8002/products/$PRODUCT_ID" | python3 -c "import sys, json; print('Stock:', json.load(sys.stdin)['stock'])"
# Должно быть: 10

# Создать заказ на 2 штуки (см. выше)

# Проверить stock после заказа
curl "http://localhost:8002/products/$PRODUCT_ID" | python3 -c "import sys, json; print('Stock:', json.load(sys.stdin)['stock'])"
# Должно быть: 8 (10 - 2)
```

#### 3. Проверка rate limiting
```bash
# Создать первый заказ
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":1}]}"

# Сразу создать второй заказ (должна быть ошибка)
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":1}]}"

# Ожидается: ORDER_LIMIT_EXCEEDED
```

#### 4. Проверка активных заказов
```bash
# Создать заказ
ORDER_ID=$(curl -s -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":1}]}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

# Попытаться создать еще один (должна быть ошибка)
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":1}]}"

# Ожидается: ORDER_HAS_ACTIVE
```

#### 5. Проверка недостаточного stock
```bash
# Попытаться заказать больше чем есть
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{\"items\":[{\"product_id\":\"$PRODUCT_ID\",\"quantity\":999}]}"

# Ожидается: INSUFFICIENT_STOCK с деталями
```

#### 6. Проверка отмены заказа
```bash
# Отменить заказ
curl -X POST "http://localhost:8003/orders/$ORDER_ID/cancel" \
  -H "X-User-Id: $USER_ID"

# Проверить что stock вернулся
curl "http://localhost:8002/products/$PRODUCT_ID" | python3 -c "import sys, json; print('Stock:', json.load(sys.stdin)['stock'])"
# Stock должен увеличиться
```

#### 7. Проверка БД
```bash
# Orders БД
docker-compose exec postgres-orders psql -U marketplace -d marketplace_orders -c "
SELECT id, status, total_amount, discount_amount 
FROM orders 
ORDER BY created_at DESC 
LIMIT 5;
"

# Order items
docker-compose exec postgres-orders psql -U marketplace -d marketplace_orders -c "
SELECT oi.id, oi.product_id, oi.quantity, oi.price_at_order
FROM order_items oi
JOIN orders o ON oi.order_id = o.id
ORDER BY o.created_at DESC
LIMIT 5;
"

# User operations (rate limiting)
docker-compose exec postgres-orders psql -U marketplace -d marketplace_orders -c "
SELECT user_id, operation_type, created_at
FROM user_operations
ORDER BY created_at DESC
LIMIT 5;
"
```

#### 8. Проверка Kafka событий
```bash
# Посмотреть логи Order Service
docker-compose logs order-service | grep "Event sent to Kafka"

# Должно быть:
# INFO: Event sent to Kafka topic 'order.created': {'order_id': '...', ...}
# INFO: Event sent to Kafka topic 'order.canceled': {'order_id': '...', ...}
```

---

## 📊 Итоговая проверка

### Swagger UI
```bash
# Product Service
open http://localhost:8002/docs

# Order Service
open http://localhost:8003/docs
```

### Статус сервисов
```bash
docker-compose ps

# Все должны быть UP:
# - postgres-products (healthy)
# - postgres-orders (healthy)
# - kafka (healthy)
# - zookeeper (up)
# - product-service (up)
# - order-service (up)
```

### Проверка БД
```bash
# Product Service БД
docker-compose exec postgres-products psql -U marketplace -d marketplace_products -c "\dt"

# Order Service БД
docker-compose exec postgres-orders psql -U marketplace -d marketplace_orders -c "\dt"
```

---

## ✅ Все задания выполнены!

Каждое задание можно проверить через:
1. Swagger UI (http://localhost:8002/docs)
2. curl команды (см. выше)
3. Проверка БД (psql команды)
4. Логи сервисов (docker-compose logs)

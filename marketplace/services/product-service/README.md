# Product Service - Marketplace API

Сервис для управления товарами, заказами и промокодами маркетплейса.

## Реализованные задания

### ✅ Задание 1-2: OpenAPI спецификация (2 балла)
- Полная OpenAPI спецификация в `openapi/marketplace-api.yaml`
- CRUD операции для товаров (POST, GET, PUT, DELETE)
- Пагинация и фильтрация для GET /products
- Отдельные схемы ProductCreate, ProductUpdate, ProductResponse

### ✅ Задание 4: PostgreSQL + CRUD (1 балл)
- PostgreSQL с миграциями через Alembic
- Индекс на поле status в таблице products
- Автоматическое заполнение created_at/updated_at
- Мягкое удаление (статус ARCHIVED)

### ✅ Задание 5: Контрактная обработка ошибок (1 балл)
- Единый формат ошибок (error_code, message, details)
- Все обязательные коды ошибок реализованы
- Ошибки описаны в OpenAPI

### ✅ Задание 6: Контрактная валидация (1 балл)
- Все ограничения заданы в схемах Pydantic
- Валидация на уровне фреймворка
- Возврат VALIDATION_ERROR с деталями

### ✅ Задание 7: Сложная бизнес-логика заказов (1 балл)
- Полная схема БД (orders, order_items, promo_codes, user_operations)
- Машина состояний заказов
- Проверка частоты операций (rate limiting)
- Проверка активных заказов
- Валидация каталога и остатков
- Резервирование stock
- Снапшот цен (price_at_order)
- Применение промокодов с валидацией
- Обновление и отмена заказов
- Все операции в транзакциях

## Структура проекта

```
services/product-service/
├── openapi/
│   └── marketplace-api.yaml      # OpenAPI спецификация
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py # Миграция БД
│   └── env.py
├── app/
│   ├── routers/                  # API endpoints
│   │   ├── products.py
│   │   ├── orders.py
│   │   └── promo_codes.py
│   ├── services/                 # Бизнес-логика
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   └── promo_service.py
│   ├── models.py                 # SQLAlchemy модели
│   ├── schemas.py                # Pydantic схемы
│   ├── exceptions.py             # Кастомные исключения
│   ├── database.py               # Подключение к БД
│   ├── config.py                 # Конфигурация
│   └── main.py                   # FastAPI приложение
├── Dockerfile
├── requirements.txt
└── alembic.ini
```

## Запуск

### Запуск всей системы
```bash
docker-compose up -d
```

### Запуск только product-service
```bash
docker-compose up -d postgres product-service
```

### Просмотр логов
```bash
docker-compose logs -f product-service
```

### Остановка
```bash
docker-compose down
```

## API Endpoints

### Товары
- `POST /products` - Создать товар
- `GET /products` - Список товаров (пагинация, фильтры)
- `GET /products/{id}` - Получить товар
- `PUT /products/{id}` - Обновить товар
- `DELETE /products/{id}` - Архивировать товар

### Заказы
- `POST /orders` - Создать заказ
- `GET /orders/{id}` - Получить заказ
- `PUT /orders/{id}` - Обновить заказ
- `POST /orders/{id}/cancel` - Отменить заказ

### Промокоды
- `POST /promo-codes` - Создать промокод

## Примеры запросов

### Создание товара
```bash
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ноутбук",
    "description": "Мощный ноутбук для работы",
    "price": 50000.00,
    "stock": 10,
    "category": "Электроника",
    "status": "ACTIVE"
  }'
```

### Получение списка товаров
```bash
curl "http://localhost:8002/products?page=0&size=20&status=ACTIVE"
```

### Создание промокода
```bash
curl -X POST http://localhost:8002/promo-codes \
  -H "Content-Type: application/json" \
  -d '{
    "code": "SALE2024",
    "discount_type": "PERCENTAGE",
    "discount_value": 10,
    "min_order_amount": 1000,
    "max_uses": 100,
    "valid_from": "2024-01-01T00:00:00Z",
    "valid_until": "2024-12-31T23:59:59Z",
    "active": true
  }'
```

### Создание заказа
```bash
curl -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{
    "items": [
      {
        "product_id": "product-uuid-here",
        "quantity": 2
      }
    ],
    "promo_code": "SALE2024"
  }'
```

## Проверка БД

### Подключение к PostgreSQL
```bash
docker-compose exec postgres psql -U marketplace -d marketplace
```

### Просмотр таблиц
```sql
\dt
SELECT * FROM products;
SELECT * FROM orders;
SELECT * FROM order_items;
SELECT * FROM promo_codes;
SELECT * FROM user_operations;
```

## Технологии

- **FastAPI** - веб-фреймворк
- **SQLAlchemy** - ORM
- **Alembic** - миграции БД
- **PostgreSQL** - база данных
- **Pydantic** - валидация данных
- **Docker** - контейнеризация

## Особенности реализации

### Транзакции
Все операции с заказами выполняются в транзакциях для обеспечения консистентности данных.

### Rate Limiting
Ограничение частоты создания/обновления заказов через таблицу user_operations.

### Резервирование товаров
При создании заказа товары резервируются (уменьшается stock), при отмене - возвращаются.

### Промокоды
- Поддержка процентных и фиксированных скидок
- Валидация по срокам действия
- Ограничение количества использований
- Минимальная сумма заказа
- Максимальная скидка 70% для процентных промокодов

### Машина состояний заказов
```
CREATED → PAYMENT_PENDING → PAID → SHIPPED → COMPLETED
              ↘
                CANCELED
```

Недопустимые переходы блокируются с ошибкой INVALID_STATE_TRANSITION.

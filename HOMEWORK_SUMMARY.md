# Домашнее задание №2 - Marketplace: OpenAPI + CRUD

## Выполненные задания

### ✅ Задание 1: OpenAPI-спецификация CRUD (1 балл)

**Файл:** [`services/product-service/openapi/marketplace-api.yaml`](services/product-service/openapi/marketplace-api.yaml)

Реализованы все обязательные эндпоинты:
- `POST /products` - Создание товара
- `GET /products/{id}` - Получение товара по ID
- `GET /products` - Список товаров с пагинацией и фильтрацией
- `PUT /products/{id}` - Обновление товара
- `DELETE /products/{id}` - Мягкое удаление (статус ARCHIVED)

Параметры пагинации и фильтрации:
- `page` - номер страницы (начиная с 0)
- `size` - размер страницы (default 20)
- `status` - фильтр по статусу (enum)
- `category` - фильтр по категории (точное совпадение)

Ответ содержит: список товаров, `total_elements`, `page`, `size`.

---

### ✅ Задание 2: Описание схем данных в OpenAPI (1 балл)

**Файл:** [`services/product-service/openapi/marketplace-api.yaml`](services/product-service/openapi/marketplace-api.yaml)

Реализована полная схема Product со всеми обязательными полями:
- `id` (UUID) - только в response
- `name` (string, 1-255) - обязательно
- `description` (string, max 4000) - опционально
- `price` (decimal, > 0) - обязательно
- `stock` (integer, >= 0) - обязательно
- `category` (string, 1-100) - обязательно
- `status` (enum: ACTIVE, INACTIVE, ARCHIVED) - обязательно
- `created_at` (datetime) - только в response
- `updated_at` (datetime) - только в response

Отдельные схемы:
- `ProductCreate` - для создания
- `ProductUpdate` - для обновления
- `ProductResponse` - для ответа

Указаны `format` для decimal и datetime, `nullable` где необходимо.

---

### ✅ Задание 4: PostgreSQL + базовый CRUD (1 балл)

**Миграции:** [`services/product-service/alembic/versions/001_initial_schema.py`](services/product-service/alembic/versions/001_initial_schema.py)

Реализовано:
- PostgreSQL в Docker Compose
- Миграции через Alembic (воспроизводимы одной командой)
- Индекс на поле `status` в таблице `products`
- Автоматическое заполнение `created_at`/`updated_at` через `server_default` и `onupdate`
- Мягкое удаление - `DELETE /products/{id}` переводит статус в ARCHIVED

**Запуск миграций:** автоматически при старте контейнера в Dockerfile

---

### ✅ Задание 5: Контрактная обработка ошибок (1 балл)

**Файлы:** 
- [`services/product-service/app/exceptions.py`](services/product-service/app/exceptions.py)
- [`services/product-service/app/main.py`](services/product-service/app/main.py)

Единый формат ошибок:
```json
{
  "error_code": "PRODUCT_NOT_FOUND",
  "message": "Товар с ID ... не найден",
  "details": {}
}
```

Реализованы все обязательные коды ошибок:
- `PRODUCT_NOT_FOUND` (404)
- `PRODUCT_INACTIVE` (409)
- `ORDER_NOT_FOUND` (404)
- `ORDER_LIMIT_EXCEEDED` (429)
- `ORDER_HAS_ACTIVE` (409)
- `INVALID_STATE_TRANSITION` (409)
- `INSUFFICIENT_STOCK` (409)
- `PROMO_CODE_INVALID` (422)
- `PROMO_CODE_MIN_AMOUNT` (422)
- `ORDER_OWNERSHIP_VIOLATION` (403)
- `VALIDATION_ERROR` (400)

Все ошибки описаны в OpenAPI спецификации.

---

### ✅ Задание 6: Контрактная валидация входных данных (1 балл)

**Файл:** [`services/product-service/app/schemas.py`](services/product-service/app/schemas.py)

Все ограничения заданы в Pydantic схемах:
- `name`: minLength=1, maxLength=255
- `description`: maxLength=4000
- `price`: minimum=0.01 (exclusiveMinimum)
- `stock`: minimum=0
- `category`: minLength=1, maxLength=100
- `items`: minItems=1, maxItems=50
- `quantity`: minimum=1, maximum=999
- `promo_code`: pattern=`^[A-Z0-9_]{4,20}$`

Невалидные запросы не доходят до бизнес-логики.
При ошибке валидации возвращается `VALIDATION_ERROR` с деталями в `details`.

---

### ✅ Задание 7: Сложная бизнес-логика для заказов (1 балл)

**Файлы:**
- [`services/product-service/app/models.py`](services/product-service/app/models.py) - модели БД
- [`services/product-service/app/services/order_service.py`](services/product-service/app/services/order_service.py) - бизнес-логика

#### Схема БД

Реализованы все таблицы:
- `products` - товары
- `orders` - заказы
- `order_items` - позиции заказов
- `promo_codes` - промокоды
- `user_operations` - операции пользователей (для rate limiting)

#### Машина состояний заказов

```
CREATED → PAYMENT_PENDING → PAID → SHIPPED → COMPLETED
              ↘
                CANCELED
```

Недопустимые переходы блокируются с ошибкой `INVALID_STATE_TRANSITION`.

#### Создание заказа (POST /orders)

Последовательность проверок:
1. **Ограничение частоты** - проверка последней операции `CREATE_ORDER` (< N минут)
2. **Проверка активных заказов** - нет заказов в статусе CREATED/PAYMENT_PENDING
3. **Проверка каталога** - все товары существуют и ACTIVE
4. **Проверка остатков** - достаточно stock для всех позиций
5. **Резервирование остатков** - `product.stock -= quantity`
6. **Снапшот цен** - `price_at_order = product.price`
7. **Расчёт стоимости** - с применением промокода
   - Валидация промокода (active, uses, dates, min_amount)
   - PERCENTAGE: discount = min(total * value / 100, total * 0.7)
   - FIXED_AMOUNT: discount = min(value, total)
   - Инкремент `current_uses`
8. **Фиксация операции** - запись в `user_operations`

Всё в одной транзакции.

#### Обновление заказа (PUT /orders/{id})

1. Проверка владельца
2. Проверка состояния (только CREATED)
3. Ограничение частоты `UPDATE_ORDER`
4. Возврат предыдущих остатков
5. Проверка и резервирование новых позиций
6. Пересчёт стоимости с промокодом
7. Фиксация операции

#### Отмена заказа (POST /orders/{id}/cancel)

1. Проверка владельца
2. Проверка состояния (CREATED или PAYMENT_PENDING)
3. Возврат остатков
4. Возврат использования промокода (`current_uses -= 1`)
5. Установка статуса CANCELED

---

## Структура проекта

```
services/product-service/
├── openapi/
│   └── marketplace-api.yaml          # OpenAPI спецификация
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py     # Миграция БД
│   └── env.py
├── app/
│   ├── routers/                      # API endpoints
│   │   ├── products.py
│   │   ├── orders.py
│   │   └── promo_codes.py
│   ├── services/                     # Бизнес-логика
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   └── promo_service.py
│   ├── models.py                     # SQLAlchemy модели
│   ├── schemas.py                    # Pydantic схемы
│   ├── exceptions.py                 # Кастомные исключения
│   ├── database.py                   # Подключение к БД
│   ├── config.py                     # Конфигурация
│   └── main.py                       # FastAPI приложение
├── Dockerfile
├── requirements.txt
└── alembic.ini
```

---

## Запуск системы

### Запуск всех сервисов
```bash
docker-compose up -d
```

### Просмотр логов
```bash
docker-compose logs -f product-service
```

### Проверка здоровья
```bash
curl http://localhost:8002/health
```

### Запуск тестов
```bash
./test_api.sh
```

---

## Примеры использования

### 1. Создание товара
```bash
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ноутбук",
    "description": "Мощный ноутбук",
    "price": 50000.00,
    "stock": 10,
    "category": "Электроника",
    "status": "ACTIVE"
  }'
```

### 2. Получение списка товаров
```bash
curl "http://localhost:8002/products?page=0&size=20&status=ACTIVE"
```

### 3. Создание промокода
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
    "valid_until": "2027-12-31T23:59:59Z"
  }'
```

### 4. Создание заказа
```bash
curl -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{
    "items": [
      {"product_id": "product-uuid", "quantity": 2}
    ],
    "promo_code": "SALE2024"
  }'
```

### 5. Отмена заказа
```bash
curl -X POST http://localhost:8002/orders/{order-id}/cancel \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000"
```

---

## Проверка БД

```bash
docker-compose exec postgres psql -U marketplace -d marketplace
```

```sql
-- Просмотр таблиц
\dt

-- Проверка товаров
SELECT * FROM products;

-- Проверка заказов
SELECT * FROM orders;

-- Проверка позиций заказов
SELECT * FROM order_items;

-- Проверка промокодов
SELECT * FROM promo_codes;

-- Проверка операций пользователей
SELECT * FROM user_operations;
```

---

## Технологии

- **Python 3.11** - язык программирования
- **FastAPI** - веб-фреймворк
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **Alembic** - миграции БД
- **PostgreSQL 15** - база данных
- **Pydantic 2.5** - валидация данных
- **Docker & Docker Compose** - контейнеризация

---

## Особенности реализации

### Транзакции
Все операции с заказами выполняются в транзакциях для обеспечения консистентности данных.

### Rate Limiting
Ограничение частоты создания/обновления заказов через таблицу `user_operations` с конфигурируемым параметром `RATE_LIMIT_MINUTES`.

### Резервирование товаров
- При создании заказа: `stock -= quantity`
- При отмене заказа: `stock += quantity`
- При обновлении заказа: возврат старых + резервирование новых

### Промокоды
- Процентные скидки (максимум 70%)
- Фиксированные скидки
- Валидация по срокам действия
- Ограничение количества использований
- Минимальная сумма заказа

### Обработка ошибок
Все ошибки возвращаются в едином формате с машиночитаемыми кодами и человекочитаемыми сообщениями.

---

## Готовность к защите

Система полностью готова к защите:
1. ✅ Все 7 заданий выполнены
2. ✅ Система запускается через `docker-compose up`
3. ✅ Миграции применяются автоматически
4. ✅ API работает и протестировано
5. ✅ Данные записываются в БД
6. ✅ Бизнес-логика реализована полностью
7. ✅ Обработка ошибок работает
8. ✅ Валидация данных работает

Для демонстрации на защите:
- Запустить: `docker-compose up -d`
- Показать логи: `docker-compose logs -f product-service`
- Выполнить запросы: `./test_api.sh`
- Показать БД: `docker-compose exec postgres psql -U marketplace -d marketplace`

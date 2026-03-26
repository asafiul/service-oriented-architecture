# Гайд для защиты проекта "Marketplace"

## Общая информация о проекте

**Что реализовано:** Микросервисная архитектура маркетплейса с товарами, заказами и промокодами.

**Выполненные задания:** 1-8 (8 баллов из 10)

**Технологии:**
- FastAPI (Python 3.11)
- PostgreSQL (2 отдельные БД)
- Apache Kafka + Zookeeper
- Docker Compose
- Alembic (миграции БД)
- Pydantic v2 (валидация)
- SQLAlchemy 2.0 (ORM)

---

## Архитектура проекта

### Микросервисы

1. **Product Service** (порт 8002)
   - Управление товарами (CRUD)
   - Управление промокодами
   - Резервирование/освобождение товаров
   - БД: `postgres-products` (порт 5432)

2. **Order Service** (порт 8003)
   - Создание заказов
   - Отмена заказов
   - Сложная бизнес-логика (8 проверок)
   - БД: `postgres-orders` (порт 5433)

3. **Kafka + Zookeeper**
   - Асинхронная коммуникация
   - События: `order.created`, `order.canceled`

### Схема взаимодействия

```
Client → Order Service → Product Service (HTTP)
                ↓
              Kafka (async events)
```

---

## Задание 1: OpenAPI спецификация (1 балл) ✅

**Файл:** `services/product-service/openapi/marketplace-api.yaml`

**Что сделано:**
- Полная OpenAPI 3.0 спецификация (771 строка)
- Все эндпоинты с описаниями
- Все схемы данных (ProductCreate, OrderResponse, и т.д.)
- Коды ошибок (400, 404, 409, 500)
- Примеры запросов/ответов

**Как показать:**
```bash
# Swagger UI доступен по адресу
http://localhost:8002/docs
```

**Что рассказать:**
- "OpenAPI - это контракт API, описывает все эндпоинты, параметры и ответы"
- "Автоматически генерируется Swagger UI для тестирования"
- "Используется для генерации Pydantic моделей (задание 3)"

---

## Задание 2: CRUD операции (1 балл) ✅

**Файлы:**
- `services/product-service/app/routers/products.py` - эндпоинты
- `services/product-service/app/services/product_service.py` - бизнес-логика

**Реализованные операции:**

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/products` | Создать товар |
| GET | `/products` | Список товаров (пагинация + фильтры) |
| GET | `/products/{id}` | Получить товар по ID |
| PUT | `/products/{id}` | Обновить товар |
| DELETE | `/products/{id}` | Удалить товар (soft delete) |

**Как показать:**
```bash
# Создать товар
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Ноутбук","price":50000,"stock":10,"category":"Электроника","status":"ACTIVE"}'

# Получить список
curl http://localhost:8002/products?page=0&size=10

# Получить по ID
curl http://localhost:8002/products/{id}
```

**Что рассказать:**
- "CRUD - Create, Read, Update, Delete"
- "Пагинация реализована через параметры page и size"
- "Фильтрация по статусу и категории"
- "DELETE делает soft delete (меняет status на ARCHIVED)"

---

## Задание 3: Кодогенерация из OpenAPI (1 балл) ✅

**Файлы:**
- `services/product-service/generate_models.sh` - скрипт генерации
- `services/product-service/app/generated/models.py` - сгенерированные модели
- `services/product-service/Dockerfile` - автоматический запуск при сборке

**Как работает:**
1. OpenAPI спецификация → `datamodel-codegen` → Pydantic модели
2. Генерация происходит при сборке Docker образа
3. Модели используются в роутерах для валидации

**Как показать:**
```bash
# Посмотреть сгенерированный код
cat services/product-service/app/generated/models.py

# Пересобрать и увидеть генерацию
docker-compose build product-service
```

**Что рассказать:**
- "Используем datamodel-code-generator для генерации Pydantic моделей из OpenAPI"
- "Генерация автоматическая при сборке Docker"
- "Все валидации из OpenAPI (minLength, maxLength, gt, ge) применяются автоматически"
- "Единый источник правды - OpenAPI спецификация"

**Пример сгенерированного кода:**
```python
class ProductCreate(BaseModel):
    name: constr(min_length=1, max_length=255) = Field(...)
    price: condecimal(gt=0.01) = Field(...)
    stock: conint(ge=0) = Field(...)
```

---

## Задание 4: PostgreSQL + миграции (1 балл) ✅

**Файлы:**
- `docker-compose.yml` - 2 PostgreSQL контейнера
- `services/product-service/alembic/versions/001_initial_schema.py` - миграция
- `services/order-service/alembic/versions/001_initial_schema.py` - миграция

**Что сделано:**
- 2 отдельные БД (products на 5432, orders на 5433)
- Alembic для управления миграциями
- Автоматическое применение миграций при старте

**Таблицы:**

**Product Service:**
- `products` (id, name, description, price, stock, category, status, created_at, updated_at)
- `promo_codes` (id, code, discount_type, discount_value, max_uses, current_uses, valid_from, valid_until, active)

**Order Service:**
- `orders` (id, user_id, status, total_amount, discount_amount, promo_code_id, created_at, updated_at)
- `order_items` (id, order_id, product_id, quantity, price_at_order)
- `user_operations` (id, user_id, operation_type, order_id, timestamp)

**Как показать:**
```bash
# Подключиться к БД
docker exec -it service-oriented-architecture-postgres-products-1 psql -U marketplace -d marketplace

# Посмотреть таблицы
\dt

# Посмотреть структуру
\d products
```

**Что рассказать:**
- "Используем Alembic для версионирования схемы БД"
- "Миграции применяются автоматически при старте контейнера"
- "Каждый сервис имеет свою БД (принцип микросервисов)"

---

## Задание 5: Обработка ошибок (1 балл) ✅

**Файлы:**
- `services/product-service/app/exceptions.py` - кастомные исключения
- `services/product-service/app/main.py` - обработчики ошибок

**Реализованные коды ошибок:**

| Код | HTTP | Описание |
|-----|------|----------|
| PRODUCT_NOT_FOUND | 404 | Товар не найден |
| PRODUCT_INACTIVE | 400 | Товар неактивен |
| ORDER_NOT_FOUND | 404 | Заказ не найден |
| ORDER_LIMIT_EXCEEDED | 400 | Превышен лимит заказов |
| INSUFFICIENT_STOCK | 400 | Недостаточно товара |
| PROMO_CODE_INVALID | 400 | Промокод недействителен |
| VALIDATION_ERROR | 400 | Ошибка валидации |

**Формат ответа:**
```json
{
  "error_code": "PRODUCT_NOT_FOUND",
  "message": "Товар с ID ... не найден",
  "details": {"product_id": "..."}
}
```

**Как показать:**
```bash
# Попробовать получить несуществующий товар
curl http://localhost:8002/products/00000000-0000-0000-0000-000000000000

# Создать товар с невалидными данными
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"","price":-100}'
```

**Что рассказать:**
- "Все ошибки возвращаются в едином формате с error_code"
- "Валидация Pydantic автоматически возвращает VALIDATION_ERROR"
- "Кастомные исключения для бизнес-логики"

---

## Задание 6: Валидация (1 балл) ✅

**Где реализовано:**
- Pydantic модели (автоматически из OpenAPI)
- Кастомные валидаторы в сервисах

**Примеры валидаций:**

**На уровне Pydantic:**
```python
class ProductCreate(BaseModel):
    name: constr(min_length=1, max_length=255)  # Длина строки
    price: condecimal(gt=0.01)                   # Больше 0
    stock: conint(ge=0)                          # Неотрицательное
    status: ProductStatus                        # Enum
```

**На уровне бизнес-логики:**
```python
# Проверка остатков
if product.stock < quantity:
    raise InsufficientStockException()

# Проверка промокода
if promo_code.current_uses >= promo_code.max_uses:
    raise PromoCodeInvalidException("Промокод исчерпан")
```

**Как показать:**
```bash
# Невалидная цена
curl -X POST http://localhost:8002/products \
  -d '{"name":"Test","price":-100,"stock":10,"category":"Test","status":"ACTIVE"}'

# Невалидный промокод
curl -X POST http://localhost:8003/orders \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{"items":[{"product_id":"...","quantity":1}],"promo_code":"INVALID!!!"}'
```

**Что рассказать:**
- "Валидация на 2 уровнях: Pydantic (формат) и бизнес-логика (правила)"
- "Pydantic автоматически проверяет типы, длины, диапазоны"
- "Бизнес-логика проверяет остатки, лимиты, промокоды"

---

## Задание 7: Сложная бизнес-логика (1 балл) ✅

**Файл:** `services/order-service/app/services/order_service.py`

**Реализованная логика создания заказа (8 шагов):**

1. **Rate Limiting** - не более 10 заказов в час на пользователя
2. **Проверка активных заказов** - не более 3 активных заказов
3. **Валидация товаров** - все товары существуют и активны
4. **Проверка остатков** - достаточно товара на складе
5. **Резервирование товаров** - HTTP запрос в Product Service
6. **Снимок цен** - сохранение цены на момент заказа
7. **Применение промокода** - расчет скидки
8. **Логирование операций** - запись в user_operations

**Логика отмены заказа:**
- Проверка владельца
- Проверка статуса (можно отменить только CREATED/PAYMENT_PENDING)
- Освобождение товаров (HTTP запрос)
- Декремент использований промокода
- Отправка события в Kafka

**Как показать:**
```bash
# Создать заказ с промокодом
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{
    "items": [{"product_id": "...","quantity": 2}],
    "promo_code": "SUMMER2024"
  }'

# Отменить заказ
curl -X POST http://localhost:8003/orders/{id}/cancel \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000"
```

**Что рассказать:**
- "Создание заказа - это сложный процесс с 8 проверками"
- "Используем HTTP для синхронной коммуникации (резервирование товаров)"
- "Используем Kafka для асинхронных событий (order.created)"
- "Транзакционность: если что-то упало - откатываем резервирование"

---

## Задание 8: Логирование (1 балл) ✅

**Файлы:**
- `services/product-service/app/middleware/logging_middleware.py`
- `services/order-service/app/middleware/logging_middleware.py`

**Что логируется:**
```json
{
  "request_id": "uuid",
  "method": "POST",
  "endpoint": "/products",
  "status_code": 201,
  "duration_ms": 45.2,
  "user_id": "uuid",
  "timestamp": "2026-03-09T16:28:39Z"
}
```

**Как показать:**
```bash
# Посмотреть логи
docker-compose logs product-service | grep request_id

# Сделать запрос и увидеть лог
curl -X POST http://localhost:8002/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","price":100,"stock":10,"category":"Test","status":"ACTIVE"}'
```

**Что рассказать:**
- "JSON-логирование для удобного парсинга"
- "request_id для трейсинга запросов"
- "Маскирование чувствительных данных (password, token)"
- "Логируется каждый HTTP запрос"

---

## Микросервисная архитектура

**Почему микросервисы:**
1. **Независимое масштабирование** - можно масштабировать только Product Service
2. **Изоляция отказов** - падение Order Service не влияет на Product Service
3. **Разные БД** - каждый сервис владеет своими данными
4. **Независимая разработка** - разные команды могут работать параллельно

**Коммуникация между сервисами:**

**Синхронная (HTTP):**
```python
# Order Service → Product Service
async def reserve_stock(product_id, quantity):
    response = await httpx.post(
        f"{PRODUCT_SERVICE_URL}/products/{product_id}/reserve",
        json={"quantity": quantity}
    )
```

**Асинхронная (Kafka):**
```python
# Order Service → Kafka
await kafka_producer.send_event("order.created", {
    "order_id": order.id,
    "user_id": order.user_id,
    "total_amount": order.total_amount
})
```

---

## Как запустить проект

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f product-service

# Остановить
docker-compose down
```

**Доступные эндпоинты:**
- Product Service: http://localhost:8002
- Order Service: http://localhost:8003
- Swagger UI: http://localhost:8002/docs

---

## Возможные вопросы и ответы

**Q: Почему 2 отдельные БД?**
A: Принцип микросервисов - каждый сервис владеет своими данными. Это позволяет независимо масштабировать и изменять схему БД.

**Q: Зачем Kafka если есть HTTP?**
A: HTTP - для синхронных операций (резервирование товаров). Kafka - для асинхронных событий (уведомления, аналитика). Kafka не блокирует основной поток.

**Q: Что если Product Service упадет во время создания заказа?**
A: Order Service получит ошибку при резервировании и не создаст заказ. Транзакция откатится.

**Q: Как работает кодогенерация?**
A: При сборке Docker запускается скрипт generate_models.sh, который читает OpenAPI и генерирует Pydantic модели с помощью datamodel-code-generator.

**Q: Что такое soft delete?**
A: Вместо удаления записи из БД мы меняем status на ARCHIVED. Данные остаются в БД для аудита.

**Q: Как работает rate limiting?**
A: Считаем количество операций пользователя за последний час в таблице user_operations. Если больше 10 - отклоняем запрос.

---

## Итоговая таблица выполненных заданий

| № | Задание | Баллы | Статус | Файлы |
|---|---------|-------|--------|-------|
| 1 | OpenAPI спецификация | 1 | ✅ | `openapi/marketplace-api.yaml` |
| 2 | CRUD операции | 1 | ✅ | `app/routers/products.py` |
| 3 | Кодогенерация | 1 | ✅ | `generate_models.sh`, `app/generated/` |
| 4 | PostgreSQL + миграции | 1 | ✅ | `alembic/versions/`, `docker-compose.yml` |
| 5 | Обработка ошибок | 1 | ✅ | `app/exceptions.py`, `app/main.py` |
| 6 | Валидация | 1 | ✅ | Pydantic модели, сервисы |
| 7 | Сложная бизнес-логика | 1 | ✅ | `app/services/order_service.py` |
| 8 | Логирование | 1 | ✅ | `app/middleware/logging_middleware.py` |
| **Итого** | | **8/10** | | |

---

## Советы для защиты

1. **Покажи архитектуру** - нарисуй схему микросервисов на доске
2. **Запусти проект** - покажи работающие эндпоинты через Swagger UI
3. **Покажи код** - открой ключевые файлы и объясни логику
4. **Покажи логи** - продемонстрируй JSON-логирование
5. **Покажи БД** - подключись к PostgreSQL и покажи таблицы
6. **Будь готов к вопросам** - про микросервисы, Kafka, транзакции

**Удачи на защите! 🚀**

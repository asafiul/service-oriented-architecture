# Микросервисная архитектура Marketplace

## Архитектура согласно C4 диаграмме

Система разделена на независимые микросервисы с отдельными базами данных и асинхронной коммуникацией через Kafka.

## Сервисы

### 1. Product Service (порт 8002)
**Ответственность:** Управление товарами и промокодами

**База данных:** `postgres-products` (порт 5432)
- Таблица `products` - каталог товаров
- Таблица `promo_codes` - промокоды

**API эндпоинты:**
- `POST /products` - создание товара
- `GET /products` - список товаров с пагинацией
- `GET /products/{id}` - получение товара
- `PUT /products/{id}` - обновление товара
- `DELETE /products/{id}` - архивация товара
- `POST /products/{id}/reserve` - резервирование stock
- `POST /products/{id}/release` - возврат stock
- `POST /promo-codes` - создание промокода
- `GET /promo-codes/{code}` - получение промокода
- `POST /promo-codes/{id}/increment` - инкремент использований
- `POST /promo-codes/{id}/decrement` - декремент использований

### 2. Order Service (порт 8003)
**Ответственность:** Управление заказами

**База данных:** `postgres-orders` (порт 5433)
- Таблица `orders` - заказы
- Таблица `order_items` - позиции заказов
- Таблица `user_operations` - операции для rate limiting

**API эндпоинты:**
- `POST /orders` - создание заказа
- `GET /orders/{id}` - получение заказа
- `POST /orders/{id}/cancel` - отмена заказа

**Интеграции:**
- HTTP клиент к Product Service для валидации товаров и промокодов
- Kafka producer для отправки событий

**Kafka события:**
- `order.created` - заказ создан
- `order.canceled` - заказ отменен

### 3. User Service (порт 8001)
**Ответственность:** Управление пользователями (базовая реализация)

## Инфраструктура

### PostgreSQL
- **postgres-products** - БД для Product Service (порт 5432)
- **postgres-orders** - БД для Order Service (порт 5433)

Каждый сервис имеет эксклюзивный доступ к своей БД.

### Apache Kafka
- **Zookeeper** (порт 2181) - координация Kafka
- **Kafka** (порт 9092 внутри, 29092 снаружи) - брокер сообщений

Используется для асинхронной коммуникации между сервисами.

## Взаимодействие сервисов

### Синхронное (HTTP)
Order Service → Product Service:
- Валидация товаров
- Резервирование/возврат stock
- Получение промокодов
- Управление использованием промокодов

### Асинхронное (Kafka)
Order Service → Kafka:
- События создания заказов
- События отмены заказов

В будущем можно добавить:
- Notification Service (слушает события заказов)
- Payment Service (слушает события заказов)

## Бизнес-логика заказов

### Создание заказа
1. Order Service проверяет rate limit
2. Order Service проверяет активные заказы
3. Order Service запрашивает данные товаров у Product Service (HTTP)
4. Order Service резервирует stock через Product Service (HTTP)
5. Order Service применяет промокод через Product Service (HTTP)
6. Order Service сохраняет заказ в свою БД
7. Order Service отправляет событие `order.created` в Kafka

### Отмена заказа
1. Order Service проверяет владельца и статус
2. Order Service возвращает stock через Product Service (HTTP)
3. Order Service декрементирует использование промокода (HTTP)
4. Order Service обновляет статус в своей БД
5. Order Service отправляет событие `order.canceled` в Kafka

## Преимущества архитектуры

✅ **Независимость сервисов** - каждый сервис можно разрабатывать и деплоить отдельно
✅ **Изоляция данных** - каждый сервис владеет своими данными
✅ **Масштабируемость** - можно масштабировать сервисы независимо
✅ **Отказоустойчивость** - падение одного сервиса не ломает другие
✅ **Асинхронность** - Kafka обеспечивает надежную доставку событий

## Запуск системы

```bash
docker-compose up -d
```

Это запустит:
- 2 PostgreSQL базы данных
- Zookeeper + Kafka
- Product Service
- Order Service
- User Service

## Проверка работы

```bash
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8001/health
```

## Миграции

Миграции применяются автоматически при старте каждого сервиса через Alembic.

## Логи

```bash
docker-compose logs -f product-service
docker-compose logs -f order-service
docker-compose logs -f kafka
```

## Соответствие C4 диаграмме

✅ Product Service - отдельный сервис с отдельной БД
✅ Order Service - отдельный сервис с отдельной БД
✅ Message Queue (Kafka) - для асинхронной коммуникации
✅ Синхронное взаимодействие через HTTP
✅ Асинхронное взаимодействие через Kafka
✅ Изоляция данных - каждый сервис со своей БД

## Дальнейшее развитие

Можно добавить:
- API Gateway (Nginx/Kong) для единой точки входа
- Payment Service для обработки платежей
- Notification Service для отправки уведомлений
- Recommendation Service для персонализации
- Service Discovery (Consul/Eureka)
- Distributed Tracing (Jaeger/Zipkin)
- Centralized Logging (ELK Stack)

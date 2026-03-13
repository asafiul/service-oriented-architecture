# Kafka и Zookeeper - Объяснение

## 🐘 Что такое Zookeeper?

**Zookeeper** - это координационный сервис для распределенных систем.

**Простыми словами:** Это как "диспетчер" для Kafka, который:
- Следит за тем, какие Kafka брокеры живы
- Хранит метаданные о топиках
- Координирует работу Kafka кластера
- Выбирает лидеров для партиций

**Аналогия:** Если Kafka - это почтовая служба, то Zookeeper - это главный офис, который знает где все почтальоны и какие маршруты они обслуживают.

## 📨 Что такое Kafka?

**Kafka** - это распределенная система обмена сообщениями (message broker).

**Простыми словами:** Это как "почтовый ящик" между сервисами:
- Один сервис кладет сообщение (producer)
- Другой сервис забирает сообщение (consumer)
- Сообщения не теряются, даже если получатель временно недоступен

## 🔄 Как мы используем Kafka в проекте?

### Где используется:

**Order Service отправляет события в Kafka:**

Файл: [`services/order-service/app/kafka_producer.py`](services/order-service/app/kafka_producer.py)
```python
class KafkaProducerClient:
    async def send_event(self, topic: str, event: dict):
        await self.producer.send_and_wait(topic, event)
```

Файл: [`services/order-service/app/services/order_service.py`](services/order-service/app/services/order_service.py)
```python
# После создания заказа
await kafka_producer.send_event('order.created', {
    'order_id': str(order.id),
    'user_id': str(user_id),
    'total_amount': float(total_amount)
})

# После отмены заказа
await kafka_producer.send_event('order.canceled', {
    'order_id': str(order.id),
    'user_id': str(user_id)
})
```

### Какие события отправляются:

1. **`order.created`** - когда создается новый заказ
   - Содержит: order_id, user_id, total_amount, items_count

2. **`order.canceled`** - когда заказ отменяется
   - Содержит: order_id, user_id

### Зачем это нужно?

**Асинхронная коммуникация:**
- Order Service не ждет ответа
- Другие сервисы могут подписаться на эти события
- Если сервис упал, события не потеряются

**Примеры использования:**
- **Notification Service** мог бы слушать `order.created` и отправлять email
- **Payment Service** мог бы слушать `order.created` и создавать платеж
- **Analytics Service** мог бы собирать статистику по заказам

## 🎯 Архитектура в нашем проекте:

```
Order Service (Producer)
    ↓
    ↓ отправляет события
    ↓
Kafka (Message Broker)
    ↓
    ↓ события хранятся в топиках
    ↓
[Будущие Consumer сервисы]
    - Notification Service (отправка уведомлений)
    - Payment Service (обработка платежей)
    - Analytics Service (сбор статистики)
```

## 🔍 Как проверить что Kafka работает?

### 1. Проверить статус Kafka
```bash
docker-compose ps kafka
```

### 2. Посмотреть логи Order Service
```bash
docker-compose logs order-service | grep -i kafka
```

Должно быть:
```
INFO:     Kafka producer started: kafka:9092
```

### 3. Создать заказ и посмотреть события
```bash
# Создать заказ
curl -X POST http://localhost:8003/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{"items":[{"product_id":"<uuid>","quantity":1}]}'

# Посмотреть логи
docker-compose logs order-service | grep "Event sent to Kafka"
```

Должно быть:
```
INFO:     Event sent to Kafka topic 'order.created': {'order_id': '...', ...}
```

### 4. Посмотреть топики в Kafka
```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### 5. Прочитать сообщения из топика
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic order.created \
  --from-beginning
```

## 📊 Схема работы:

```
1. Пользователь создает заказ
   ↓
2. Order Service:
   - Сохраняет заказ в БД
   - Отправляет событие в Kafka
   ↓
3. Kafka:
   - Сохраняет событие в топик 'order.created'
   - Событие не теряется
   ↓
4. Consumer сервисы (в будущем):
   - Notification Service читает событие → отправляет email
   - Payment Service читает событие → создает платеж
   - Analytics Service читает событие → обновляет статистику
```

## ✅ Преимущества Kafka:

1. **Надежность** - события не теряются
2. **Асинхронность** - Order Service не ждет ответа
3. **Масштабируемость** - можно добавлять новых consumers
4. **Отказоустойчивость** - если consumer упал, события сохраняются
5. **Разделение ответственности** - каждый сервис делает свое

## 🎓 Для защиты:

**Вопрос:** "Зачем вы используете Kafka?"

**Ответ:** 
"Kafka используется для асинхронной коммуникации между микросервисами. Когда Order Service создает заказ, он отправляет событие `order.created` в Kafka. Это позволяет другим сервисам (Notification, Payment, Analytics) независимо обрабатывать эти события без блокировки Order Service. Zookeeper координирует работу Kafka кластера."

**Можно показать:**
1. Код отправки событий в [`order_service.py`](services/order-service/app/services/order_service.py)
2. Kafka producer в [`kafka_producer.py`](services/order-service/app/kafka_producer.py)
3. Логи с событиями: `docker-compose logs order-service | grep Kafka`

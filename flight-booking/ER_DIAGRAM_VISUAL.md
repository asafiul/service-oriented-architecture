# ER-диаграмма Flight Booking System (Визуальная)

---

## Flight Service Database

```mermaid
erDiagram
    FLIGHTS ||--o{ SEAT_RESERVATIONS : "has"
    
    FLIGHTS {
        integer id PK "Primary Key"
        varchar flight_number "Номер рейса (SU1234)"
        varchar airline "Авиакомпания"
        varchar origin "Аэропорт вылета (IATA)"
        varchar destination "Аэропорт прилета (IATA)"
        datetime departure_time "Время вылета"
        datetime arrival_time "Время прилета"
        integer total_seats "Общее количество мест"
        integer available_seats "Доступные места"
        float price "Цена билета"
        enum status "SCHEDULED, DEPARTED, CANCELLED, COMPLETED"
        datetime created_at
        datetime updated_at
    }
    
    SEAT_RESERVATIONS {
        integer id PK "Primary Key"
        integer flight_id FK "→ flights.id"
        varchar booking_id UK "ID из Booking Service"
        integer seat_count "Количество мест"
        enum status "ACTIVE, RELEASED, EXPIRED"
        datetime created_at
        datetime updated_at
    }
```

## Booking Service Database

```mermaid
erDiagram
    BOOKINGS {
        integer id PK "Primary Key"
        integer user_id "ID пользователя"
        integer flight_id "Ссылка на Flight Service"
        varchar passenger_name "Имя пассажира"
        varchar passenger_email "Email пассажира"
        integer seat_count "Количество мест"
        float total_price "Общая стоимость (snapshot)"
        enum status "CONFIRMED, CANCELLED"
        datetime created_at
        datetime updated_at
    }
```

## Связи между сервисами

```mermaid
graph LR
    subgraph "Booking Service DB"
        B[bookings]
    end
    
    subgraph "Flight Service DB"
        F[flights]
        SR[seat_reservations]
    end
    
    B -->|flight_id| F
    B -.->|booking_id| SR
    F -->|id| SR
    
    style B fill:#e1f5ff
    style F fill:#fff4e1
    style SR fill:#fff4e1
```

## Полная архитектура системы

```mermaid
graph TB
    subgraph "Client Layer"
        C[REST Client]
    end
    
    subgraph "Booking Service"
        BS[FastAPI REST API]
        BDB[(PostgreSQL<br/>bookings)]
        CB[Circuit Breaker]
        RC[Retry Logic]
    end
    
    subgraph "Flight Service"
        FS[gRPC Server]
        FDB[(PostgreSQL<br/>flights, seat_reservations)]
        REDIS[Redis Sentinel<br/>Master + Replica]
        AUTH[API Key Auth]
    end
    
    C -->|HTTP/REST| BS
    BS -->|gRPC| CB
    CB --> RC
    RC -->|with retry| FS
    BS -->|SQL| BDB
    FS -->|SQL| FDB
    FS -->|Cache| REDIS
    FS -->|Validate| AUTH
    
    style C fill:#e3f2fd
    style BS fill:#fff3e0
    style FS fill:#f3e5f5
    style BDB fill:#c8e6c9
    style FDB fill:#c8e6c9
    style REDIS fill:#ffccbc
    style CB fill:#ffeb3b
    style RC fill:#ffeb3b
    style AUTH fill:#ff9800
```

## Constraints (Ограничения целостности)

### flights
```sql
-- Положительные значения
CHECK (total_seats > 0)
CHECK (available_seats >= 0)
CHECK (price > 0)

-- Логические ограничения
CHECK (available_seats <= total_seats)
CHECK (arrival_time > departure_time)

-- Уникальность
UNIQUE (flight_number, departure_time)
```

### seat_reservations
```sql
-- Положительные значения
CHECK (seat_count > 0)

-- Уникальность
UNIQUE (booking_id)

-- Foreign Key
FOREIGN KEY (flight_id) REFERENCES flights(id)
```

### bookings
```sql
-- Положительные значения
CHECK (seat_count > 0)
CHECK (total_price > 0)
```

## Индексы для производительности

### flights
- `id` (PRIMARY KEY)
- `flight_number` (для поиска по номеру)
- `origin` (для поиска по маршруту)
- `destination` (для поиска по маршруту)
- `departure_time` (для поиска по дате)
- `status` (для фильтрации SCHEDULED)
- `(flight_number, departure_time)` UNIQUE

### seat_reservations
- `id` (PRIMARY KEY)
- `flight_id` (для JOIN)
- `booking_id` UNIQUE (для быстрого поиска)
- `status` (для фильтрации ACTIVE)

### bookings
- `id` (PRIMARY KEY)
- `user_id` (для списка бронирований пользователя)
- `flight_id` (для связи с рейсом)
- `status` (для фильтрации)

## Нормализация (3NF)

### 1NF (Первая нормальная форма)
- Все атрибуты атомарны
- Нет повторяющихся групп
- Каждая таблица имеет первичный ключ

### 2NF (Вторая нормальная форма)
- Выполнена 1NF
- Все неключевые атрибуты полностью зависят от первичного ключа
- Нет частичных зависимостей

###  3NF (Третья нормальная форма)
- Выполнена 2NF
- Нет транзитивных зависимостей
- Все неключевые атрибуты зависят только от первичного ключа

**Пример:** В таблице `bookings` поле `total_price` - это snapshot цены на момент бронирования, а не вычисляемое значение. Это предотвращает транзитивную зависимость через `flight_id → price`.

## Транзакционные сценарии

### Создание бронирования (с SELECT FOR UPDATE)

```mermaid
sequenceDiagram
    participant BS as Booking Service
    participant FS as Flight Service
    participant DB as Flight DB
    
    BS->>FS: GetFlight(flight_id)
    FS->>DB: SELECT * FROM flights WHERE id=?
    DB-->>FS: flight data
    FS-->>BS: Flight{price, available_seats}
    
    BS->>FS: ReserveSeats(flight_id, seat_count, booking_id)
    FS->>DB: BEGIN TRANSACTION
    FS->>DB: SELECT * FROM flights WHERE id=? FOR UPDATE
    DB-->>FS: flight (locked)
    
    alt Достаточно мест
        FS->>DB: UPDATE flights SET available_seats = available_seats - ?
        FS->>DB: INSERT INTO seat_reservations
        FS->>DB: COMMIT
        FS-->>BS: Success
        BS->>BS: Create booking in local DB
    else Недостаточно мест
        FS->>DB: ROLLBACK
        FS-->>BS: RESOURCE_EXHAUSTED
        BS->>BS: Don't create booking
    end
```

### Отмена бронирования

```mermaid
sequenceDiagram
    participant BS as Booking Service
    participant FS as Flight Service
    participant DB as Flight DB
    
    BS->>FS: ReleaseReservation(booking_id)
    FS->>DB: BEGIN TRANSACTION
    FS->>DB: SELECT * FROM seat_reservations WHERE booking_id=? FOR UPDATE
    DB-->>FS: reservation
    FS->>DB: SELECT * FROM flights WHERE id=? FOR UPDATE
    DB-->>FS: flight (locked)
    FS->>DB: UPDATE flights SET available_seats = available_seats + ?
    FS->>DB: UPDATE seat_reservations SET status='RELEASED'
    FS->>DB: COMMIT
    FS-->>BS: Success
    BS->>BS: Update booking status to CANCELLED
```

## Кеширование (Redis)

```mermaid
graph LR
    subgraph "Cache Keys"
        K1["flight:{id}<br/>TTL: 5 min"]
        K2["search:{origin}:{dest}:{date}<br/>TTL: 5 min"]
    end
    
    subgraph "Invalidation Events"
        E1[ReserveSeats]
        E2[ReleaseReservation]
        E3[UpdateFlight]
    end
    
    E1 -->|DELETE| K1
    E1 -->|DELETE pattern| K2
    E2 -->|DELETE| K1
    E2 -->|DELETE pattern| K2
    E3 -->|DELETE| K1
    E3 -->|DELETE pattern| K2
    
    style K1 fill:#ffccbc
    style K2 fill:#ffccbc
    style E1 fill:#fff59d
    style E2 fill:#fff59d
    style E3 fill:#fff59d
```

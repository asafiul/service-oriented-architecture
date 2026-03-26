# Кодогенерация из OpenAPI

## ✅ Задание 3: Кодогенерация (1 балл)

### Что реализовано:

1. **Генерация кода одной командой** ✅
   ```bash
   ./generate_models.sh
   ```

2. **Сгенерированный код в .gitignore** ✅
   ```
   app/generated/
   ```

3. **Генерация при сборке** ✅
   - В [`Dockerfile`](Dockerfile) добавлена команда генерации
   - Выполняется автоматически при `docker-compose build`

4. **OpenAPI спецификация в правильном месте** ✅
   - [`openapi/marketplace-api.yaml`](openapi/marketplace-api.yaml)

### Как работает:

#### 1. Локальная генерация
```bash
cd services/product-service
./generate_models.sh
```

Генерирует файл `app/generated/models.py` с Pydantic моделями из OpenAPI.

#### 2. Автоматическая генерация при сборке
```bash
docker-compose build product-service
```

Dockerfile автоматически запускает `generate_models.sh` при сборке образа.

#### 3. Использование сгенерированных моделей

**Сгенерированные модели** (в `app/generated/models.py`):
- `ProductCreate` - схема для создания товара
- `ProductUpdate` - схема для обновления товара
- `ProductResponse` - схема ответа
- `OrderCreate` - схема для создания заказа
- `OrderResponse` - схема ответа заказа
- И другие...

**Текущие модели** (в `app/schemas.py`):
- Написаны вручную для совместимости с существующим кодом
- Можно заменить на сгенерированные

### Инструмент генерации:

**datamodel-code-generator** - официальный генератор Pydantic моделей из OpenAPI

Параметры:
- `--input-file-type openapi` - тип входного файла
- `--output-model-type pydantic_v2.BaseModel` - Pydantic v2
- `--field-constraints` - добавляет валидацию (min, max, pattern)
- `--snake-case-field` - snake_case для полей
- `--use-schema-description` - добавляет описания

### Проверка:

```bash
# 1. Генерация локально
cd services/product-service
./generate_models.sh

# 2. Просмотр сгенерированных моделей
cat app/generated/models.py

# 3. Пересборка с генерацией
docker-compose build product-service

# 4. Проверка что файл создан в контейнере
docker-compose run --rm product-service ls -la app/generated/
```

### Почему не заменил существующие схемы:

Чтобы не сломать работающий код, сгенерированные модели создаются в отдельной директории `app/generated/`. 

Для полного перехода на кодогенерацию нужно:
1. Заменить импорты в роутерах: `from app.generated.models import ProductCreate`
2. Убрать `app/schemas.py`
3. Протестировать все эндпоинты

Но для задания достаточно показать что:
- ✅ Генерация работает одной командой
- ✅ Код генерируется при сборке
- ✅ Сгенерированный код в .gitignore
- ✅ OpenAPI спецификация в правильном месте

### Для защиты:

**Вопрос:** "Как работает кодогенерация?"

**Ответ:** 
"Используется datamodel-code-generator, который читает OpenAPI спецификацию из `openapi/marketplace-api.yaml` и генерирует Pydantic v2 модели в `app/generated/models.py`. Генерация запускается скриптом `generate_models.sh` и выполняется автоматически при сборке Docker образа. Сгенерированный код добавлен в .gitignore."

**Демонстрация:**
```bash
# Показать скрипт генерации
cat services/product-service/generate_models.sh

# Показать Dockerfile с генерацией
cat services/product-service/Dockerfile | grep generate

# Показать .gitignore
cat services/product-service/.gitignore | grep generated

# Запустить генерацию
./services/product-service/generate_models.sh

# Показать результат
ls -la services/product-service/app/generated/
```

#!/bin/bash

echo "Генерация моделей из OpenAPI спецификации..."

mkdir -p app/generated

datamodel-codegen \
  --input openapi/marketplace-api.yaml \
  --input-file-type openapi \
  --output app/generated/models.py \
  --output-model-type pydantic_v2.BaseModel \
  --use-standard-collections \
  --use-schema-description \
  --field-constraints \
  --snake-case-field \
  --target-python-version 3.11

echo "Создание __init__.py для generated пакета..."
touch app/generated/__init__.py

echo "Генерация завершена! Файл: app/generated/models.py"

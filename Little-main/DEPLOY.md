# RAG Chat Backend — Инструкция по разворачиванию

## Обзор

FastAPI-бэкенд для AI-ассистента: принимает вопросы, ищет контекст в Elasticsearch
(два индекса + опционально Cognee), стримит ответы от Ollama через SSE.

---

## Архитектура

```
Клиент (gateway-portal / curl)
  ↓  HTTP / SSE
FastAPI Backend (порт 8000)
  ├── Elasticsearch — поиск по индексам knowledge_base и chunking_index
  ├── Ollama — генерация эмбеддингов + LLM-ответов
  └── Cognee (опционально) — граф знаний
```

---

## Предварительные требования

- **Docker** и **Docker Compose** (v2)
- **Ollama** запущен и доступен (по умолчанию: `http://10.0.10.153:11434`)
  - Модели загружены: `qwen3.5:4b` (LLM) и `qwen3-embedding:0.6b` (эмбеддинги)
- Порты `8000` и `9200` свободны

---

## Быстрый старт (через единый docker-compose)

### 1. Перейдите в корень проекта

```bash
cd /путь/к/Little
```

### 2. Настройте переменные окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```bash
# Главные настройки — укажите адрес Ollama
RAG_OLLAMA_URL=http://10.0.10.153:11434
RAG_OLLAMA_MODEL=qwen3.5:4b
RAG_OLLAMA_EMBED_MODEL=qwen3-embedding:0.6b
```

### 3. Запустите

```bash
docker compose up --build -d
```

Это поднимет:
- **Elasticsearch** на `localhost:9200`
- **RAG Backend** на `localhost:8000`

### 4. Проверьте

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

---

## С Cognee (опционально)

```bash
docker compose --profile cognee up --build -d
```

В `.env` включите:
```
RAG_COGNEE_ENABLED=true
```

---

## С Kibana для отладки

```bash
docker compose --profile debug up --build -d
```

Kibana будет на `localhost:5601`.

---

## Разворачивание только бэкенда (без docker-compose)

### 1. Установите зависимости

```bash
cd Little-main/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Задайте переменные окружения

```bash
export RAG_ELASTICSEARCH_URL=http://localhost:9200
export RAG_OLLAMA_URL=http://10.0.10.153:11434
export RAG_OLLAMA_MODEL=qwen3.5:4b
export RAG_OLLAMA_EMBED_MODEL=qwen3-embedding:0.6b
```

### 3. Запустите

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Переменные окружения

Все переменные имеют префикс `RAG_`.

| Переменная | По умолчанию | Описание |
|---|---|---|
| `RAG_ELASTICSEARCH_URL` | `http://localhost:9200` | URL Elasticsearch |
| `RAG_ELASTICSEARCH_INDEX` | `knowledge_base` | Основной индекс (загруженные документы) |
| `RAG_ELASTICSEARCH_MART_INDEX` | `chunking_index` | Индекс из mart_meet (учебники) |
| `RAG_RAG_ENABLE_LEGACY_INDEX` | `true` | Искать в knowledge_base |
| `RAG_RAG_ENABLE_MART_INDEX` | `true` | Искать в chunking_index |
| `RAG_OLLAMA_URL` | `http://10.0.10.153:11434` | URL Ollama-сервера |
| `RAG_OLLAMA_MODEL` | `qwen3.5:4b` | LLM-модель для генерации ответов |
| `RAG_OLLAMA_EMBED_MODEL` | `qwen3-embedding:0.6b` | Модель для эмбеддингов |
| `RAG_RAG_TOP_K` | `5` | Кол-во документов для контекста |
| `RAG_RAG_MIN_SCORE` | `0.3` | Мин. порог релевантности (0–1) |
| `RAG_SESSION_MAX_HISTORY` | `20` | Макс. сообщений в сессии |
| `RAG_COGNEE_ENABLED` | `false` | Включить Cognee |
| `RAG_COGNEE_URL` | `http://localhost:8001` | URL Cognee API |
| `RAG_INGESTION_CHUNK_SIZE` | `1200` | Размер чанка при загрузке документов |
| `RAG_INGESTION_CHUNK_OVERLAP` | `200` | Перекрытие чанков |

---

## API-эндпоинты

### Чат (SSE-стрим)
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-1","message":"Что такое графит?"}'
```

**SSE-события:**
- `event: sources` — найденные документы (JSON)
- `event: token` — токены ответа
- `event: done` — конец ответа
- `event: error` — ошибка

### Загрузка документа
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@document.pdf" \
  -F "dataset_name=my_docs"
```

Поддерживаемые форматы: `.txt`, `.pdf`, `.docx`

### Управление сессиями
```bash
# Информация о сессии
curl http://localhost:8000/api/session/test-1

# История сообщений
curl http://localhost:8000/api/session/test-1/history

# Сброс сессии
curl -X DELETE http://localhost:8000/api/session/test-1
```

### Получение источника
```bash
curl http://localhost:8000/api/documents/source/knowledge_base/<doc_id>
```

---

## Загрузка данных из mart_meet

Если индекс `chunking_index` ещё не заполнен учебниками:

1. Убедитесь, что Elasticsearch запущен
2. Перейдите в `mart_meet/DmitriyMeet/chunking/python/`
3. Настройте `.env` (URL Elasticsearch и Ollama)
4. Запустите `python main.py`

Скрипт обработает PDF-файлы и создаст индексы `chunking_index` и `book_index`.

---

## Устранение неполадок

### Бэкенд не стартует
```bash
docker compose logs rag-backend
```
Частые причины: Elasticsearch ещё не готов (подождите 30 сек), неверный `RAG_ELASTICSEARCH_URL`.

### Пустые ответы от LLM
- Проверьте доступность Ollama: `curl http://10.0.10.153:11434/api/tags`
- Убедитесь, что модели загружены: `ollama list` на машине с Ollama

### Документы не находятся
- Проверьте индексы в Kibana: `http://localhost:5601`
- Убедитесь, что `RAG_RAG_ENABLE_LEGACY_INDEX=true` и/или `RAG_RAG_ENABLE_MART_INDEX=true`
- Понизьте `RAG_RAG_MIN_SCORE` (например, до `0.2`)

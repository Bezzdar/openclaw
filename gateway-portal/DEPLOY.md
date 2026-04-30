# Gateway Portal — Инструкция по обновлению и запуску

## Обзор

Корпоративный портал ИХТЦ на Next.js 16. Развёртывается в Docker-контейнере
в **режиме разработчика** (dev mode), чтобы правки в исходниках немедленно
отражались на портале без пересборки.

---

## Предварительные требования

- **Docker** и **Docker Compose** (v2) установлены на сервере
- Сетевой доступ к `10.0.10.155:8080` (OpenProject) и `10.0.10.157:3000` (Wiki)
- Порт `8000` свободен (или измените в `docker-compose.dev.yml`)

---

## Обновление портала (со старой версии на новую)

### 1. Подключитесь к серверу

```bash
ssh user@<IP-сервера>
```

### 2. Перейдите в папку портала

```bash
cd /путь/к/gateway-portal
```

### 3. Получите новые файлы

Если используете Git:
```bash
git pull origin main
```

Если копируете вручную (например, через scp):
```bash
# На локальной машине:
scp -r ./gateway-portal/ user@<IP-сервера>:/путь/к/gateway-portal/
```

### 4. Остановите старый контейнер

```bash
docker compose -f docker-compose.dev.yml down
```

### 5. Пересоберите и запустите новую версию

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

- `--build` — принудительная пересборка (устанавливает новые зависимости)
- `-d` — запуск в фоне

### 6. Проверьте работоспособность

```bash
# Статус контейнера
docker compose -f docker-compose.dev.yml ps

# Логи (следить в реальном времени)
docker compose -f docker-compose.dev.yml logs -f
```

Откройте в браузере: **http://<IP-сервера>:8000**

---

## Первый запуск (с нуля)

### 1. Скопируйте папку `gateway-portal` на сервер

```bash
scp -r ./gateway-portal/ user@<IP-сервера>:/opt/gateway-portal/
```

### 2. Запустите в режиме разработчика

```bash
cd /opt/gateway-portal
docker compose -f docker-compose.dev.yml up --build -d
```

Портал доступен по адресу: **http://<IP-сервера>:8000**

---

## Режим разработчика — как это работает

Файл `docker-compose.dev.yml` настроен так:

- **Volume mount**: Папка с исходниками монтируется внутрь контейнера (`./:/app`)
- **Hot reload**: Next.js dev-сервер автоматически перекомпилирует при изменении файлов
- **WATCHPACK_POLLING=true**: Обеспечивает отслеживание изменений файлов в Docker

**Для внесения правок:**
1. Измените файл в папке `gateway-portal/` на сервере
2. Next.js автоматически перекомпилирует (1–3 секунды)
3. Обновите страницу в браузере

---

## Управление данными

### Объявления

Файл: `public/data/announcements.json`
```json
{
  "active": true,
  "message": "Текст объявления.\nМожно использовать переносы строк."
}
```
Установите `"active": false`, чтобы скрыть объявление.

### Дни рождения

Файл: `public/data/birthdays.csv` (разделитель — `;`)
```
ФИО;Должность;Компания;Дата
Иванов Иван Иванович;Инженер;ИХТЦ;15.03.1990
```

### Ссылки в боковой панели

Файл: `components/sidebar.tsx`
- `navigationLinks` — внешние ссылки (OpenProject, Wiki, Сайт)
- `internalLinks` — внутренние ссылки-заглушки

---

## Полезные команды

```bash
# Перезапуск контейнера
docker compose -f docker-compose.dev.yml restart

# Остановка
docker compose -f docker-compose.dev.yml down

# Просмотр логов
docker compose -f docker-compose.dev.yml logs -f

# Зайти внутрь контейнера (для отладки)
docker compose -f docker-compose.dev.yml exec gateway-portal sh
```

---

## Смена порта

В `docker-compose.dev.yml` измените маппинг портов:
```yaml
ports:
  - "НОВЫЙ_ПОРТ:3000"
```

---

## Переход на production-режим

Когда портал стабилизируется, можно переключиться на production:
```bash
docker compose -f docker-compose.yml up --build -d
```
Это собирает оптимизированный standalone-билд (быстрее загрузка, меньше памяти),
но изменения потребуют пересборки (`--build`).

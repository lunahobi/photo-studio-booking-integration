# Система бронирования фотостудии с интеграцией платежных систем

## Описание проекта

Прототип интеграционного решения для системы бронирования залов фотостудии с интеграцией платежных шлюзов (ЮKassa, СберPay, Тинькофф Касса).

## Архитектура

Решение построено на базе микросервисной архитектуры с событийно-ориентированными интеграциями и API Gateway.

### Компоненты системы:

1. **API Gateway** (порт 5000) - центральная точка входа для всех клиентов (маршрутизация запросов)
2. **Booking Service** (порт 5001) - сервис управления бронированиями и календарем
3. **Payment Service** (порт 5002) - сервис обработки платежей и интеграции с платежными шлюзами
4. **Integration Service** (порт 5003) - сервис обработки событий и интеграций
5. **Notification Service** (порт 5004) - сервис отправки уведомлений (Telegram, Email)
6. **Message Broker** (порт 5050) - брокер сообщений для асинхронной коммуникации между сервисами

## Структура проекта

```
.
├── backend/
│   ├── api_gateway/           # API Gateway
│   ├── booking_service/       # Сервис бронирований
│   ├── payment_service/       # Сервис платежей
│   ├── integration_service/   # Сервис интеграций
│   ├── notification_service/  # Сервис уведомлений
│   ├── message_broker/        # Брокер сообщений
│   ├── schemas/               # Схемы данных (контракты)
│   ├── database/              # SQL схемы БД
│   └── tests/                 # Тесты
├── frontend/                  # React приложение
│   ├── src/
│   └── public/
├── requirements.txt           # Python зависимости
├── start_services.bat         # Скрипт запуска (Windows)
├── start_services.sh          # Скрипт запуска (Linux/Mac)
└── stop_services.bat          # Скрипт остановки (Windows)
```

## Быстрый старт

### 1. Установка зависимостей

**Python зависимости:**
```bash
pip install -r requirements.txt
```

**Frontend зависимости (опционально):**
```bash
cd frontend
npm install
npm start  # Запустит React приложение на http://localhost:3000
```

### 2. Запуск сервисов

**Windows:**
```bash
start_services.bat
```

**Остановка сервисов (Windows):**
```bash
stop_services.bat
```

**Linux/Mac:**
```bash
chmod +x start_services.sh
./start_services.sh
```

Все сервисы запустятся в отдельных окнах. Убедитесь, что порты 5000-5004 и 5050 свободны.

### 3. Проверка работы

После запуска проверьте статус сервисов:

```bash
curl http://localhost:5000/health  # API Gateway
curl http://localhost:5001/health  # Booking Service
curl http://localhost:5002/health  # Payment Service
curl http://localhost:5003/health  # Integration Service
curl http://localhost:5004/health  # Notification Service
curl http://localhost:5050/health  # Message Broker
```

### 4. Тестирование

**Автоматические тесты:**
```bash
cd backend
python tests/test_booking_flow.py
```

**Интерактивное тестирование:**
Откройте frontend в браузере (если запущен) или используйте API напрямую.

## API Endpoints

Все запросы проходят через **API Gateway** (порт 5000).

### Booking Service
- `GET /api/bookings/availability?hall_id={id}&start_date={date}&end_date={date}` - проверка доступности залов
- `POST /api/bookings` - создание бронирования
- `GET /api/bookings/{id}` - получение бронирования
- `GET /api/bookings` - список всех бронирований
- `DELETE /api/bookings/{id}` - отмена бронирования
- `POST /api/bookings/{id}/confirm` - подтверждение бронирования (после оплаты)

### Payment Service
- `POST /api/payments` - создание платежа
- `POST /api/payments/webhook/{gateway}` - webhook от платежного шлюза (yookassa/sberpay/tinkoff)
- `GET /api/payments/{id}` - статус платежа
- `POST /api/payments/{id}/refund` - возврат средств

### Notification Service
- `GET /api/notifications` - список уведомлений
- `POST /api/notifications/send` - ручная отправка уведомления (для тестов)

### Integration Service
- `GET /api/integrations/events` - просмотр событий

## Основные функции

- ✅ Онлайн-календарь бронирования с шагом 15 минут
- ✅ Интеграция с платежными системами (ЮKassa, СберPay, Тинькофф Касса)
- ✅ Поддержка тестовых (sandbox) и продакшн режимов платежных систем
- ✅ Режим MOCK для локальной разработки без реальных платежных шлюзов
- ✅ Предоплата и полная оплата
- ✅ Автоматическая обработка событий через Message Broker
- ✅ Отправка уведомлений клиентам через Telegram
- ✅ Автоматическое подтверждение бронирования после успешной оплаты
- ✅ Обработка webhook'ов от платежных шлюзов

## Поток работы

1. **Проверка доступности** → `GET /api/bookings/availability`
2. **Создание бронирования** → `POST /api/bookings` (статус: `pending_payment`)
3. **Создание платежа** → `POST /api/payments`
4. **Оплата** → редирект на платежный шлюз
5. **Webhook от платежного шлюза** → `POST /api/payments/webhook/{gateway}`
6. **Автоматическое подтверждение** → статус брони меняется на `confirmed`
7. **Уведомление клиенту** → отправка SMS через Telegram

## Тестирование платежных интеграций

Система поддерживает три режима работы:

- **MOCK** (по умолчанию) - заглушки для локального тестирования без реальных API
- **TEST** - использование тестовых API платежных систем (нужны тестовые ключи)
- **PRODUCTION** - продакшн режим (нужны реальные ключи)

Установка режима через переменную окружения:
```bash
set PAYMENT_ENV=mock  # Windows
export PAYMENT_ENV=mock  # Linux/Mac
```

Подробная документация по тестированию: [docs/PAYMENT_TESTING.md](backend/docs/PAYMENT_TESTING.md)

## Конфигурация

### Переменные окружения

- `BOOKING_SERVICE_URL` - URL Booking Service (по умолчанию: `http://localhost:5001`)
- `PAYMENT_SERVICE_URL` - URL Payment Service (по умолчанию: `http://localhost:5002`)
- `MESSAGE_BROKER_URL` - URL Message Broker (по умолчанию: `http://localhost:5050/broker`)
- `PAYMENT_ENV` - режим работы платежных шлюзов: `mock`, `test`, `production` (по умолчанию: `mock`)
- `PORT` - порт сервиса (у каждого сервиса свой дефолтный порт)

### Telegram уведомления

Notification Service поддерживает отправку уведомлений через Telegram Bot. Для настройки измените в `backend/notification_service/main.py`:
- `TELEGRAM_BOT_TOKEN` - токен бота
- `TELEGRAM_CHAT_ID` - ID чата для отправки

## Документация

- [backend/docs/API.md](backend/docs/API.md) - подробная документация API
- [backend/docs/ARCHITECTURE.md](backend/docs/ARCHITECTURE.md) - архитектура системы
- [backend/docs/PAYMENT_TESTING.md](backend/docs/PAYMENT_TESTING.md) - тестирование платежей
- [backend/docs/SEQUENCE_DIAGRAM.md](backend/docs/SEQUENCE_DIAGRAM.md) - диаграммы последовательности

## Решение проблем

### Проблемы с портами

Если порты заняты, измените их через переменные окружения или напрямую в коде сервисов.

### Ошибки при создании платежа

1. Проверьте, что все сервисы запущены
2. Убедитесь, что Booking Service доступен на порту 5001
3. Проверьте логи Payment Service на наличие ошибок

### Проблемы с уведомлениями

1. Проверьте настройки Telegram Bot в Notification Service
2. Убедитесь, что Message Broker работает и события доставляются
3. Проверьте логи Notification Service

## Технологии

- **Backend**: Python 3.11+, Flask, Pydantic
- **Frontend**: React, Axios
- **Архитектура**: Микросервисы, Event-Driven
- **Коммуникация**: REST API, HTTP-based Message Broker

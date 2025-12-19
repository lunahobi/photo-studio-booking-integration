# Тестирование платежных интеграций

## Режимы работы

Система поддерживает три режима работы платежных шлюзов:

1. **MOCK** (по умолчанию) - заглушки для локального тестирования
2. **TEST** - использование тестовых (sandbox) API платежных систем
3. **PRODUCTION** - продакшн режим с реальными платежами

Режим устанавливается через переменную окружения:
```bash
export PAYMENT_ENV=test  # или mock, production
```

## Локальное тестирование (MOCK режим)

В режиме MOCK используются заглушки, не требующие реальных API ключей.

### Создание тестового платежа

```bash
curl -X POST http://localhost:5000/api/payments \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "test-booking-123",
    "amount": 3000.00,
    "payment_type": "full_payment",
    "payment_method": "yookassa"
  }'
```

### Симуляция webhook

Используйте скрипт `payment_service/test_webhook.py`:

```bash
# Успешная оплата
python payment_service/test_webhook.py yookassa yookassa-123 success

# Неуспешная оплата
python payment_service/test_webhook.py yookassa yookassa-123 failed
```

## Тестирование с реальными платежными системами (TEST режим)

### ЮKassa (YooMoney)

1. **Регистрация в тестовом режиме:**
   - Зарегистрируйтесь на https://yookassa.ru/
   - Получите тестовые Shop ID и Secret Key в личном кабинете

2. **Настройка переменных окружения:**
   ```bash
   export PAYMENT_ENV=test
   export YOOKASSA_TEST_SHOP_ID=your_test_shop_id
   export YOOKASSA_TEST_SECRET_KEY=your_test_secret_key
   ```

3. **Тестовые карты:**
   - Успешная оплата: `5555555555554444` (любая дата, любой CVC)
   - Неуспешная оплата: `4111111111111111` (будет отклонена)

4. **Документация:** https://yookassa.ru/developers/api

### СберPay

1. **Регистрация:**
   - Зарегистрируйтесь на https://developer.sberbank.ru/
   - Получите тестовые учетные данные

2. **Настройка:**
   ```bash
   export PAYMENT_ENV=test
   export SBERPAY_TEST_USERNAME=your_username
   export SBERPAY_TEST_PASSWORD=your_password
   ```

3. **Документация:** https://developer.sberbank.ru/doc/v1/

### Тинькофф Касса

1. **Регистрация:**
   - Зарегистрируйтесь на https://www.tinkoff.ru/kassa/
   - Получите тестовые Terminal Key и Password

2. **Настройка:**
   ```bash
   export PAYMENT_ENV=test
   export TINKOFF_TEST_TERMINAL_KEY=your_terminal_key
   export TINKOFF_TEST_PASSWORD=your_password
   ```

3. **Документация:** https://www.tinkoff.ru/kassa/develop/api/

## Тестирование webhook локально

Для локального тестирования webhook используйте:

### 1. ngrok (рекомендуется)

```bash
# Установите ngrok: https://ngrok.com/

# Запустите туннель
ngrok http 5002

# Используйте полученный URL в настройках webhook в платежной системе
# Например: https://abc123.ngrok.io/api/payments/webhook/yookassa
```

### 2. Локальные тестовые скрипты

Используйте `payment_service/test_webhook.py` для симуляции webhook:

```bash
# После создания платежа получите external_payment_id из ответа
python payment_service/test_webhook.py yookassa <external_payment_id> success
```

## Сценарии тестирования

### 1. Успешная оплата

```bash
# 1. Создать бронирование
curl -X POST http://localhost:5000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "hall_id": "hall-001",
    "user_id": "user-123",
    "start_time": "2025-01-20T14:00:00",
    "end_time": "2025-01-20T16:00:00",
    "customer_name": "Иван Иванов",
    "customer_email": "ivan@example.com",
    "customer_phone": "+79161234567"
  }'

# 2. Создать платеж (получить payment_id и external_payment_id)
curl -X POST http://localhost:5000/api/payments \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<booking_id>",
    "amount": 3000.00,
    "payment_type": "full_payment",
    "payment_method": "yookassa"
  }'

# 3. Симулировать успешный webhook
python payment_service/test_webhook.py yookassa <external_payment_id> success

# 4. Проверить статус бронирования (должен быть "confirmed")
curl http://localhost:5000/api/bookings/<booking_id>
```

### 2. Неуспешная оплата

```bash
# 1-2. Создать бронирование и платеж (как выше)

# 3. Симулировать неуспешный webhook
python payment_service/test_webhook.py yookassa <external_payment_id> failed

# 4. Проверить статус бронирования (должен остаться "pending_payment")
curl http://localhost:5000/api/bookings/<booking_id>
```

### 3. Возврат средств

```bash
# После успешной оплаты
curl -X POST http://localhost:5000/api/payments/<payment_id>/refund \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1500.00,
    "reason": "Частичный возврат"
  }'
```

## Проверка событий

Все платежные события логируются через Message Broker. Проверьте события:

```bash
# Посмотреть события в Integration Service
curl http://localhost:5003/api/integrations/events?event_type=payment.succeeded
```

## Отладка

### Логи платежного сервиса

Проверяйте логи сервиса для отладки:

```bash
# Если запущен через start_services.bat, логи будут в отдельных окнах
# Или запустите сервис отдельно:
python payment_service/main.py
```

### Проверка подключения к платежным системам

В TEST режиме при ошибках подключения система автоматически переключается на заглушки. Проверьте:

1. Правильность API ключей
2. Доступность API платежной системы
3. Корректность формата запросов

### Валидация webhook

В PRODUCTION режиме обязательно проверяется подпись webhook. Убедитесь, что:

1. Подпись правильно вычисляется платежной системой
2. Метод `verify_webhook()` правильно валидирует подпись
3. Webhook URL доступен из интернета (через ngrok или прокси)

## Рекомендации

1. **Для разработки:** Используйте MOCK режим для быстрого тестирования логики
2. **Для интеграционного тестирования:** Используйте TEST режим с реальными API
3. **Для продакшн:** Обязательно используйте PRODUCTION режим с валидацией подписей

4. **Тестовые данные:**
   - Никогда не используйте реальные карты в TEST режиме
   - Используйте тестовые карты, предоставленные платежными системами
   - Регулярно очищайте тестовые данные

5. **Безопасность:**
   - Храните секретные ключи в переменных окружения
   - Не коммитьте ключи в репозиторий
   - Используйте .env файлы с .gitignore


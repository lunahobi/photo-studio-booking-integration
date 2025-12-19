# API Документация

## Базовый URL
- **API Gateway**: `http://localhost:5000`
- **Booking Service**: `http://localhost:5001`
- **Payment Service**: `http://localhost:5002`
- **Integration Service**: `http://localhost:5003`
- **Notification Service**: `http://localhost:5004`
- **Message Broker**: `http://localhost:5050`

## Booking Service

### 1. Проверка доступности залов

**GET** `/api/bookings/availability`

**Параметры запроса:**
- `hall_id` (optional) - ID зала
- `start_date` (required) - Начальная дата (ISO 8601)
- `end_date` (required) - Конечная дата (ISO 8601)

**Пример запроса:**
```bash
curl "http://localhost:5000/api/bookings/availability?hall_id=hall-001&start_date=2025-01-20T00:00:00Z&end_date=2025-01-21T00:00:00Z"
```

**Пример ответа:**
```json
{
  "slots": [
    {
      "hall_id": "hall-001",
      "start_time": "2025-01-20T09:00:00",
      "end_time": "2025-01-20T09:15:00",
      "available": true
    }
  ]
}
```

### 2. Создание бронирования

**POST** `/api/bookings`

**Тело запроса:**
```json
{
  "hall_id": "hall-001",
  "user_id": "user-123",
  "start_time": "2025-01-20T14:00:00",
  "end_time": "2025-01-20T16:00:00",
  "customer_name": "Иван Иванов",
  "customer_email": "ivan@example.com",
  "customer_phone": "+79161234567"
}
```

**Пример ответа:**
```json
{
  "booking_id": "550e8400-e29b-41d4-a716-446655440000",
  "hall_id": "hall-001",
  "user_id": "user-123",
  "start_time": "2025-01-20T14:00:00",
  "end_time": "2025-01-20T16:00:00",
  "status": "pending_payment",
  "total_amount": 3000.00,
  "customer_name": "Иван Иванов",
  "customer_email": "ivan@example.com",
  "customer_phone": "+79161234567",
  "created_at": "2025-01-19T10:00:00"
}
```

### 3. Получение бронирования

**GET** `/api/bookings/{booking_id}`

### 4. Отмена бронирования

**DELETE** `/api/bookings/{booking_id}`

## Payment Service

### 1. Создание платежа

**POST** `/api/payments`

**Тело запроса:**
```json
{
  "booking_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 3000.00,
  "payment_type": "full_payment",
  "payment_method": "yookassa"
}
```

**Пример ответа:**
```json
{
  "payment_id": "660e8400-e29b-41d4-a716-446655440001",
  "booking_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 3000.00,
  "status": "pending",
  "payment_method": "yookassa",
  "payment_type": "full_payment",
  "payment_url": "https://payment-gateway.ru/pay/660e8400...",
  "external_payment_id": "gateway-660e8400...",
  "created_at": "2025-01-19T10:05:00"
}
```

### 2. Webhook от платежного шлюза

**POST** `/api/payments/webhook/{gateway}`

где `gateway` может быть: `yookassa`, `sberpay`, `tinkoff`

**Тело запроса (пример):**
```json
{
  "payment_id": "gateway-660e8400...",
  "status": "succeeded",
  "amount": 3000.00,
  "gateway": "yookassa"
}
```

### 3. Получение статуса платежа

**GET** `/api/payments/{payment_id}`

### 4. Возврат средств

**POST** `/api/payments/{payment_id}/refund`

**Тело запроса (опционально):**
```json
{
  "amount": 1500.00,
  "reason": "Отмена бронирования"
}
```

## Integration Service

### 1. Просмотр событий

**GET** `/api/integrations/events`

**Параметры:**
- `event_type` (optional) - Тип события
- `source_service` (optional) - Сервис-источник
- `limit` (optional, default: 100) - Лимит записей

## Health Checks

Все сервисы имеют endpoint `/health` для проверки состояния.

**Пример:**
```bash
curl http://localhost:5000/health
```


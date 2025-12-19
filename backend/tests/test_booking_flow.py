"""
Интеграционные тесты (snake_case с _), включая проверку:
- после webhook бронь переходит в confirmed.

Почему это должно сработать:
- Payment Service при успешном webhook вызывает Booking Service:
  POST /api/bookings/<booking_id>/confirm. [file:14]
- Booking Service на этом endpoint выставляет booking.status = CONFIRMED. [file:17]
"""
import json
from datetime import datetime, timedelta

import requests


API_GATEWAY_URL = "http://localhost:5000"
PAYMENT_SERVICE_URL = "http://localhost:5002"


def _print_response(resp: requests.Response) -> None:
    print(f"URL: {resp.request.method} {resp.request.url}")
    print(f"HTTP: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(resp.text)


def test_availability_check():
    print("\n=== Тест проверки доступности ===")

    start_date = datetime.now() + timedelta(days=1)
    end_date = start_date + timedelta(days=1)

    params = {
        "hall_id": "hall-001",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    resp = requests.get(f"{API_GATEWAY_URL}/api/bookings/availability", params=params, timeout=10)
    _print_response(resp)

    assert resp.status_code == 200, "Запрос должен быть успешным"
    data = resp.json()
    assert "slots" in data, "Должен быть список slots"
    print(f"Найдено слотов: {len(data.get('slots', []))}")

    return data


def test_booking_creation():
    print("\n=== Тест создания бронирования ===")

    start_time = (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=2)

    booking_data = {
        "hall_id": "hall-001",
        "user_id": "user-123",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "customer_name": "Иван Иванов",
        "customer_email": "ivan@example.com",
        "customer_phone": "+79161234567",
    }

    resp = requests.post(f"{API_GATEWAY_URL}/api/bookings", json=booking_data, timeout=10)
    _print_response(resp)

    assert resp.status_code == 201, "Бронирование должно быть создано"
    booking = resp.json()
    assert booking.get("booking_id"), "Должен быть booking_id"
    assert booking.get("status") == "pending_payment", "Статус должен быть pending_payment"

    return booking


def test_get_booking(booking_id: str) -> dict:
    print("\n=== Тест получения бронирования ===")

    resp = requests.get(f"{API_GATEWAY_URL}/api/bookings/{booking_id}", timeout=10)
    _print_response(resp)

    assert resp.status_code == 200, "Бронирование должно успешно получаться"
    booking = resp.json()
    assert booking.get("booking_id") == booking_id, "booking_id должен совпадать"

    return booking


def test_payment_creation(booking: dict):
    print("\n=== Тест создания платежа ===")

    payment_data = {
        "booking_id": booking["booking_id"],
        "amount": float(booking["total_amount"]),
        "payment_type": "full_payment",
        "payment_method": "yookassa",
    }

    resp = requests.post(f"{API_GATEWAY_URL}/api/payments", json=payment_data, timeout=10)
    _print_response(resp)

    assert resp.status_code == 201, "Платеж должен быть создан"
    payment = resp.json()
    assert payment.get("payment_id"), "Должен быть payment_id"
    assert payment.get("payment_url"), "Должен быть payment_url"
    assert payment.get("external_payment_id"), "Должен быть external_payment_id"
    assert payment.get("status") == "pending", "Статус платежа должен быть pending"

    return payment


def test_webhook_processing(payment: dict, booking: dict):
    print("\n=== Тест обработки webhook ===")

    # Реальный формат YooKassa, который ожидает gateway.process_webhook(). [file:25]
    webhook_data = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": payment["external_payment_id"],
            "status": "succeeded",
            "amount": {"value": str(payment["amount"]), "currency": "RUB"},
            "metadata": {"booking_id": booking["booking_id"]},
        },
        "created_at": datetime.now().isoformat(),
    }

    resp = requests.post(
        f"{PAYMENT_SERVICE_URL}/api/payments/webhook/yookassa",
        json=webhook_data,
        timeout=10,
    )
    _print_response(resp)

    assert resp.status_code == 200, "Webhook должен обработаться успешно"

    # Проверяем, что платеж стал succeeded
    resp2 = requests.get(f"{API_GATEWAY_URL}/api/payments/{payment['payment_id']}", timeout=10)
    _print_response(resp2)

    assert resp2.status_code == 200, "Платеж должен успешно читаться"
    payment_status = resp2.json().get("status")
    assert payment_status == "succeeded", "Платеж должен стать succeeded"

    # Проверяем, что бронь стала confirmed (Payment Service дергает confirm endpoint). [file:14]
    updated_booking = test_get_booking(booking["booking_id"])
    assert updated_booking.get("status") == "confirmed", "Бронь должна стать confirmed"


if __name__ == "__main__":
    print("Запуск тестов интеграции...")
    print("Убедитесь, что все сервисы запущены!")

    try:
        test_availability_check()
        booking = test_booking_creation()
        payment = test_payment_creation(booking)
        test_webhook_processing(payment, booking)
        print("\n✓ Все тесты пройдены успешно!")
    except AssertionError as e:
        print(f"\n✗ Ошибка теста: {e}")
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")

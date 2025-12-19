"""
Скрипт для тестирования webhook от платежных шлюзов
Имитирует запросы от платежных систем
"""
import requests
import json
import sys
from datetime import datetime

PAYMENT_SERVICE_URL = "http://localhost:5002"


def test_yookassa_webhook_success(payment_id: str):
    """Тестовый webhook от ЮKassa (успешная оплата)"""
    webhook_data = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": payment_id,
            "status": "succeeded",
            "amount": {
                "value": "3000.00",
                "currency": "RUB"
            },
            "metadata": {
                "booking_id": "test-booking-123"
            },
            "created_at": datetime.now().isoformat()
        }
    }
    
    response = requests.post(
        f"{PAYMENT_SERVICE_URL}/api/payments/webhook/yookassa",
        json=webhook_data
    )
    
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response


def test_yookassa_webhook_failed(payment_id: str):
    """Тестовый webhook от ЮKassa (неуспешная оплата)"""
    webhook_data = {
        "type": "notification",
        "event": "payment.canceled",
        "object": {
            "id": payment_id,
            "status": "canceled",
            "amount": {
                "value": "3000.00",
                "currency": "RUB"
            },
            "metadata": {
                "booking_id": "test-booking-123"
            }
        }
    }
    
    response = requests.post(
        f"{PAYMENT_SERVICE_URL}/api/payments/webhook/yookassa",
        json=webhook_data
    )
    
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response


def test_sberpay_webhook(payment_id: str):
    """Тестовый webhook от СберPay"""
    webhook_data = {
        "orderId": payment_id,
        "status": 2,  # 2 = оплачен
        "amount": 300000  # в копейках
    }
    
    response = requests.post(
        f"{PAYMENT_SERVICE_URL}/api/payments/webhook/sberpay",
        json=webhook_data
    )
    
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response


def test_tinkoff_webhook(payment_id: str):
    """Тестовый webhook от Тинькофф"""
    webhook_data = {
        "TerminalKey": "test_terminal",
        "OrderId": "test-order-123",
        "PaymentId": payment_id,
        "Status": "CONFIRMED",
        "Amount": 300000  # в копейках
    }
    
    response = requests.post(
        f"{PAYMENT_SERVICE_URL}/api/payments/webhook/tinkoff",
        json=webhook_data
    )
    
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python test_webhook.py <gateway> <payment_id> [success|failed]")
        print("\nПримеры:")
        print("  python test_webhook.py yookassa yookassa-123 success")
        print("  python test_webhook.py yookassa yookassa-123 failed")
        print("  python test_webhook.py sberpay sberpay-123")
        print("  python test_webhook.py tinkoff tinkoff-123")
        sys.exit(1)
    
    gateway = sys.argv[1]
    payment_id = sys.argv[2]
    status = sys.argv[3] if len(sys.argv) > 3 else "success"
    
    print(f"\nТестирование webhook от {gateway} (payment_id: {payment_id}, status: {status})")
    print("-" * 60)
    
    if gateway == "yookassa":
        if status == "success":
            test_yookassa_webhook_success(payment_id)
        else:
            test_yookassa_webhook_failed(payment_id)
    elif gateway == "sberpay":
        test_sberpay_webhook(payment_id)
    elif gateway == "tinkoff":
        test_tinkoff_webhook(payment_id)
    else:
        print(f"Неизвестный шлюз: {gateway}")


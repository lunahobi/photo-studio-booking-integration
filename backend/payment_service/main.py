"""
Payment Service - Сервис обработки платежей

- Создаёт платежи для бронирований
- Интегрируется с платёжными шлюзами: YooKassa, СберPay, Тинькофф
- Обрабатывает webhook-и
- Публикует события payment.succeeded / payment.failed
"""

import sys
import os

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from decimal import Decimal
import uuid
import requests
import json

from schemas.payment import (
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
    PaymentMethod,
    PaymentType,
    PaymentWebhook,
    PaymentSucceededEvent,
    PaymentFailedEvent,
    RefundRequest,
    RefundResponse,
)

try:
    from gateways import get_gateway, Environment
except ImportError:
    from payment_service.gateways import get_gateway, Environment

app = Flask(__name__)
CORS(app)

# Конфигурация
BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "http://localhost:5001")
MESSAGE_BROKER_URL = os.getenv(
    "MESSAGE_BROKER_URL", "http://localhost:5050/broker/publish"
)
PORT = int(os.getenv("PORT", 5002))

# Режим работы платёжных шлюзов
PAYMENT_ENV = Environment(os.getenv("PAYMENT_ENV", "mock").lower())

# In-memory хранилище
payments_db: dict = {}


def serialize_for_json(obj):
    """Хелпер для сериализации datetime и Decimal в JSON"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def publish_event(event: dict) -> None:
    """Публикация события в Message Broker"""
    try:
        # Сериализуем event в JSON строку, а затем обратно в dict для requests
        event_json = json.dumps(event, default=serialize_for_json)
        event_dict = json.loads(event_json)
        resp = requests.post(MESSAGE_BROKER_URL, json=event_dict, timeout=5)
        resp.raise_for_status()
        print(f"✅ Event отправлен: {event.get('event_type')}")
    except Exception as e:
        print(f"❌ Ошибка публикации события: {e}")


def get_booking_amount(booking_id: str) -> Decimal:
    """
    Получить сумму брони из Booking Service.
    Пытается прочитать total_amount или price.
    """
    try:
        resp = requests.get(
            f"{BOOKING_SERVICE_URL}/api/bookings/{booking_id}", timeout=5
        )
        if resp.status_code != 200:
            print(
                f"⚠️ Не удалось получить бронирование {booking_id}: {resp.status_code}"
            )
            return Decimal("0")

        booking = resp.json()
        amount = booking.get("total_amount") or booking.get("price")
        if amount is None:
            print(f"⚠️ В бронировании {booking_id} нет total_amount/price")
            return Decimal("0")

        return Decimal(str(amount))
    except Exception as e:
        print(f"❌ Ошибка запроса к Booking Service: {e}")
        return Decimal("0")


def create_payment_gateway(
    payment_method: PaymentMethod,
    amount: Decimal,
    booking_id: str,
    return_url: str | None = None,
) -> dict:
    """Создание платежа в платёжном шлюзе"""
    gateway = get_gateway(payment_method.value, PAYMENT_ENV)
    return gateway.create_payment(amount, booking_id, return_url)


def process_webhook(
    gateway: PaymentMethod, webhook_data: dict, signature: str | None = None
):
    """Обработка webhook от платёжного шлюза"""
    gateway_instance = get_gateway(gateway.value, PAYMENT_ENV)

    # Проверка подписи в проде
    if PAYMENT_ENV == Environment.PRODUCTION and signature:
        if not gateway_instance.verify_webhook(webhook_data, signature):
            return {"error": "Невалидная подпись"}, 400

    processed_data = gateway_instance.process_webhook(webhook_data)
    external_payment_id = processed_data.get("payment_id")
    status = processed_data.get("status", "pending")

    status_mapping = {
        "succeeded": PaymentStatus.SUCCEEDED.value,
        "pending": PaymentStatus.PENDING.value,
        "canceled": PaymentStatus.FAILED.value,
        "failed": PaymentStatus.FAILED.value,
    }
    mapped_status = status_mapping.get(status.lower(), PaymentStatus.PENDING.value)

    # Находим платёж по external_payment_id
    payment = None
    for p in payments_db.values():
        if p.get("external_payment_id") == external_payment_id:
            payment = p
            break

    if not payment:
        return {"error": "Платёж не найден"}, 404

    old_status = payment["status"]
    payment["status"] = mapped_status
    payment["updated_at"] = datetime.now().isoformat()
    
    # Обновляем в БД (payment уже ссылается на объект из payments_db)
    payments_db[payment["payment_id"]] = payment

    # Успешная оплата
    if (
        mapped_status == PaymentStatus.SUCCEEDED.value
        and old_status != PaymentStatus.SUCCEEDED.value
    ):
        # Подтверждаем бронь
        try:
            requests.post(
                f"{BOOKING_SERVICE_URL}/api/bookings/{payment['booking_id']}/confirm",
                timeout=5,
            )
        except Exception as e:
            print(f"⚠️ Не удалось подтвердить бронь: {e}")

        # Конвертируем payment dict в PaymentResponse, обрабатывая строковые даты
        payment_for_response = payment.copy()
        if isinstance(payment_for_response.get("created_at"), str):
            payment_for_response["created_at"] = datetime.fromisoformat(payment_for_response["created_at"])
        if payment_for_response.get("updated_at") and isinstance(payment_for_response["updated_at"], str):
            payment_for_response["updated_at"] = datetime.fromisoformat(payment_for_response["updated_at"])
        if isinstance(payment_for_response.get("amount"), (str, float)):
            payment_for_response["amount"] = Decimal(str(payment_for_response["amount"]))
        
        event = PaymentSucceededEvent(
            payment=PaymentResponse(**payment_for_response),
            booking_id=payment["booking_id"],
            timestamp=datetime.now(),
        )
        publish_event(event.dict())

    # Неуспешная оплата
    elif mapped_status == PaymentStatus.FAILED.value:
        event = PaymentFailedEvent(
            payment_id=payment["payment_id"],
            booking_id=payment["booking_id"],
            timestamp=datetime.now(),
        )
        publish_event(event.dict())

    return {"status": "ok"}


@app.route("/api/payments", methods=["POST"])
def create_payment():
    """Создание нового платежа"""
    data = request.json or {}
    print(f"💳 Создание платежа: {data}")

    booking_id = data.get("booking_id")
    if not booking_id:
        return jsonify({"error": "booking_id обязателен"}), 400

    # 1. Берём amount из запроса, если он есть
    amount_raw = data.get("amount")

    # 2. Если нет — тянем из Booking Service
    if amount_raw is None:
        print("ℹ️ amount не указан, получаем из Booking Service…")
        amount = get_booking_amount(booking_id)
        if amount <= 0:
            return jsonify({"error": "Не удалось определить сумму платежа"}), 400
    else:
        amount = Decimal(str(amount_raw))

    try:
        payment_method = PaymentMethod(data.get("payment_method", "yookassa"))

        gateway_result = create_payment_gateway(
            payment_method,
            amount,
            booking_id,
            data.get("return_url"),
        )

        payment_id = str(uuid.uuid4())
        created_at = datetime.now()
        payment_data = {
            "payment_id": payment_id,
            "booking_id": booking_id,
            "amount": amount,
            "payment_method": payment_method.value,
            "status": PaymentStatus.PENDING.value,
            "created_at": created_at,
            "updated_at": None,
            "external_payment_id": gateway_result.get("external_payment_id"),
            "payment_url": gateway_result.get("payment_url"),
        }

        # Для хранения в БД конвертируем datetime в строку
        payments_db[payment_id] = {
            **payment_data,
            "created_at": created_at.isoformat(),
            "updated_at": None,
        }
        print(f"✅ Платёж создан: {payment_id}")

        resp = PaymentResponse(**payment_data)
        return jsonify(resp.dict()), 201

    except ValueError:
        return jsonify({"error": "Неверный payment_method"}), 400
    except Exception as e:
        print(f"❌ Ошибка платежа: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/payments/webhook/<gateway>", methods=["POST"])
def webhook(gateway: str):
    """Webhook от платёжного шлюза"""
    try:
        webhook_data = request.json or {}

        try:
            payment_method = PaymentMethod(gateway)
        except ValueError:
            return jsonify({"error": f"Неизвестный платёжный шлюз: {gateway}"}), 400

        signature = request.headers.get("X-Signature") or request.headers.get(
            "Signature"
        )

        result = process_webhook(payment_method, webhook_data, signature)

        if isinstance(result, tuple):
            body, code = result
            return jsonify(body), code

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/payments/<payment_id>", methods=["GET"])
def get_payment(payment_id: str):
    """Получение статуса платежа"""
    payment = payments_db.get(payment_id)
    if not payment:
        return jsonify({"error": "Платёж не найден"}), 404
    
    # Конвертируем строковые даты обратно в datetime для PaymentResponse
    payment_for_response = payment.copy()
    if isinstance(payment_for_response.get("created_at"), str):
        payment_for_response["created_at"] = datetime.fromisoformat(payment_for_response["created_at"])
    if payment_for_response.get("updated_at") and isinstance(payment_for_response["updated_at"], str):
        payment_for_response["updated_at"] = datetime.fromisoformat(payment_for_response["updated_at"])
    if isinstance(payment_for_response.get("amount"), (str, float)):
        payment_for_response["amount"] = Decimal(str(payment_for_response["amount"]))
    
    resp = PaymentResponse(**payment_for_response)
    return jsonify(resp.dict()), 200


@app.route("/api/payments/<payment_id>/refund", methods=["POST"])
def refund_payment(payment_id: str):
    """Возврат средств (прототип)"""
    try:
        payment = payments_db.get(payment_id)
        if not payment:
            return jsonify({"error": "Платёж не найден"}), 404

        if payment["status"] != PaymentStatus.SUCCEEDED.value:
            return jsonify(
                {"error": "Возврат возможен только для успешных платежей"}
            ), 400

        data = request.json or {}
        refund_req = RefundRequest(**data)
        refund_amount = (
            refund_req.amount
            if refund_req.amount
            else Decimal(str(payment["amount"]))
        )

        refund_id = str(uuid.uuid4())
        payment["status"] = PaymentStatus.REFUNDED.value
        payment["updated_at"] = datetime.now().isoformat()

        refund_resp = RefundResponse(
            refund_id=refund_id,
            payment_id=payment_id,
            amount=refund_amount,
            status="succeeded",
            timestamp=datetime.now(),
        )
        return jsonify(refund_resp.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "payment"}), 200


if __name__ == "__main__":
    print(f"🚀 Starting Payment Service on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

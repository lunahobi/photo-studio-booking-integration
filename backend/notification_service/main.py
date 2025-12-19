from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import uuid
import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
CORS(app)

MESSAGE_BROKER_URL = os.getenv("MESSAGE_BROKER_URL", "http://localhost:5050/broker")
BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "http://localhost:5001")
PORT = int(os.getenv("PORT", 5004))

TITLE = "📸 PhotoStudio Notifier"


# In-memory база уведомлений
notifications_db = []

def send_email(to: str, subject: str, body: str):
    """Отправка email (заглушка)"""
    notification = {
        "notification_id": str(uuid.uuid4()),
        "type": "email",
        "to": to,
        "subject": subject,
        "body": body,
        "status": "sent",
        "sent_at": datetime.now().isoformat()
    }
    notifications_db.append(notification)
    print(f"📧 Notification Email to {to}: {subject}")

def send_sms(to: str, message: str):
    """Отправка SMS через Telegram Bot"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        # Fallback на заглушку
        notification = {
            "notification_id": str(uuid.uuid4()),
            "type": "sms",
            "to": to,
            "message": message,
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }
        notifications_db.append(notification)
        print(f"[Telegram MOCK] SMS to={to}: {message}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text = f"📱 SMS для <b>{to}</b>:\n\n<i>{message}</i>"
    
    try:
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=5)
        resp.raise_for_status()
        
        # Успешно отправлено
        notification = {
            "notification_id": str(uuid.uuid4()),
            "type": "sms",
            "to": to,
            "message": message,
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }
        notifications_db.append(notification)
        print(f"✅ Telegram SMS sent to {to}: {message}")
        
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        # Записываем как failed
        notification = {
            "notification_id": str(uuid.uuid4()),
            "type": "sms",
            "to": to,
            "message": message,
            "status": "failed",
            "sent_at": datetime.now().isoformat()
        }
        notifications_db.append(notification)

def get_booking_from_service(booking_id: str) -> dict:
    """Получить бронирование из Booking Service"""
    try:
        resp = requests.get(
            f"{BOOKING_SERVICE_URL}/api/bookings/{booking_id}", timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️ Не удалось получить бронирование {booking_id}: {resp.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Ошибка запроса к Booking Service: {e}")
        return {}

def handle_booking_created(payload: dict):
    booking = payload.get("booking")
    if not booking:
        print("⚠️ booking не найден в payload события booking.created")
        return
    
    customer_phone = booking.get("customer_phone") if booking else None
    customer_email = booking.get("customer_email") if booking else None
    customer_name = booking.get("customer_name") if booking else None
    
    if customer_phone:
        send_sms(customer_phone, f"📸 Бронь создана, {customer_name}! Оплатите в течение 1 часа.")
    if customer_email:
        send_email(customer_email, "📸 Бронь создана!", f"Привет, {customer_name}!")

def handle_booking_confirmed(payload: dict):
    booking_id = payload.get("booking_id")
    if not booking_id:
        print("⚠️ booking_id не найден в payload события booking.confirmed")
        return
    
    # Пытаемся получить booking из payload, если нет - из сервиса
    booking = payload.get("booking") or get_booking_from_service(booking_id)
    customer_phone = booking.get("customer_phone") if booking else None
    
    if customer_phone:
        send_sms(customer_phone, f"✅ Бронь {booking_id} подтверждена!")

def handle_payment_succeeded(payload: dict):
    booking_id = payload.get("booking_id")
    if not booking_id:
        print("⚠️ booking_id не найден в payload события payment.succeeded")
        return
    
    # Получаем booking из Booking Service, так как в payload его нет
    booking = get_booking_from_service(booking_id)
    customer_phone = booking.get("customer_phone") if booking else None
    
    if customer_phone:
        send_sms(customer_phone, f"💳 Оплата {booking_id} прошла! До встречи! 📸")

@app.route("/broker/consume", methods=["POST"])
def consume_message():
    try:
        data = request.json or {}
        event_type = data.get("event_type")
        payload = data.get("payload") or {}
        print("[Notification] Получено событие:", event_type)

        if event_type == "booking.created":
            handle_booking_created(payload)
        elif event_type == "booking.confirmed":
            handle_booking_confirmed(payload)
        elif event_type == "payment.succeeded":
            handle_payment_succeeded(payload)
        # другие события по желанию

        # 🔑 Всегда возвращаем 200, даже если смс/телега не отправились
        return jsonify({"status": "processed"}), 200
    except Exception as e:
        # Логируем, но тоже отвечаем 200, чтобы брокер не ретраил бесконечно
        print("[Notification] Ошибка обработки события:", e)
        return jsonify({"status": "processed_with_error"}), 200


@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Получить список уведомлений"""
    limit = int(request.args.get("limit", 100))
    return jsonify({
        "notifications": notifications_db[-limit:],
        "total": len(notifications_db)
    }), 200

@app.route("/api/notifications/send", methods=["POST"])
def send_notification():
    """Ручная отправка уведомления (для тестов)"""
    try:
        data = request.json
        notification_type = data.get("type")  # email или sms
        to = data.get("to")

        if notification_type == "email":
            subject = data.get("subject")
            body = data.get("body")
            send_email(to, subject, body)
        elif notification_type == "sms":
            message = data.get("message")
            send_sms(to, message)
        else:
            return jsonify({"error": "Invalid type"}), 400

        return jsonify({"status": "sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "notification",
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
        "notifications_count": len(notifications_db)
    }), 200

@app.route("/test-telegram", methods=["GET"])
def test_telegram():
    """ПРЯМАЯ проверка Telegram"""
    print("🔥 ТЕСТ TELEGRAM ВЫЗВАН!")
    print(f"BOT_TOKEN: {'*' * 20 if TELEGRAM_BOT_TOKEN else 'EMPTY'}")
    print(f"CHAT_ID: {TELEGRAM_CHAT_ID}")
    
    send_sms("+79161234567", "🔥 ТЕСТ TELEGRAM РАБОТАЕТ! 🚀")
    return jsonify({"status": "test_sent"})


if __name__ == "__main__":
    print(f"Starting Notification Service on port {PORT}")
    print(f"Telegram configured: {bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

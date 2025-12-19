"""
Booking Service - Сервис управления бронированиями

- Создаёт и хранит брони
- Публикует события booking.created / booking.confirmed / booking.cancelled
- НЕ вызывает сам себя и не зацикливает события
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from typing import Dict, List, Optional
import requests

try:
    from schemas.booking import (
        BookingCreateRequest,
        BookingResponse,
        BookingStatus,
        AvailabilityRequest,
        AvailabilityResponse,
        Slot,
        BookingCreatedEvent,
        BookingConfirmedEvent,
        BookingCancelledEvent,
    )
except ImportError:
    # фоллбек для прототипа
    class BookingStatus:
        PENDING = "pending"
        PENDING_PAYMENT = "pending_payment"
        CONFIRMED = "confirmed"
        CANCELLED = "cancelled"

    class Slot:
        def __init__(
            self,
            hall_id: str,
            start_time: datetime,
            end_time: datetime,
            available: bool,
        ):
            self.hall_id = hall_id
            self.start_time = start_time
            self.end_time = end_time
            self.available = available

        def dict(self):
            return {
                "hall_id": self.hall_id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "available": self.available,
            }

app = Flask(__name__)
CORS(app)

BOOKING_DB_URL = os.getenv("BOOKING_DB_URL", "http://localhost:5432")
MESSAGE_BROKER_URL = os.getenv("MESSAGE_BROKER_URL", "http://localhost:5050/broker")
PORT = int(os.getenv("PORT", 5001))

bookings_db: Dict[str, dict] = {}

halls_db: Dict[str, dict] = {
    "hall-001": {
        "hall_id": "hall-001",
        "name": "Большой зал",
        "min_booking_duration": 60,
        "work_start_time": "09:00:00",
        "work_end_time": "22:00:00",
    },
    "hall-002": {
        "hall_id": "hall-002",
        "name": "Малый зал",
        "min_booking_duration": 30,
        "work_start_time": "09:00:00",
        "work_end_time": "22:00:00",
    },
}


def publish_event(event: dict) -> None:
    try:
        resp = requests.post(f"{MESSAGE_BROKER_URL}/publish", json=event, timeout=5)
        if resp.status_code == 200:
            print(f"✅ Event отправлен: {event.get('event_type')}")
        else:
            print(f"⚠️ Broker ответил: {resp.status_code}")
    except Exception as e:
        print(f"❌ Ошибка брокера: {e}")


def calculate_price(hall_id: str, start_time: datetime, end_time: datetime) -> Decimal:
    duration_hours = (end_time - start_time).total_seconds() / 3600
    base_price = Decimal("1500.00")
    return Decimal(str(duration_hours)) * base_price


def check_availability(
    hall_id: Optional[str], start_date: datetime, end_date: datetime
) -> List[Slot]:
    slots: List[Slot] = []
    current_time = start_date.replace(minute=0, second=0, microsecond=0)

    while current_time < end_date:
        slot_end = current_time + timedelta(minutes=15)

        hall_ids = [hall_id] if hall_id else list(halls_db.keys())

        for hid in hall_ids:
            is_available = True
            for booking in bookings_db.values():
                if booking["hall_id"] != hid:
                    continue
                # Проверяем статусы, которые означают занятость (занятое время)
                booking_status = booking.get("status", "")
                # Используем строковые значения для надежности
                occupied_statuses = [
                    "pending_payment",
                    "confirmed", 
                    "pending",  # Для обратной совместимости, если где-то сохраняется "pending"
                ]
                # Добавляем значения из enum, если они есть
                try:
                    occupied_statuses.append(BookingStatus.PENDING_PAYMENT.value if hasattr(BookingStatus.PENDING_PAYMENT, 'value') else str(BookingStatus.PENDING_PAYMENT))
                    occupied_statuses.append(BookingStatus.CONFIRMED.value if hasattr(BookingStatus.CONFIRMED, 'value') else str(BookingStatus.CONFIRMED))
                except (AttributeError, KeyError):
                    pass
                
                if booking_status in occupied_statuses:
                    try:
                        # Обрабатываем разные форматы дат
                        start_time_str = booking["start_time"]
                        end_time_str = booking["end_time"]
                        
                        # Если уже datetime объект, используем как есть
                        if isinstance(start_time_str, datetime):
                            b_start = start_time_str
                        else:
                            # Парсим строку, обрабатывая разные форматы
                            if isinstance(start_time_str, str):
                                start_time_str = start_time_str.replace("Z", "+00:00")
                            b_start = datetime.fromisoformat(start_time_str)
                        
                        if isinstance(end_time_str, datetime):
                            b_end = end_time_str
                        else:
                            if isinstance(end_time_str, str):
                                end_time_str = end_time_str.replace("Z", "+00:00")
                            b_end = datetime.fromisoformat(end_time_str)
                        
                        if not (slot_end <= b_start or current_time >= b_end):
                            is_available = False
                            break
                    except (ValueError, TypeError, AttributeError) as e:
                        # Если не удалось распарсить дату, логируем и пропускаем эту бронь
                        print(f"⚠️ Ошибка парсинга даты для брони {booking.get('booking_id')}: {e}")
                        continue
            slots.append(
                Slot(
                    hall_id=hid,
                    start_time=current_time,
                    end_time=slot_end,
                    available=is_available,
                )
            )

        current_time += timedelta(minutes=15)

    return slots


@app.route("/api/bookings/availability", methods=["GET"])
def get_availability():
    try:
        hall_id = request.args.get("hall_id")
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")

        if not start_date_str or not end_date_str:
            return jsonify({"error": "start_date и end_date обязательны"}), 400

        try:
            # Обрабатываем разные форматы дат
            start_date_str_clean = start_date_str.replace("Z", "+00:00") if "Z" in start_date_str else start_date_str
            end_date_str_clean = end_date_str.replace("Z", "+00:00") if "Z" in end_date_str else end_date_str
            start_date = datetime.fromisoformat(start_date_str_clean)
            end_date = datetime.fromisoformat(end_date_str_clean)
        except ValueError as e:
            return jsonify({"error": f"Неверный формат даты: {e}"}), 400

        slots = check_availability(hall_id, start_date, end_date)

        return jsonify({"slots": [s.dict() for s in slots]}), 200
    except Exception as e:
        print(f"❌ Ошибка в get_availability: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    """Создание новой брони с расчётом цены и публикацией booking.created"""
    try:
        data = request.json or {}
        print(f"📥 Создание брони: {data}")

        required_fields = [
            "hall_id",
            "user_id",
            "start_time",
            "end_time",
            "customer_name",
            "customer_email",
            "customer_phone",
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        start_time = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(data["end_time"].replace("Z", "+00:00"))

        price = calculate_price(data["hall_id"], start_time, end_time)

        booking_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        booking_data = {
            "booking_id": booking_id,
            "hall_id": data["hall_id"],
            "user_id": data["user_id"],
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "customer_name": data["customer_name"],
            "customer_email": data["customer_email"],
            "customer_phone": data["customer_phone"],
            "total_amount": float(price),
            "status": "pending_payment",
            "created_at": created_at,
            "updated_at": None,
        }

        bookings_db[booking_id] = booking_data
        print(f"✅ Бронь создана: {booking_id} за {price}₽")

        publish_event(
            {
                "event_type": "booking.created",
                "payload": {"booking": booking_data},
            }
        )

        return jsonify(booking_data), 201
    except Exception as e:
        print(f"❌ Ошибка создания брони: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/bookings/<booking_id>", methods=["GET"])
def get_booking(booking_id: str):
    booking = bookings_db.get(booking_id)
    if not booking:
        return jsonify({"error": "Бронирование не найдено"}), 404
    return jsonify(booking), 200


@app.route("/api/bookings/<booking_id>", methods=["DELETE"])
def cancel_booking(booking_id: str):
    booking = bookings_db.get(booking_id)
    if not booking:
        return jsonify({"error": "Бронирование не найдено"}), 404

    if booking["status"] == BookingStatus.CANCELLED:
        return jsonify({"error": "Бронирование уже отменено"}), 400

    booking["status"] = BookingStatus.CANCELLED
    booking["updated_at"] = datetime.now().isoformat()

    publish_event(
        {"event_type": "booking.cancelled", "payload": {"booking_id": booking_id}}
    )

    return jsonify(booking), 200


@app.route("/api/bookings/<booking_id>/confirm", methods=["POST"])
def confirm_booking(booking_id: str):
    """Подтверждение брони, публикация booking.confirmed только один раз"""
    booking = bookings_db.get(booking_id)
    if not booking:
        return jsonify({"error": "Бронирование не найдено"}), 404

    if booking["status"] == BookingStatus.CONFIRMED:
        # уже подтверждено, второе событие не шлём
        return jsonify(booking), 200

    booking["status"] = BookingStatus.CONFIRMED
    booking["updated_at"] = datetime.now().isoformat()

    publish_event(
        {
            "event_type": "booking.confirmed",
            "payload": {"booking_id": booking_id, "booking": booking},
        }
    )

    return jsonify(booking), 200


@app.route("/api/bookings", methods=["GET"])
def list_bookings():
    return jsonify({"bookings": list(bookings_db.values()), "total": len(bookings_db)})


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "healthy",
            "service": "booking",
            "bookings_count": len(bookings_db),
        }
    ), 200


if __name__ == "__main__":
    print(f"🚀 Starting Booking Service on port {PORT}")
    print(f"📡 Message Broker: {MESSAGE_BROKER_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

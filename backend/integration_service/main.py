"""
Integration Service - Сервис интеграции

- Принимает события от Message Broker
- Логирует их / имитирует отправку в CRM
- НЕ создаёт новых событий booking.* / payment.* и не дёргает Booking/Payment
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import uuid
from typing import Dict, Any

from schemas.integration import IntegrationMessage, EventLog, SyncRequest

app = Flask(__name__)
CORS(app)

MESSAGE_BROKER_URL = os.getenv("MESSAGE_BROKER_URL", "http://localhost:5000/broker")
PORT = int(os.getenv("PORT", 5003))

events_db: list[dict] = []
event_logs: Dict[str, dict] = {}


def process_event(event_type: str, payload: Dict[str, Any], source_service: str) -> dict:
    event_id = str(uuid.uuid4())
    event_log = {
        "event_id": event_id,
        "event_type": event_type,
        "source_service": source_service,
        "payload": payload,
        "status": "processed",
        "processed_at": datetime.now().isoformat(),
        "timestamp": datetime.now().isoformat(),
    }
    events_db.append(event_log)
    event_logs[event_id] = event_log

    if event_type == "booking.created":
        handle_booking_created(payload)
    elif event_type == "booking.confirmed":
        handle_booking_confirmed(payload)
    elif event_type == "booking.cancelled":
        handle_booking_cancelled(payload)
    elif event_type == "payment.succeeded":
        handle_payment_succeeded(payload)
    elif event_type == "payment.failed":
        handle_payment_failed(payload)

    return event_log


def handle_booking_created(payload: Dict[str, Any]) -> None:
    booking = payload.get("booking", {})
    print(f"[Integration] booking.created: {booking.get('booking_id')}")


def handle_booking_confirmed(payload: Dict[str, Any]) -> None:
    booking_id = payload.get("booking_id")
    print(f"[Integration] booking.confirmed: {booking_id}")


def handle_booking_cancelled(payload: Dict[str, Any]) -> None:
    booking_id = payload.get("booking_id")
    print(f"[Integration] booking.cancelled: {booking_id}")


def handle_payment_succeeded(payload: Dict[str, Any]) -> None:
    payment = payload.get("payment", {})
    print(f"[Integration] payment.succeeded: {payment.get('payment_id')}")


def handle_payment_failed(payload: Dict[str, Any]) -> None:
    payment_id = payload.get("payment_id")
    print(f"[Integration] payment.failed: {payment_id}")


@app.route("/api/integrations/events", methods=["GET"])
def get_events():
    try:
        event_type = request.args.get("event_type")
        source_service = request.args.get("source_service")
        limit = int(request.args.get("limit", 100))

        filtered = events_db
        if event_type:
            filtered = [e for e in filtered if e["event_type"] == event_type]
        if source_service:
            filtered = [e for e in filtered if e["source_service"] == source_service]

        filtered.sort(key=lambda x: x["timestamp"], reverse=True)
        return (
            jsonify({"events": filtered[:limit], "total": len(filtered)}),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/integrations/events/<event_id>", methods=["GET"])
def get_event(event_id: str):
    if event_id not in event_logs:
        return jsonify({"error": "Событие не найдено"}), 404
    return jsonify(event_logs[event_id]), 200


@app.route("/api/integrations/sync", methods=["POST"])
def sync():
    try:
        data = request.json or {}
        sync_req = SyncRequest(**data)
        result = {
            "sync_id": str(uuid.uuid4()),
            "entity_type": sync_req.entity_type,
            "entity_id": sync_req.entity_id,
            "action": sync_req.action,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/broker/consume", methods=["POST"])
def consume_message():
    """Endpoint, который дергает Message Broker"""
    try:
        data = request.json or {}
        message = IntegrationMessage(**data)
        event_log = process_event(
            message.event_type, message.payload, message.source_service
        )
        return jsonify({"status": "processed", "event_id": event_log["event_id"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "integration"}), 200


if __name__ == "__main__":
    print(f"🚀 Starting Integration Service on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

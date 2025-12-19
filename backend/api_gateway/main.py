"""
API Gateway for Booking & Payment Services

Запускается на порту 5000 и пробрасывает:
- /api/bookings*  → Booking Service
- /api/payments*  → Payment Service
"""

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Куда проксируем
BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "http://localhost:5001")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:5002")

# Порт GATEWAY
PORT = int(os.getenv("PORT", 5000))


def _proxy(method: str, base_url: str, path: str, **kwargs):
    """Общий прокси-хелпер"""
    url = f"{base_url}{path}"
    try:
        resp = requests.request(method, url, timeout=10, **kwargs)
        # Пытаемся парсить JSON, если не получается - возвращаем текст как ошибку
        try:
            data = resp.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            data = {"error": resp.text[:200]}  # Ограничиваем длину текста
        return (data, resp.status_code)
    except Exception as e:
        print(f"[Gateway] Error proxying {method} {url}: {e}")
        return {"error": str(e)}, 502


# ---------- BOOKING ----------

@app.route("/api/bookings", methods=["GET", "POST"])
def gw_bookings_collection():
    if request.method == "GET":
        data, code = _proxy("GET", BOOKING_SERVICE_URL, "/api/bookings")
        return jsonify(data), code
    else:
        data, code = _proxy("POST", BOOKING_SERVICE_URL, "/api/bookings", json=request.json)
        return jsonify(data), code


@app.route("/api/bookings/availability", methods=["GET"])
def gw_bookings_availability():
    data, code = _proxy("GET", BOOKING_SERVICE_URL, "/api/bookings/availability", params=request.args)
    if code >= 400:
        print(f"[Gateway] Availability error: code={code}, data={data}")
    return jsonify(data), code


@app.route("/api/bookings/<booking_id>", methods=["GET", "DELETE"])
def gw_booking_item(booking_id: str):
    if request.method == "GET":
        data, code = _proxy("GET", BOOKING_SERVICE_URL, f"/api/bookings/{booking_id}")
    else:
        data, code = _proxy("DELETE", BOOKING_SERVICE_URL, f"/api/bookings/{booking_id}")
    return jsonify(data), code


@app.route("/api/bookings/<booking_id>/confirm", methods=["POST"])
def gw_booking_confirm(booking_id: str):
    data, code = _proxy("POST", BOOKING_SERVICE_URL, f"/api/bookings/{booking_id}/confirm")
    return jsonify(data), code


# ---------- PAYMENTS ----------

@app.route("/api/payments", methods=["POST"])
def gw_create_payment():
    data, code = _proxy("POST", PAYMENT_SERVICE_URL, "/api/payments", json=request.json)
    return jsonify(data), code


@app.route("/api/payments/<payment_id>", methods=["GET"])
def gw_get_payment(payment_id: str):
    data, code = _proxy("GET", PAYMENT_SERVICE_URL, f"/api/payments/{payment_id}")
    return jsonify(data), code


@app.route("/api/payments/<payment_id>/refund", methods=["POST"])
def gw_refund_payment(payment_id: str):
    data, code = _proxy("POST", PAYMENT_SERVICE_URL, f"/api/payments/{payment_id}/refund", json=request.json)
    return jsonify(data), code


# ---------- Health ----------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "api-gateway"}), 200


if __name__ == "__main__":
    print(f"🚀 Starting API Gateway on port {PORT}")
    print(f"➡️  Booking Service: {BOOKING_SERVICE_URL}")
    print(f"💳 Payment Service: {PAYMENT_SERVICE_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

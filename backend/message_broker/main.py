"""
Message Broker - Простой брокер сообщений для событийно-ориентированной архитектуры
В реальной системе здесь будет RabbitMQ или Kafka
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from collections import defaultdict
import uuid
import threading
import requests
import time
import os

app = Flask(__name__)
CORS(app)

# Конфигурация
INTEGRATION_SERVICE_URL = os.getenv("INTEGRATION_SERVICE_URL", "http://localhost:5003")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:5004")
PORT = int(os.getenv("PORT", 5050))

# Хранилище сообщений (очереди для разных типов событий)
queues: dict = defaultdict(list)

# Подписчики на события
subscribers = {
    "booking.created": ["integration", "notification"],
    "booking.confirmed": ["integration", "notification"],
    "booking.cancelled": ["integration", "notification"],
    "payment.succeeded": ["integration", "notification"],
    "payment.failed": ["integration"],
}

# URL сервисов-подписчиков
subscriber_urls = {
    "integration": f"{INTEGRATION_SERVICE_URL}/broker/consume",
    "notification": f"{NOTIFICATION_SERVICE_URL}/broker/consume",
}


def deliver_message(subscriber: str, message: dict):
    """Доставка сообщения подписчику"""
    url = subscriber_urls.get(subscriber)
    if not url:
        print(f"[Broker] Подписчик {subscriber} не найден")
        return False
    
    try:
        response = requests.post(url, json=message, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[Broker] Ошибка доставки сообщения {subscriber}: {e}")
        return False


def process_queue():
    while True:
        for event_type, queue in list(queues.items()):
            if not queue:
                continue

            message = queue.pop(0)  # достали из очереди ОДИН РАЗ

            subscribers_list = subscribers.get(event_type, [])
            for subscriber in subscribers_list:
                success = deliver_message(subscriber, message)

                if not success:
                    # 🔑 Просто логируем ошибку и НЕ возвращаем в очередь
                    print(f"[Broker] Сообщение {message['message_id']} для {subscriber} провалено")
                else:
                    print(f"[Broker] Сообщение {message['message_id']} доставлено {subscriber}")

        time.sleep(0.5)



# Запускаем обработчик очереди в отдельном потоке
threading.Thread(target=process_queue, daemon=True).start()


@app.route("/broker/publish", methods=["POST"])
def publish():
    """Публикация сообщения в брокер"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        event_type = data.get("event_type")
        if not event_type:
            return jsonify({"error": "event_type is required"}), 400
        
        message = {
            "message_id": str(uuid.uuid4()),
            "event_type": event_type,
            "source_service": data.get("source_service", "unknown"),
            "payload": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Добавляем в очередь
        queues[event_type].append(message)
        
        print(f"[Broker] Сообщение опубликовано: {event_type} (очередь: {len(queues[event_type])})")
        
        return jsonify({
            "status": "published",
            "message_id": message["message_id"],
            "queue_size": len(queues[event_type])
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/broker/queues", methods=["GET"])
def get_queues():
    """Получение информации об очередях"""
    queue_info = {
        event_type: {
            "size": len(queue),
            "messages": queue[:10]  # Первые 10 сообщений для просмотра
        }
        for event_type, queue in queues.items()
    }
    
    return jsonify(queue_info), 200


@app.route("/broker/subscribe", methods=["POST"])
def subscribe():
    """Подписка на события (для динамической подписки)"""
    try:
        data = request.json
        event_type = data.get("event_type")
        subscriber = data.get("subscriber")
        callback_url = data.get("callback_url")
        
        if not all([event_type, subscriber, callback_url]):
            return jsonify({"error": "event_type, subscriber, callback_url are required"}), 400
        
        if event_type not in subscribers:
            subscribers[event_type] = []
        
        if subscriber not in subscribers[event_type]:
            subscribers[event_type].append(subscriber)
        
        subscriber_urls[subscriber] = callback_url
        
        return jsonify({"status": "subscribed"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    total_messages = sum(len(q) for q in queues.values())
    return jsonify({
        "status": "healthy",
        "service": "message_broker",
        "queues": {k: len(v) for k, v in queues.items()},
        "total_messages": total_messages
    }), 200


if __name__ == "__main__":
    print(f"Starting Message Broker on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)


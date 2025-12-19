"""
Конфигурация интеграционного брокера
"""

# Маршрутизация событий
EVENT_ROUTES = {
    "order.created": ["warehouse", "accounting"],
    "order.reserved": ["accounting"],
    "order.shipped": ["accounting"],
    "warehouse.low_stock": ["order"],
    "accounting.invoice.created": ["order"],
    "accounting.payment.received": ["order", "warehouse"],
}

# URL сервисов
SERVICE_URLS = {
    "order": "http://localhost:5001",
    "warehouse": "http://localhost:5002",
    "accounting": "http://localhost:5003",
    "broker": "http://localhost:5000",
}

# Таймауты для запросов (в секундах)
REQUEST_TIMEOUT = 5

# Максимальное количество попыток повтора
MAX_RETRIES = 3


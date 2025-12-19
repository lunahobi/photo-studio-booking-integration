#!/bin/bash
# Скрипт для запуска всех сервисов

echo "Запуск сервисов системы бронирования фотостудии..."

# Запуск в фоновом режиме
python message_broker/main.py &
sleep 2

python booking_service/main.py &
sleep 1

python payment_service/main.py &
sleep 1

python integration_service/main.py &
sleep 1

python notification_service/main.py &
sleep 1

python api_gateway/main.py &

echo "Все сервисы запущены!"
echo "API Gateway доступен на http://localhost:5000"
echo "Message Broker доступен на http://localhost:5050"



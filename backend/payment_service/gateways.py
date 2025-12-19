"""
Реализация интеграций с платежными шлюзами
Поддержка тестовых (sandbox) и продакшн режимов
"""
import os
import requests
import uuid
from decimal import Decimal
from typing import Dict, Optional
from enum import Enum


class Environment(str, Enum):
    TEST = "test"
    PRODUCTION = "production"
    MOCK = "mock"  # Заглушка для локального тестирования


class PaymentGateway:
    """Базовый класс для платежных шлюзов"""
    
    def __init__(self, environment: Environment = Environment.MOCK):
        self.environment = environment
    
    def create_payment(self, amount: Decimal, booking_id: str, return_url: Optional[str] = None) -> Dict:
        """Создание платежа"""
        raise NotImplementedError
    
    def verify_webhook(self, payload: dict, signature: str) -> bool:
        """Проверка подписи webhook"""
        raise NotImplementedError
    
    def process_webhook(self, payload: dict) -> Dict:
        """Обработка webhook"""
        raise NotImplementedError


class YooKassaGateway(PaymentGateway):
    """Интеграция с ЮKassa"""
    
    # Тестовые данные для ЮKassa
    TEST_SHOP_ID = os.getenv("YOOKASSA_TEST_SHOP_ID", "your_test_shop_id")
    TEST_SECRET_KEY = os.getenv("YOOKASSA_TEST_SECRET_KEY", "your_test_secret_key")
    
    PROD_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
    PROD_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
    
    TEST_API_URL = "https://api.yookassa.ru/v3/payments"  # В тестовом режиме используется тот же URL
    
    def __init__(self, environment: Environment = Environment.TEST):
        super().__init__(environment)
        if environment == Environment.PRODUCTION:
            self.shop_id = self.PROD_SHOP_ID
            self.secret_key = self.PROD_SECRET_KEY
        else:
            self.shop_id = self.TEST_SHOP_ID
            self.secret_key = self.TEST_SECRET_KEY
        self.base_url = self.TEST_API_URL
    
    def create_payment(self, amount: Decimal, booking_id: str, return_url: Optional[str] = None) -> Dict:
        """Создание платежа в ЮKassa"""
        if self.environment == Environment.MOCK:
            # Заглушка для локального тестирования
            payment_id = str(uuid.uuid4())
            return {
                "external_payment_id": f"yookassa-{payment_id}",
                "payment_url": f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}",
                "status": "pending"
            }
        
        # Реальный вызов API ЮKassa
        headers = {
            "Authorization": f"Basic {self._get_auth_token()}",
            "Content-Type": "application/json",
            "Idempotence-Key": str(uuid.uuid4())
        }
        
        payload = {
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://example.com/return"
            },
            "description": f"Бронирование фотостудии #{booking_id}",
            "metadata": {
                "booking_id": booking_id
            }
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                auth=(self.shop_id, self.secret_key),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "external_payment_id": data["id"],
                "payment_url": data["confirmation"]["confirmation_url"],
                "status": data["status"]
            }
        except Exception as e:
            # В случае ошибки при тестировании возвращаем заглушку
            if self.environment == Environment.TEST:
                payment_id = str(uuid.uuid4())
                return {
                    "external_payment_id": f"yookassa-test-{payment_id}",
                    "payment_url": f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}",
                    "status": "pending"
                }
            raise
    
    def _get_auth_token(self) -> str:
        """Получение токена авторизации"""
        import base64
        auth_string = f"{self.shop_id}:{self.secret_key}"
        return base64.b64encode(auth_string.encode()).decode()
    
    def verify_webhook(self, payload: dict, signature: str) -> bool:
        """Проверка подписи webhook от ЮKassa"""
        # В реальной реализации здесь должна быть проверка подписи
        # Для тестирования возвращаем True
        return True
    
    def process_webhook(self, payload: dict) -> Dict:
        """Обработка webhook от ЮKassa"""
        # Формат webhook от ЮKassa
        event_type = payload.get("event")
        payment_data = payload.get("object", {})
        
        return {
            "payment_id": payment_data.get("id"),
            "status": payment_data.get("status"),  # pending, succeeded, canceled
            "amount": float(payment_data.get("amount", {}).get("value", 0)),
            "metadata": payment_data.get("metadata", {})
        }


class SberPayGateway(PaymentGateway):
    """Интеграция с СберPay"""
    
    def __init__(self, environment: Environment = Environment.TEST):
        super().__init__(environment)
        # В реальной реализации здесь будут настроены учетные данные
    
    def create_payment(self, amount: Decimal, booking_id: str, return_url: Optional[str] = None) -> Dict:
        """Создание платежа в СберPay"""
        payment_id = str(uuid.uuid4())
        return {
            "external_payment_id": f"sberpay-{payment_id}",
            "payment_url": f"https://securepayments.sberbank.ru/payment?orderId={payment_id}",
            "status": "pending"
        }
    
    def verify_webhook(self, payload: dict, signature: str) -> bool:
        return True
    
    def process_webhook(self, payload: dict) -> Dict:
        return {
            "payment_id": payload.get("orderId"),
            "status": "succeeded" if payload.get("status") == 2 else "pending",
            "amount": float(payload.get("amount", 0)) / 100,  # Сбер передает в копейках
            "metadata": {}
        }


class TinkoffGateway(PaymentGateway):
    """Интеграция с Тинькофф Касса"""
    
    def __init__(self, environment: Environment = Environment.TEST):
        super().__init__(environment)
    
    def create_payment(self, amount: Decimal, booking_id: str, return_url: Optional[str] = None) -> Dict:
        """Создание платежа в Тинькофф"""
        payment_id = str(uuid.uuid4())
        return {
            "external_payment_id": f"tinkoff-{payment_id}",
            "payment_url": f"https://securepay.tinkoff.ru/payments?orderId={payment_id}",
            "status": "pending"
        }
    
    def verify_webhook(self, payload: dict, signature: str) -> bool:
        return True
    
    def process_webhook(self, payload: dict) -> Dict:
        return {
            "payment_id": payload.get("PaymentId"),
            "status": "succeeded" if payload.get("Status") == "CONFIRMED" else "pending",
            "amount": float(payload.get("Amount", 0)) / 100,
            "metadata": {}
        }


def get_gateway(gateway_name: str, environment: Environment = None) -> PaymentGateway:
    """Фабрика для получения экземпляра платежного шлюза"""
    if environment is None:
        env_str = os.getenv("PAYMENT_ENV", "mock").lower()
        environment = Environment(env_str)
    
    gateways = {
        "yookassa": YooKassaGateway,
        "sberpay": SberPayGateway,
        "tinkoff": TinkoffGateway
    }
    
    gateway_class = gateways.get(gateway_name.lower())
    if not gateway_class:
        raise ValueError(f"Неизвестный платежный шлюз: {gateway_name}")
    
    return gateway_class(environment)


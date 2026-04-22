import base64
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class PaymentResult:
    ok: bool
    url: Optional[str] = None
    message: str = ""


class PaymentService:
    def __init__(self) -> None:
        self.provider = (os.getenv("PAYMENT_PROVIDER") or "").strip().lower()

    def create_payment(self, order_id: int, amount_uah: int, description: str) -> PaymentResult:
        if not self.provider:
            return PaymentResult(ok=False, message="Провайдер оплати не налаштований.")

        if self.provider == "liqpay":
            return self._create_liqpay(order_id, amount_uah, description)
        if self.provider == "wayforpay":
            return self._create_wayforpay(order_id, amount_uah, description)

        return PaymentResult(ok=False, message=f"Непідтримуваний PAYMENT_PROVIDER: {self.provider}")

    def _create_liqpay(self, order_id: int, amount_uah: int, description: str) -> PaymentResult:
        public_key = os.getenv("LIQPAY_PUBLIC_KEY")
        private_key = os.getenv("LIQPAY_PRIVATE_KEY")
        server_url = os.getenv("LIQPAY_SERVER_URL", "https://example.com/payment/success")

        if not public_key or not private_key:
            return PaymentResult(ok=False, message="LIQPAY_PUBLIC_KEY / LIQPAY_PRIVATE_KEY не задані.")

        payload = {
            "version": "3",
            "public_key": public_key,
            "action": "pay",
            "amount": str(amount_uah),
            "currency": "UAH",
            "description": description,
            "order_id": f"order-{order_id}",
            "server_url": server_url,
        }

        data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
        signature = base64.b64encode(
            hashlib.sha1((private_key + data + private_key).encode("utf-8")).digest()
        ).decode("utf-8")
        url = f"https://www.liqpay.ua/api/3/checkout?data={data}&signature={signature}"
        return PaymentResult(ok=True, url=url)

    def _create_wayforpay(self, order_id: int, amount_uah: int, description: str) -> PaymentResult:
        merchant_account = os.getenv("WAYFORPAY_MERCHANT_ACCOUNT")
        merchant_secret = os.getenv("WAYFORPAY_SECRET_KEY")
        return_url = os.getenv("WAYFORPAY_RETURN_URL", "https://example.com/payment/success")

        if not merchant_account or not merchant_secret:
            return PaymentResult(
                ok=False,
                message="WAYFORPAY_MERCHANT_ACCOUNT / WAYFORPAY_SECRET_KEY не задані.",
            )

        payload = {
            "transactionType": "CREATE_INVOICE",
            "merchantAccount": merchant_account,
            "merchantDomainName": "localhost",
            "merchantTransactionSecureType": "AUTO",
            "merchantSignature": merchant_secret,
            "orderReference": f"order-{order_id}",
            "orderDate": 1710000000,
            "amount": amount_uah,
            "currency": "UAH",
            "orderTimeout": 49000,
            "productName": [description],
            "productPrice": [amount_uah],
            "productCount": [1],
            "serviceUrl": return_url,
        }

        try:
            response = requests.post("https://api.wayforpay.com/api", json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return PaymentResult(ok=False, message=f"WayForPay помилка: {exc}")

        invoice_url = data.get("invoiceUrl") or data.get("url")
        if not invoice_url:
            return PaymentResult(ok=False, message=f"WayForPay відповідь без URL: {data}")
        return PaymentResult(ok=True, url=invoice_url)


class CRMService:
    def __init__(self) -> None:
        self.webhook_url = os.getenv("CRM_WEBHOOK_URL", "").strip()

    def push_order(self, order_payload: Dict[str, Any]) -> str:
        if not self.webhook_url:
            return "CRM_WEBHOOK_URL не задано — пропускаю інтеграцію з CRM."

        try:
            response = requests.post(self.webhook_url, json=order_payload, timeout=15)
            response.raise_for_status()
            return "Дані замовлення відправлено в CRM."
        except Exception as exc:
            return f"Не вдалося відправити замовлення в CRM: {exc}"


class NovaPoshtaService:
    API_URL = "https://api.novaposhta.ua/v2.0/json/"

    def __init__(self) -> None:
        self.api_key = os.getenv("NOVA_POSHTA_API_KEY", "").strip()

    def find_warehouses(self, city_name: str, limit: int = 10) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "message": "NOVA_POSHTA_API_KEY не задано."}

        payload = {
            "apiKey": self.api_key,
            "modelName": "Address",
            "calledMethod": "getWarehouses",
            "methodProperties": {"CityName": city_name, "Limit": str(limit)},
        }

        try:
            response = requests.post(self.API_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"ok": False, "message": f"Помилка запиту до Nova Poshta API: {exc}"}

        if not data.get("success"):
            return {"ok": False, "message": f"Nova Poshta API error: {data.get('errors')}"}

        items = data.get("data", [])
        lines = [f"{item.get('Number')}: {item.get('Description')}" for item in items]
        return {"ok": True, "items": lines}

from functools import partial

from . import BASE_URL, ACCOUNT_ID, REQUEST as __REQUEST

URL = f"{BASE_URL}/payments/account/{ACCOUNT_ID}"
_REQUEST = partial(__REQUEST, url=URL)


def _GET(endpoint, params=None):
    return _REQUEST(method_name="GET", endpoint=endpoint, stuff=params)


def _POST(endpoint, data: dict):
    return _REQUEST(method_name="POST", endpoint=endpoint, stuff=data)


def get_default_payment_options():
    return _GET("payment_options?entity_type=invoice")


def add_payment_option_to_invoice(invoice_id, gateway_name="stripe"):
    return _POST(
        f"invoice/{invoice_id}/payment_options",
        data={
            "gateway_name": gateway_name,
            "entity_id": invoice_id,
            "entity_type": "invoice",
            "has_credit_card": True,
        },
    )

import typing

WHAT = "payments"


def get_default_payment_options(*, get_func: typing.Callable) -> dict:
    return get_func(what=WHAT, endpoint="payment_options?entity_type=invoice")


def add_payment_option_to_invoice(
    post_func: typing.Callable, invoice_id: int, gateway_name: str = "stripe"
) -> dict:
    return post_func(
        what=WHAT,
        endpoint=f"invoice/{invoice_id}/payment_options",
        data={
            "gateway_name": gateway_name,
            "entity_id": invoice_id,
            "entity_type": "invoice",
            "has_credit_card": True,
        },
    )

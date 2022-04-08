import datetime as dt
from decimal import Decimal
from functools import partial, lru_cache
from typing import NamedTuple

from avt_fresh import BASE_URL, ACCOUNT_ID, REQUEST as __REQUEST

URL = f"{BASE_URL}/accounting/account/{ACCOUNT_ID}/invoices/invoices"
_REQUEST = partial(__REQUEST, url=URL)


class ArgumentError(Exception):
    pass


class MoreThanOne(Exception):
    pass


class DoesntExist(Exception):
    pass


class InvalidField(Exception):
    pass


def _GET(endpoint, params=None):
    return _REQUEST(method_name="GET", endpoint=endpoint, stuff=params)


def _POST(endpoint, data: dict):
    return _REQUEST(method_name="POST", endpoint=endpoint, stuff=data)


def _PUT(endpoint, thing_id: int, data: dict):
    return _REQUEST(method_name="PUT", endpoint=f"{endpoint}/{thing_id}", stuff=data)


class FreshbooksLine(NamedTuple):
    invoice_id: int
    client_id: int
    description: str
    name: str
    rate: Decimal
    line_id: int
    quantity: Decimal
    amount: Decimal

    @classmethod
    def from_api(cls, **kwargs):
        return cls(
            invoice_id=kwargs["invoice_id"],
            client_id=kwargs["client_id"],
            rate=Decimal(kwargs["unit_cost"]["amount"]),
            description=kwargs["description"],
            name=kwargs["name"],
            quantity=Decimal(kwargs["qty"]),
            line_id=kwargs["lineid"],
            amount=Decimal(kwargs["amount"]["amount"]),
        )

    @property
    def dict_(self):
        return {
            "name": self.name,
            "description": self.description,
            "unit_cost": str(self.rate),
            "quantity": str(self.quantity),
        }


class FreshbooksInvoice(NamedTuple):
    lines: list[FreshbooksLine]
    notes: str
    client_id: int
    date: dt.date
    invoice_id: int
    number: str
    organization: str
    amount: Decimal
    status: str
    amount_outstanding: Decimal
    po_number: str
    line_id_line_dict: dict
    line_description_line_dict: dict
    line_description_line_id_dict: dict
    contacts: dict[str, dict]
    allowed_gateways: list

    @classmethod
    def from_api(cls, **kwargs):
        lines = [
            FreshbooksLine.from_api(
                invoice_id=kwargs["id"], client_id=kwargs["customerid"], **line
            )
            for line in kwargs["lines"]
        ]

        line_description_line_id_dict = {
            line.description: line.line_id for line in lines
        }
        line_id_line_dict = {line.line_id: line for line in lines}
        line_description_line_dict = {line.description: line for line in lines}

        return cls(
            lines=lines,
            line_description_line_id_dict=line_description_line_id_dict,
            line_description_line_dict=line_description_line_dict,
            line_id_line_dict=line_id_line_dict,
            notes=kwargs["notes"],
            client_id=kwargs["customerid"],
            date=dt.date.fromisoformat(kwargs["create_date"]),
            invoice_id=kwargs["id"],
            po_number=kwargs["po_number"],
            number=kwargs["invoice_number"],
            organization=kwargs["organization"],
            allowed_gateways=kwargs["allowed_gateways"],
            amount=Decimal(kwargs["amount"]["amount"]),
            amount_outstanding=Decimal(kwargs["outstanding"]["amount"]),
            contacts={contact["email"]: contact for contact in kwargs["contacts"]},
            status=kwargs["v3_status"],
        )


def get_all_draft_invoices():
    return get(status="draft")


def get_all_invoices_for_org_name(org_name: str) -> list[FreshbooksInvoice]:
    return get(org_name=org_name)


@lru_cache
def get_all_invoices_for_client_id(client_id: int) -> list[FreshbooksInvoice]:
    return get(client_id=client_id)


def get_draft_invoices_for_client_id(client_id: int) -> list[FreshbooksInvoice]:
    return get(client_id=client_id, status="draft")


def get_one(invoice_id) -> FreshbooksInvoice:
    invoices = get(invoice_id)
    if invoices:
        if len(invoices) > 1:
            raise MoreThanOne
        return invoices[0]
    raise DoesntExist


def get(
    invoice_id=None,
    client_id=None,
    org_name=None,
    status=None,
) -> list[FreshbooksInvoice]:

    if client_id is not None and org_name is not None:
        raise ArgumentError("Please provide either client_id or org_name")

    if invoice_id is not None and any(
        arg is not None for arg in (client_id, org_name, status)
    ):
        raise ArgumentError(
            "Please provide invoice_id and no other args, or else don't provide invoice_id"
        )

    full_url = ""
    sep = "?"

    if invoice_id is not None:
        full_url += f"/{invoice_id}"

    if client_id is not None:
        full_url += f"{sep}search[customerid]={client_id}"
        sep = "&"

    if status is not None:
        full_url += f"{sep}search[v3_status]={status}"
        sep = "&"

    response = _GET(full_url)
    try:
        num_results = response["total"]
    except KeyError:
        full_url += (
            f"{sep}include[]=lines&include[]=contacts&include[]=allowed_gateways"
        )
    else:
        if not num_results:
            return []
        full_url += (
            f"{sep}per_page={num_results}"
            f"&include[]=lines&include[]=contacts&include[]=allowed_gateways"
        )

    result = _GET(full_url)
    if "invoice" in result:
        return [FreshbooksInvoice.from_api(**result["invoice"])]
    invoices = result["invoices"]

    if org_name is not None:
        invoices = [i for i in invoices if org_name == i["current_organization"]]

    fb_invoices = []
    for invoice in invoices:
        try:
            fb_invoice = FreshbooksInvoice.from_api(**invoice)
        except ValueError as e:
            raise InvalidField(f"{invoice}") from e
        else:
            fb_invoices.append(fb_invoice)
    return fb_invoices


STATUS_STRING_INT_LOOKUP = {
    "draft": 1,
    "paid": 4,
}


def create(
    client_id: int,
    notes: str,
    lines: list[dict],
    status: str | int,
    contacts: list[dict] | None = None,
    po_number=None,
    create_date=None,
) -> dict:
    """
    `lines`
      The dictionaries must contain entries for `name`, `description`, `unit_cost`, and `qty`.
      The values must be JSON-serializable, so no `Decimal`s for example (all strings is fine).
    `contacts`
      Each of these dictionaries should simply be `{'contactid': <contactid>}`.
    `status`
      Status can be any of the `v3_status` values as a `str` or `1` or `4` (draft/paid).
    """
    create_date = create_date or str(dt.date.today())
    if isinstance(status, str):
        status = STATUS_STRING_INT_LOOKUP[status]
    data = dict(
        invoice=dict(
            customerid=client_id,  # type: ignore
            notes=notes,
            status=status,  # type: ignore
            lines=lines,  # type: ignore
            create_date=create_date,
            allowed_gateway_name="Stripe",
        )
    )
    if contacts:
        data["invoice"]["contacts"] = contacts
    if po_number:
        data["invoice"]["po_number"] = po_number

    return _POST("", data=data)


def update(invoice_id, **kwargs) -> dict:
    return _PUT("", invoice_id, dict(invoice=kwargs))


def delete(invoice_id) -> dict:
    return _PUT("", invoice_id, dict(invoice=dict(vis_state=1)))


def send(invoice_id) -> dict:
    return _PUT("", invoice_id, {"invoice": {"action_email": True}})

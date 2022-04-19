from avt_fresh import BASE_URL, REQUEST as _REQUEST
from avt_fresh.client import (
    FreshbooksClient,
    get_freshbooks_client_from_email,
    get_freshbooks_client_from_client_id,
    get_freshbooks_client_from_org_name,
    get_all_clients,
    delete as delete_client,
    create as create_client,
    delete_contact,
    add_contacts,
)
from avt_fresh.invoice import (
    FreshbooksInvoice,
    get_one as get_one_invoice,
    get_all_draft_invoices,
    get_all_invoices_for_client_id,
    get_all_invoices_for_org_name,
    get_draft_invoices_for_client_id,
    create as create_invoice,
    update as update_invoice,
    delete as delete_invoice,
    send as send_invoice,
)
from avt_fresh.payments import (
    get_default_payment_options,
    add_payment_option_to_invoice,
)


class ApiClient:
    def __init__(
        self, client_secret: str, client_id: str, redirect_uri: str, account_id: str
    ):
        self.client_secret = client_secret
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.account_id = account_id
        self.url_lookup = self._make_url_lookup(account_id)

    @staticmethod
    def _make_url_lookup(account_id: str) -> dict[str, str]:
        return {
            "client": f"{BASE_URL}/accounting/account/{account_id}/users/clients",
            "invoice": f"{BASE_URL}/accounting/account/{account_id}/invoices/invoices",
            "payments": f"{BASE_URL}/payments/account/{account_id}",
        }

    def _REQUEST(
        self, *, what: str, method_name: str, endpoint: str, stuff: dict | None = None
    ) -> dict:
        if method_name not in ("GET", "PUT", "POST"):
            raise Exception
        if what == "payments" and method_name == "PUT":
            raise Exception

        if what == "client" and method_name == "PUT":
            url = f"{BASE_URL}/accounting/account"
        else:
            url = self.url_lookup[what]
        return _REQUEST(
            url=url, method_name=method_name, endpoint=endpoint, stuff=stuff
        )

    def _GET(self, *, what: str, endpoint: str, params=None):
        return self._REQUEST(
            what=what, method_name="GET", endpoint=endpoint, stuff=params
        )

    def _POST(self, *, what: str, endpoint: str, data: dict):
        return self._REQUEST(
            what=what, method_name="POST", endpoint=endpoint, stuff=data
        )

    def _PUT(self, *, what: str, thing_id: int, data: dict):
        return self._REQUEST(
            what=what, method_name="PUT", endpoint=f"/{thing_id}", stuff=data
        )

    def get_one_invoice(self, invoice_id: int) -> FreshbooksInvoice:
        return get_one_invoice(get_func=self._GET, invoice_id=invoice_id)

    def get_all_draft_invoices(self) -> list[FreshbooksInvoice]:
        return get_all_draft_invoices(get_func=self._GET)

    def get_all_invoices_for_org_name(self, org_name: str) -> list[FreshbooksInvoice]:
        return get_all_invoices_for_org_name(get_func=self._GET, org_name=org_name)

    def get_all_invoices_for_client_id(self, client_id: int) -> list[FreshbooksInvoice]:
        return get_all_invoices_for_client_id(get_func=self._GET, client_id=client_id)

    def get_draft_invoices_for_client_id(
        self, client_id: int
    ) -> list[FreshbooksInvoice]:
        return get_draft_invoices_for_client_id(get_func=self._GET, client_id=client_id)

    def create_invoice(
        self,
        *,
        client_id: int,
        notes: str,
        lines: list[dict],
        status: str | int,
        contacts: list[dict] | None = None,
        po_number=None,
        create_date=None,
    ) -> dict:
        return create_invoice(
            post_func=self._POST,
            client_id=client_id,
            notes=notes,
            lines=lines,
            status=status,
            contacts=contacts,
            po_number=po_number,
            create_date=create_date,
        )

    def update_invoice(self, invoice_id: int, **kwargs) -> dict:
        return update_invoice(put_func=self._PUT, invoice_id=invoice_id, **kwargs)

    def delete_invoice(self, invoice_id: int) -> dict:
        return delete_invoice(put_func=self._PUT, invoice_id=invoice_id)

    def send_invoice(self, invoice_id: int) -> dict:
        return send_invoice(put_func=self._PUT, invoice_id=invoice_id)

    def get_freshbooks_client_from_email(self, email: str) -> FreshbooksClient:
        return get_freshbooks_client_from_email(get_func=self._GET, email=email)

    def get_freshbooks_client_from_client_id(self, client_id: int) -> FreshbooksClient:
        return get_freshbooks_client_from_client_id(
            get_func=self._GET, client_id=client_id
        )

    def get_freshbooks_client_from_org_name(self, org_name: str) -> FreshbooksClient:
        return get_freshbooks_client_from_org_name(
            get_func=self._GET, org_name=org_name
        )

    def get_all_clients(self) -> list[FreshbooksClient]:
        return get_all_clients(get_func=self._GET)

    def create_client(
        self, first_name: str, last_name: str, email: str, organization: str
    ) -> FreshbooksClient:
        return create_client(
            get_func=self._GET,
            post_func=self._POST,
            first_name=first_name,
            last_name=last_name,
            email=email,
            organization=organization,
        )

    def delete_client(self, client_id: int) -> None:
        delete_client(put_func=self._PUT, client_id=client_id)

    def add_contacts(self, client_id: int, contacts: list[dict]) -> None:
        add_contacts(
            get_func=self._GET,
            put_func=self._PUT,
            client_id=client_id,
            contacts=contacts,
        )

    def delete_contact(self, client_id: int, email: str) -> None:
        delete_contact(
            get_func=self._GET, put_func=self._PUT, client_id=client_id, email=email
        )

    def get_default_payment_options(self) -> dict:
        return get_default_payment_options(get_func=self._GET)

    def add_payment_option_to_invoice(self, invoice_id: int, gateway_name: str = "stripe") -> dict:
        return add_payment_option_to_invoice(
            post_func=self._POST, invoice_id=invoice_id, gateway_name=gateway_name
        )

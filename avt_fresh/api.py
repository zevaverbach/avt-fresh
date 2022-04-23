import datetime as dt
import json

import requests

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
from avt_fresh.token import TokenStoreOnDisk, NoToken, TokenStore, TokenTup


BASE_URL = "https://api.freshbooks.com"
URL = f"{BASE_URL}/auth/oauth/token"
HEADERS = {"Content-Type": "application/json"}


class ReRun(Exception):
    pass


class AvtFreshException(Exception):
    pass


class ApiClient:
    def __init__(
        self,
        client_secret: str,
        client_id: str,
        redirect_uri: str,
        account_id: str,
        token_store: TokenStore = TokenStoreOnDisk,
        connection_string: str | None = None,
    ):
        self.client_secret = client_secret
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.account_id = account_id
        self.url_lookup = self._make_url_lookup(account_id)
        self.token_store = token_store(connection_string)

    def make_headers(self):
        return {**HEADERS, "Authorization": f"Bearer {self._get_access_token()}"}

    def _get_access_token(self, authorization_code: str | None = None) -> str:
        if authorization_code:
            token = self._get_token_from_api_with_authorization_code(
                authorization_code=authorization_code
            )
            self.token_store.set(token)
            return token["access_token"]

        try:
            token = self.token_store.get()
        except NoToken:
            auth_code = _get_code_from_user()
            token_dict = self._get_token_from_api_with_authorization_code(auth_code)
            self.token_store.set(token_dict)
            token = self.token_store.get()
        if not _is_expired(token):
            return token.access_token

        try:
            token_dict = self._get_token_from_api_with_refresh_token(
                refresh_token=token.refresh_token
            )
        except AvtFreshException:
            auth_code = _get_code_from_user()
            token_dict = self._get_token_from_api_with_authorization_code(auth_code)
            self.token_store.set(token_dict)
            token = self.token_store.get()
            return token.access_token
        else:
            self.token_store.set(token_dict)
            return token_dict["access_token"]

    def _get_token_from_api_with_authorization_code(
        self, authorization_code: str
    ) -> dict:
        payload = {
            "client_secret": self.client_secret,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",  # get this by visiting
            "code": authorization_code,
        }
        res = requests.post(URL, data=json.dumps(payload), headers=HEADERS)
        return _return_or_raise(res, payload)

    def _get_token_from_api_with_refresh_token(self, refresh_token: str) -> dict:
        """
        :return:
            {
                'access_token': <access_token: str>,
                'token_type': 'Bearer',
                'expires_in': <seconds: int>,
                'refresh_token': <refresh_token: str>,
                'scope': 'admin:all:legacy',
                'created_at': <timestamp>,
                'direct_buy_tokens': {}
             }

        """
        payload = {
            "client_secret": self.client_secret,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        res = requests.post(URL, data=json.dumps(payload), headers=HEADERS)
        return _return_or_raise(res, payload)

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

        method, arg_name = REQUEST_LOOKUP[method_name]
        if endpoint == "" or endpoint.startswith("?"):
            rendered_url = f"{url}{endpoint}"
        else:
            rendered_url = f"{url}/{endpoint}"

        _, the_rest = rendered_url.split("https://")
        if "//" in the_rest:
            the_rest = the_rest.replace("//", "/")

        rendered_url = f"https://{the_rest}"

        print(rendered_url)

        raw_response = method(
            rendered_url,
            **{
                arg_name: stuff or {},
                "headers": self.make_headers(),
            },
        )
        if not raw_response.ok:
            raise Exception(
                f"response: {raw_response.reason}\nrendered_url: '{rendered_url}'\nstuff:{stuff}"
            )
        try:
            response = raw_response.json()["response"]
        except KeyError:
            return raw_response.json()
        if "result" in response:
            return response["result"]
        raise Exception(
            f"response: {response}\nrendered_url: '{rendered_url}'\nstuff:{stuff}"
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

    def add_payment_option_to_invoice(
        self, invoice_id: int, gateway_name: str = "stripe"
    ) -> dict:
        return add_payment_option_to_invoice(
            post_func=self._POST, invoice_id=invoice_id, gateway_name=gateway_name
        )


REQUEST_LOOKUP = {
    "GET": (requests.get, "params"),
    "PUT": (requests.put, "json"),
    "POST": (requests.post, "json"),
}


def _get_code_from_user() -> str:
    return input(
        "Please go here and get an auth code: "
        "https://my.freshbooks.com/#/developer, then enter it here: "
    )


def _is_expired(token: TokenTup) -> bool:
    return dt.datetime.now().timestamp() > token.created_at + token.expires_in


def _return_or_raise(response: requests.Response, payload: dict) -> dict:
    response_json = response.json()
    if "error" in response_json:
        raise AvtFreshException(f"{payload}:\n\n{response_json['error_description']}")
    del response_json["direct_buy_tokens"]
    return response_json

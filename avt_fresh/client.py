from functools import partial
from typing import NamedTuple

import requests

from avt_fresh import BASE_URL, REQUEST as __REQUEST, ACCOUNT_ID, make_headers


class FreshbooksContact(NamedTuple):
    contact_id: int
    first_name: str
    last_name: str
    email: str

    @classmethod
    def from_api(cls, contactid, fname, lname, email, **_):
        return cls(contact_id=contactid, first_name=fname, last_name=lname, email=email)

    @property
    def dict(self):
        return {
            "email": self.email,
            "fname": self.first_name,
            "lname": self.last_name,
        }


class FreshbooksClient(NamedTuple):
    client_id: int
    email: str
    organization: str
    first_name: str
    last_name: str
    contacts: dict[str, FreshbooksContact]
    contact_id_email_lookup: dict[int, str]
    email_contact_id_lookup: dict[str, int]

    @classmethod
    def from_api(cls, fname, lname, organization, userid, email, contacts, **_):
        contacts = {
            contact["email"]: FreshbooksContact.from_api(**contact)
            for contact in contacts
        }
        contact_id_email_lookup = {
            contact.contact_id: email for email, contact in contacts.items()
        }
        email_contact_id_lookup = {v: k for k, v in contact_id_email_lookup.items()}
        return cls(
            client_id=userid,
            email=email,
            first_name=fname,
            last_name=lname,
            organization=organization,
            contacts=contacts,
            contact_id_email_lookup=contact_id_email_lookup,
            email_contact_id_lookup=email_contact_id_lookup,
        )


URL = f"{BASE_URL}/accounting/account/{ACCOUNT_ID}/users/clients"
_REQUEST = partial(__REQUEST, url=URL)


def _GET(endpoint, params=None):
    return _REQUEST(method_name="GET", endpoint=endpoint, stuff=params)


def _POST(endpoint, data: dict):
    return _REQUEST(method_name="POST", endpoint=endpoint, stuff=data)


def _PUT(endpoint, thing_id: int, data: dict):
    return _REQUEST(method_name="PUT", endpoint=f"{endpoint}/{thing_id}", stuff=data)


class NoResult(Exception):
    pass


class MoreThanOne(Exception):
    pass


INCLUDE = "include[]=contacts"


def get_freshbooks_client_from_email(email: str) -> FreshbooksClient:
    try:
        return get_one(_GET(f"?search[email]={email}&{INCLUDE}"))
    except NoResult as e:
        raise NoResult(email) from e


def get_freshbooks_client_from_org_name(org_name: str) -> FreshbooksClient:
    return get_one(_GET(f"?search[organization_like]={org_name}&{INCLUDE}"))


def get_freshbooks_client_from_client_id(client_id: int) -> FreshbooksClient:
    return FreshbooksClient.from_api(**_GET(f"{client_id}?{INCLUDE}")["client"])


def get_one(response: dict) -> FreshbooksClient:
    clients = [FreshbooksClient.from_api(**client) for client in response["clients"]]
    if len(clients) > 1:
        print("warning, more than one result, returning the first")
    elif not clients:
        raise NoResult
    return clients[0]


def get_all_clients() -> list[FreshbooksClient]:
    return _GET(f"?{INCLUDE}")


def delete(client_id) -> None:
    requests.put(
        f"{BASE_URL}/accounting/account/{client_id}",
        json={"client": {"vis_state": 1}},
        headers=make_headers(),
    )


def create(
    first_name: str, last_name: str, email: str, organization: str
) -> FreshbooksClient:
    data = {
        "client": dict(
            fname=first_name, lname=last_name, email=email, organization=organization
        )
    }
    client_id = _POST(endpoint="", data=data)["client"]["id"]
    return get_freshbooks_client_from_client_id(client_id)


def add_contacts(client_id, contacts: list[dict]) -> None:
    """contacts: [dict(email, fname, lname)]"""
    to_update = []
    new_contacts_email_dict = {c["email"]: c for c in contacts}
    current_contacts = get_freshbooks_client_from_client_id(client_id).contacts

    if current_contacts:
        for email, current_contact in current_contacts.items():
            new_contact = new_contacts_email_dict.get(email)
            if new_contact is None:
                to_update.append(current_contact)
            else:
                to_update.append(new_contact)
                del new_contacts_email_dict[new_contact["email"]]

    to_update += list(new_contacts_email_dict.values())
    update_contacts(client_id, to_update)


def delete_contact(client_id, email) -> None:
    client = get_freshbooks_client_from_client_id(client_id)
    contact_to_delete = client.contacts.get(email)
    if contact_to_delete is not None:
        return update_contacts(
            client_id,
            [
                client.dict
                for client in client.contacts.values()
                if client != contact_to_delete
            ],
        )


def update_contacts(client_id, contacts: list[dict]) -> None:
    _update_freshbooks_client(client_id, {"contacts": contacts})


def _update_freshbooks_client(client_id, data: dict) -> None:
    requests.put(
        f"{BASE_URL}/accounting/account/{client_id}",
        json={"client": data},
        headers=make_headers(),
    )

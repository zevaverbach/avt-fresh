import typing

WHAT = "client"


class FreshbooksContact(typing.NamedTuple):
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


class FreshbooksClient(typing.NamedTuple):
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


class NoResult(Exception):
    pass


class MoreThanOne(Exception):
    pass


INCLUDE = "include[]=contacts"


def get_freshbooks_client_from_email(
    *, get_func: typing.Callable, email: str
) -> FreshbooksClient:
    try:
        return _get_one(
            get_func(what=WHAT, endpoint=f"?search[email]={email}&{INCLUDE}")
        )
    except NoResult as e:
        raise NoResult(email) from e


def get_freshbooks_client_from_org_name(
    *, get_func: typing.Callable, org_name: str
) -> FreshbooksClient:
    return _get_one(
        get_func(what=WHAT, endpoint=f"?search[organization_like]={org_name}&{INCLUDE}")
    )


def get_freshbooks_client_from_client_id(
    *, get_func: typing.Callable, client_id: int
) -> FreshbooksClient:
    return FreshbooksClient.from_api(
        **get_func(what=WHAT, endpoint=f"{client_id}?{INCLUDE}")["client"]
    )


def get_all_clients(*, get_func: typing.Callable) -> list[FreshbooksClient]:
    response = get_func(what=WHAT, endpoint="")
    num_results = response["total"]
    return [FreshbooksClient.from_api(**c) for c in get_func(what=WHAT, endpoint=f"?{INCLUDE}&per_page={num_results}")["clients"]]


def delete(*, put_func: typing.Callable, client_id: int) -> None:
    return put_func(what=WHAT, thing_id=client_id, data={"client": {"vis_state": 1}})


def create(
    *,
    get_func: typing.Callable,
    post_func: typing.Callable,
    first_name: str,
    last_name: str,
    email: str,
    organization: str,
) -> FreshbooksClient:
    data = {
        "client": dict(
            fname=first_name, lname=last_name, email=email, organization=organization
        )
    }
    client_id = post_func(what=WHAT, endpoint="", data=data)["client"]["id"]
    return get_freshbooks_client_from_client_id(get_func=get_func, client_id=client_id)


def add_contacts(
    *,
    get_func: typing.Callable,
    put_func: typing.Callable,
    client_id: int,
    contacts: list[dict],
) -> None:
    """contacts: [dict(email, fname, lname)]"""
    to_update = []
    new_contacts_email_dict = {c["email"]: c for c in contacts}
    current_contacts = get_freshbooks_client_from_client_id(
        get_func=get_func, client_id=client_id
    ).contacts

    if current_contacts:
        for email, current_contact in current_contacts.items():
            new_contact = new_contacts_email_dict.get(email)
            if new_contact is None:
                to_update.append(current_contact)
            else:
                to_update.append(new_contact)
                del new_contacts_email_dict[new_contact["email"]]

    to_update += list(new_contacts_email_dict.values())
    _update_contacts(put_func=put_func, client_id=client_id, contacts=to_update)


def delete_contact(
    *, get_func: typing.Callable, put_func: typing.Callable, client_id: int, email: str
) -> None:
    client = get_freshbooks_client_from_client_id(
        get_func=get_func, client_id=client_id
    )
    contact_to_delete = client.contacts.get(email)
    if contact_to_delete is not None:
        return _update_contacts(
            put_func=put_func,
            client_id=client_id,
            contacts=[
                client.dict
                for client in client.contacts.values()
                if client != contact_to_delete
            ],
        )


def _update_contacts(
    *, put_func: typing.Callable, client_id: int, contacts: list[dict]
) -> None:
    _update_freshbooks_client(
        put_func=put_func, client_id=client_id, data={"contacts": contacts}
    )


def _update_freshbooks_client(
    *, put_func: typing.Callable, client_id: int, data: dict
) -> None:
    put_func(what=WHAT, thing_id=client_id, data={"client": data})


def _get_one(response: dict) -> FreshbooksClient:
    clients = [FreshbooksClient.from_api(**client) for client in response["clients"]]
    if len(clients) > 1:
        print("warning, more than one result, returning the first")
    elif not clients:
        raise NoResult
    return clients[0]

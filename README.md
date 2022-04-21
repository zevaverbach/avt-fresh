# AVT Fresh!

This is a wrapper of [the roly-poly, not 100% ergonomic Freshbooks web API](https://www.freshbooks.com/api/start). It is far from comprehensive: It was created for the specific client- and invoice-related needs of [Averbach Transcription](https://avtranscription.com).

There are "band-aids" here to work around some of the API's shortcomings. For example, you don't have to deal with pagination at all. 🎉

# Installation

```
pip install avt-fresh
```

# Usage
Instantiate the avt_fresh `Client` like so, and you're off to the races:

```python
client = Client(client_secret="...", client_id="...", redirect_uri="https://...", account_id="...")

monster_invoices = client.get_all_invoices_for_org_name("Monsters Inc")
```

You can get and set the required arguments to `Client` [here](https://my.freshbooks.com/#/developer). Well, all of them except `FRESHBOOKS_ACCOUNT_ID`, which you can see (there's got to be another way??) by clicking on one of your invoices and grabbing the substring here: `https://my.freshbooks.com/#/invoice/<THIS THING>-1234567`. 

Don't tell anyone but `redirect_uri` can be pretty much anything! See `Initializing` below 👇.

# The Goodies

## Invoices
`client.get_one_invoice`, `client.create_invoice`, `client.send_invoice`, `client.update_invoice` and `client.delete_invoice` are the bread and butter methods here.

The `get...` functions return some handy `NamedTuple` instances with helpful attributes, notably `FreshbooksInvoice.lines` which have `Decimal` values where you would hope to find them. Also some lookups for addressing the `FreshbooksLine`s you may be interested in.

```python

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


class FreshbooksLine(NamedTuple):
    invoice_id: int
    client_id: int
    description: str
    name: str
    rate: Decimal
    line_id: int
    quantity: Decimal
    amount: Decimal
```

Then you have helpers `client.get_all_draft_invoices`, `client.get_all_invoices_for_org_name`, `client.get_all_invoices_for_client_id`, and `client.get_draft_invoices_for_client_id`.

### Create an Invoice
The signature of `client.create_invoice` is like so:

```python
def create(
    self,
    client_id: int,
    notes: str,
    lines: list[dict],
    status: str | int,
    contacts: list[dict] | None = None,
    po_number=None,
    create_date=None,
) -> dict:
```
#### `lines` 
The dictionaries must contain entries for `name`, `description`, `unit_cost`, and `qty`.
The values must be JSON-serializable, so no `Decimal`s for example (all strings is fine).

#### `contacts`
Each of these dictionaries should simply be `{'contactid': <contactid>}`.

#### `status`
Status can be any of the `v3_status` values as a `str` or `1` or `4` (draft/paid).


## Clients
`client.get_all_clients`, `client.create_client`, and `client.delete_client` are available here.

Once more the `get...` functions return `NamedTuple` instances with some helpful attributes, notably `FreshbooksClient.contacts` and a couple of related lookups (`.contact_id_email_lookup` and `.email_contact_id_lookup`).

```python
class FreshbooksClient(NamedTuple):
    client_id: int
    email: str
    organization: str
    first_name: str
    last_name: str
    contacts: dict[str, FreshbooksContact]
    contact_id_email_lookup: dict[int, str]
    email_contact_id_lookup: dict[str, int]


class FreshbooksContact(NamedTuple):
    contact_id: int
    first_name: str
    last_name: str
    email: str
```

Then, `client.update_contacts`, `client.delete_contact`, `client.add_contacts`, `client.get_freshbooks_client_from_client_id`, `client.get_freshbooks_client_from_email`, and `client.get_freshbooks_client_from_org_name`.

# Initializing
When you first call one of the functions which touches the Freshbooks API, you'll be prompted in the terminal like so:

```
Please go here and get an auth code: https://my.freshbooks.com/#/developer, then enter it here:
```

If you don't have an app there, create a really basic one. Name and description can be whatever, and you can skip the URL fields. 

Application Type: "Private App"
Scopes: `admin:all:legacy`

Add a redirect URI, it can actually be pretty much anything. Well, preferably a URL you control since it will receive OAuth tokens.

Finally, once you have an app on that developer page, click into it and click "go to authentication" page. Freshbooks will pop open a tab and go to your redirect URI, appending `?code=blahblahblah` to it. Grab the "blah blah blah" value and paste it into the prompt. 

You should only have to do this once in each environment you use this library in.

# Hardcoded Stuff / TODOs
Here are some quirks and TODOs. PRs are welcome!:

OAuth tokens are currently saved in the ever-so-insecure path of `~/freshbooks_oauth_token.json`. TODO: don't do this anymore. ¯\_(ツ)_/¯

Only Python 3.10 is supported at the moment.

When it comes to invoice statuses, we're only using `v3_status` strings, not the numbers. What's more, when you create an invoice we're only supporting two possible statuses: "draft" and "paid".

The `create`, `update`, and `delete` functions return dictionaries rather than an instance of the appropriate `NamedTuple`. This would be a great improvement!

The docs need improvement for sure: For now, have a peek at the source code, which includes pretty comprehensive type hints at the very least.

There are no tests! However, this code has been used in production in at least one company with some success.

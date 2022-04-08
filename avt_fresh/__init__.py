import datetime as dt
import json
import os

from dotenv import load_dotenv, find_dotenv
import requests

from avt_fresh.token import Token, NoToken

dotenv_path = find_dotenv()
if not dotenv_path:
    dotenv_path = os.getcwd() + "/.env"
load_dotenv(dotenv_path)

BASE_URL = "https://api.freshbooks.com"
URL = f"{BASE_URL}/auth/oauth/token"
HEADERS = {"Content-Type": "application/json"}

CLIENT_ID = os.getenv("FRESHBOOKS_API_CLIENT_ID")
SECRET = os.getenv("FRESHBOOKS_API_CLIENT_SECRET")
ACCOUNT_ID = os.getenv("FRESHBOOKS_ACCOUNT_ID")
REDIRECT_URI = os.getenv("FRESHBOOKS_REDIRECT_URI")


class ReRun(Exception):
    pass


class AvtFreshException(Exception):
    pass


def make_headers():
    return {**HEADERS, "Authorization": f"Bearer {_get_access_token()}"}


REQUEST_LOOKUP = {
    "GET": (requests.get, "params"),
    "PUT": (requests.put, "json"),
    "POST": (requests.post, "json"),
}


def REQUEST(url, method_name: str, endpoint: str, stuff=None):
    method, arg_name = REQUEST_LOOKUP[method_name]
    if endpoint == "" or endpoint.startswith("?"):
        rendered_url = f"{url}{endpoint}"
    else:
        rendered_url = f"{url}/{endpoint}"
    _, the_rest = rendered_url.split("https://")
    if "//" in the_rest:
        the_rest = the_rest.replace("//", "/")
    rendered_url = f"https://{the_rest}"
    print(f"{rendered_url=}")
    raw_response = method(
        rendered_url,
        **{
            arg_name: stuff or {},
            "headers": make_headers(),
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


def _get_access_token(authorization_code: str | None = None) -> str:
    if authorization_code:
        token = _get_token_from_api_with_authorization_code(
            authorization_code=authorization_code
        )
        _save_token(token)
        return token["access_token"]

    try:
        token = Token.get()
    except NoToken:
        auth_code = _get_code_from_user()
        token_dict = _get_token_from_api_with_authorization_code(auth_code)
        _save_token(token_dict)
        token = Token.get()
    if not _is_expired(token):
        return token.access_token

    old_token = token
    try:
        token = _get_token_from_api_with_refresh_token(
            refresh_token=old_token.refresh_token
        )
    except AvtFreshException:
        auth_code = _get_code_from_user()
        token_dict = _get_token_from_api_with_authorization_code(auth_code)
        old_token.delete()
        _save_token(token_dict)
        token = Token.get()
        return token.access_token
    else:
        old_token.delete()
        _save_token(token)
        return token["access_token"]


def _get_code_from_user() -> str:
    return input(
        "Please go here and get an auth code: "
        "https://my.freshbooks.com/#/developer, then enter it here: "
    )


def _save_token(token_response: dict):
    Token.make_from_dict(token_response)


def _is_expired(token: Token) -> bool:
    return dt.datetime.now().timestamp() > token.created_at + token.expires_in


def _get_token_from_api_with_authorization_code(authorization_code: str) -> dict:
    payload = {
        "client_secret": SECRET,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",  # get this by visiting
        "code": authorization_code,
    }
    res = requests.post(URL, data=json.dumps(payload), headers=HEADERS)
    return _return_or_raise(res, payload)


def _return_or_raise(response: requests.Response, payload: dict) -> dict:
    response_json = response.json()
    if "error" in response_json:
        raise AvtFreshException(f"{payload}:\n\n{response_json['error_description']}")
    del response_json["direct_buy_tokens"]
    return response_json


def _get_token_from_api_with_refresh_token(refresh_token: str) -> dict:
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
        "client_secret": SECRET,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    res = requests.post(URL, data=json.dumps(payload), headers=HEADERS)
    return _return_or_raise(res, payload)

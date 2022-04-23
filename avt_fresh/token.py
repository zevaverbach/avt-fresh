import abc
from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

import redis

TOKEN_PATH = Path("freshbooks_oauth_token.json")
TOKEN_KEY = "FRESHBOOKS_OAUTH_TOKEN"


class NoToken(Exception):
    pass


class OnlyOneToken(Exception):
    pass


@dataclass
class Token:
    id: int
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
    created_at: int

    def __init__(self, *args):
        ...

    @abc.abstractmethod
    def get(cls) -> "Token":
        ...

    @abc.abstractmethod
    def delete(self) -> None:
        ...

    @abc.abstractmethod
    def set(cls, token_dict: dict) -> None:
        ...


class TokenStoreOnDisk(Token):

    def __init__(self, *args):
        super().__init__(*args)

    @classmethod
    def get(cls) -> Token:
        if not TOKEN_PATH.exists():
            raise NoToken
        with TOKEN_PATH.open(encoding="utf-8") as fin:
            return json.load(fin)

    @classmethod
    def set(cls, token_dict: dict) -> None:
        if not TOKEN_PATH.exists():
            print(f"token JSON didn't exist, creating it at {TOKEN_PATH}:")
            TOKEN_PATH.touch()
        with TOKEN_PATH.open("w", encoding="utf-8") as fout:
            json.dump(token_dict, fout)


class TokenStoreOnRedis(Token):

    def __init__(self, *args):
        super().__init__(*args)
        redis_url = args[0]
        self.redis_client = redis.from_url(redis_url)

    def get(self):
        result = self.redis_client.get(TOKEN_KEY)
        if result is None:
            raise NoToken

    def set(self, token_dict: dict) -> None:
        self.redis_client.set(TOKEN_KEY, json.dumps(token_dict))

import abc
from dataclasses import dataclass
import json
from pathlib import Path
import typing

import redis

TOKEN_PATH = Path("freshbooks_oauth_token.json")
TOKEN_KEY = "FRESHBOOKS_OAUTH_TOKEN"


class NoToken(Exception):
    pass


class OnlyOneToken(Exception):
    pass


class TokenTup(typing.NamedTuple):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
    created_at: int


@dataclass
class TokenStore(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get(self) -> TokenTup:
        ...

    @abc.abstractmethod
    def set(self, token_dict: dict) -> None:
        ...


class TokenStoreOnDisk(TokenStore):
    @classmethod
    def get(cls) -> TokenTup:
        if not TOKEN_PATH.exists():
            raise NoToken
        with TOKEN_PATH.open(encoding="utf-8") as fin:
            return TokenTup(**json.load(fin))

    @classmethod
    def set(cls, token_dict: dict) -> None:
        if not TOKEN_PATH.exists():
            print(f"token JSON didn't exist, creating it at {TOKEN_PATH}:")
            TOKEN_PATH.touch()
        with TOKEN_PATH.open("w", encoding="utf-8") as fout:
            json.dump(token_dict, fout)


class TokenStoreOnRedis(TokenStore):
    def __init__(self, redis_url, redis_db_num: int = 0):
        self.redis_client = redis.from_url(redis_url, db=redis_db_num)

    def get(self) -> TokenTup:
        result = self.redis_client.get(TOKEN_KEY)
        if result is None:
            raise NoToken
        return TokenTup(**json.loads(result))

    def set(self, token_dict: dict) -> None:
        self.redis_client.set(TOKEN_KEY, json.dumps(token_dict))

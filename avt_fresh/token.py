import json
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4


class NoToken(Exception):
    pass


class OnlyOneToken(Exception):
    pass


class Token(NamedTuple):
    id: int
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
    created_at: int

    @classmethod
    def _get_all(cls) -> dict:
        TOKEN_PATH = Path("~/freshbooks_oauth_token.json").expanduser()
        if not TOKEN_PATH.exists():
            raise NoToken
        with TOKEN_PATH.open(encoding="utf-8") as fin:
            return json.load(fin)

    @classmethod
    def get(cls) -> "Token":
        tokens = cls._get_all()
        return cls(**list(tokens.values())[-1])

    def delete(self) -> None:
        tokens = self._get_all()
        if len(tokens) == 0:
            raise OnlyOneToken
        id_ = self.id
        del tokens[id_]
        self.make_from_dict(tokens)

    @classmethod
    def make_from_dict(cls, token_dict: dict) -> None:
        TOKEN_PATH = Path("~/freshbooks_oauth_token.json").expanduser()
        if not TOKEN_PATH.exists():
            print(f"token JSON didn't exist, creating it at {TOKEN_PATH}:")
            TOKEN_PATH.touch()
        id_ = str(uuid4())
        token_dict["id"] = id_
        token_dict = {id: token_dict}
        with TOKEN_PATH.open("w", encoding="utf-8") as fout:
            json.dump(token_dict, fout)

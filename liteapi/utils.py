from typing import Any
from starlette.types import ASGIApp, Scope


class AttrScope:
    def __init__(self, app: ASGIApp, scope: Scope):
        self.scope = scope
        self.ctx = Context(app)

    def __getitem__(self, key) -> Any:
        return self.scope[key]

    def __setitem__(self, key, value) -> None:
        self.scope[key] = value

    def get(self, key, default=None) -> Any:
        return self.scope.get(key, default)


class Context(dict):
    def __init__(self, app: ASGIApp):
        self.app = app

    def __getattr__(self, key) -> Any:
        return self[key]

    def __setattr__(self, key, value) -> None:
        self[key] = value

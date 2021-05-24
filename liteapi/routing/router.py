from typing import Callable, Optional, Sequence
from starlette.exceptions import HTTPException
from starlette.types import Receive, Send, ASGIApp
from liteapi.types import AttrScope
from liteapi.routing.utils import Match
from liteapi.routing.routes import (
    BaseRoute,
    PlainRoute,
    DynamicRoute,
    RouteMatch,
    Mount,
    route,
    mount,
    websocket
)


class Router:

    __slots__ = 'plain', 'dynamic', 'mounted',

    def __init__(self, routes: Sequence[BaseRoute] = None) -> None:
        self.plain = {}
        self.dynamic = []
        self.mounted = []

        if routes:
            self.__set_routes(routes)

    async def __call__(self,
                       scope: AttrScope,
                       receive: Receive,
                       send: Send) -> None:
        self._set_ctx_path(scope)
        match, endpoint = self.match(scope, receive, send)

        if match == Match.FULL:
            await endpoint(scope, receive, send)
        elif match == Match.NONE:
            raise HTTPException(status_code=404)
        elif match == Match.PARTIAL:
            raise HTTPException(status_code=405)

    def _set_ctx_path(self, scope: AttrScope) -> None:
        if 'path' not in scope.ctx:
            scope.ctx['path'] = scope['path']

    # ---

    def __set_routes(self, routes: Sequence[BaseRoute]) -> None:
        for route in routes:
            self.__set_route(route)

    def __set_route(self, route: BaseRoute) -> None:
        if isinstance(route, Mount):
            self.mounted.append(route)
        elif isinstance(route, PlainRoute):
            self.plain[route.path] = route
        elif isinstance(route, DynamicRoute):
            self.dynamic.append(route)

    def _mount(self,
               path: str,
               routes: Optional[Sequence[BaseRoute]],
               app: Optional[ASGIApp],
               name: Optional[str]) -> None:
        self.__set_route(mount(path, routes, app, name))

    def _route(self,
               path: str,
               endpoint: Callable,
               methods: Optional[Sequence[str]],
               name: Optional[str]) -> None:
        self.__set_route(route(path, endpoint, methods, name))

    def _websocket(self,
                   path: str,
                   endpoint: Callable,
                   name: Optional[str]) -> None:
        self.__set_route(websocket(path, endpoint, name))

    # ---

    def route(self,
              path: str,
              methods: Sequence[str] = None,
              name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> Callable:
            self._route(path, endpoint, methods, name)
            return endpoint
        return decorator

    # ---

    def match(self,
              scope: AttrScope,
              receive: Receive,
              send: Send) -> Optional[Callable]:
        match = self._match_plain(scope)
        if match is not None:
            return match

        match = self._match_mounted(scope)
        if match is not None:
            return match

        match = self._match_dynamic(scope)
        if match is not None:
            return match

        return Match.NONE, None

    def _match_plain(self, scope: AttrScope) -> Optional[RouteMatch]:
        route = self.plain.get(scope.ctx['path'])
        if route is not None:
            return route.match(scope)

    def _match_mounted(self, scope: AttrScope) -> Optional[RouteMatch]:
        for route in self.mounted:
            if scope.ctx['path'].startswith(route.path):
                return route.match(scope)

    def _match_dynamic(self, scope: AttrScope) -> Optional[RouteMatch]:
        for route in self.dynamic:
            match = route.match(scope)
            if match is not None:
                return match

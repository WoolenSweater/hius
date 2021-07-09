from itertools import chain
from collections import defaultdict
from typing import (
    DefaultDict,
    Awaitable,
    Callable,
    Optional,
    Sequence,
    Iterator,
    List
)
from starlette.datastructures import URLPath
from starlette.exceptions import HTTPException
from starlette.websockets import WebSocketDisconnect
from starlette.types import Scope, Receive, Send, ASGIApp
from hius.routing.utils import Match
from hius.routing.exceptions import NoMatchFound
from hius.routing.routes import (
    BaseRoute,
    PlainRoute,
    DynamicRoute,
    HTTPRoute,
    WebsocketRoute,
    RouteMatch,
    Mount,
    mount,
    route,
    websocket,
)

Lifespan = Callable[[Scope, Receive, Send], Awaitable]
Plain = DefaultDict[str, List[BaseRoute]]
Dynamic = List[BaseRoute]


class Router:

    __slots__ = '_mounted', '_http', '_webs', 'lifespan',

    def __init__(self,
                 routes: Sequence[BaseRoute] = None,
                 lifespan: Lifespan = None) -> None:
        self._mounted = []

        self._http = {'plain': defaultdict(list), 'dynamic': []}
        self._webs = {'plain': defaultdict(list), 'dynamic': []}

        async def default_lifespan(*args):
            pass  # pragma: no cover

        self.lifespan = lifespan or default_lifespan

        if routes is not None:
            for route in routes:
                self.__bind(route)

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        if scope['type'] == 'http':
            await self.match_http(scope, receive, send)
        elif scope['type'] == 'websocket':
            await self.match_websocket(scope, receive, send)
        elif scope['type'] == 'lifespan':
            await self.lifespan(scope, receive, send)

    def _set_scope_vars(self, scope: Scope) -> None:
        if 'router' not in scope:
            scope['router'] = self

        if 'ctx_path' not in scope:
            scope['ctx_path'] = scope['path']

    async def match_http(self,
                         scope: Scope,
                         receive: Receive,
                         send: Send) -> None:
        self._set_scope_vars(scope)
        match, endpoint = self._match(scope, **self._http)

        if match == Match.FULL:
            await endpoint(scope, receive, send)
        elif match == Match.NONE:
            raise HTTPException(status_code=404)
        elif match == Match.PARTIAL:
            raise HTTPException(status_code=405)

    async def match_websocket(self,
                              scope: Scope,
                              receive: Receive,
                              send: Send) -> None:
        self._set_scope_vars(scope)
        match, endpoint = self._match(scope, **self._webs)

        if match == Match.FULL:
            await endpoint(scope, receive, send)
        else:
            raise WebSocketDisconnect()

    # ---

    def _match(self,
               scope: Scope,
               plain: Plain,
               dynamic: Dynamic) -> RouteMatch:
        match = self._match_plain(scope, plain)
        if match is not None:
            return match

        match = self._match_dynamic(scope, dynamic)
        if match is not None:
            return match

        match = self._match_mounted(scope)
        if match is not None:
            return match

        return Match.NONE, None

    def _match_plain(self,
                     scope: Scope,
                     plain: Plain) -> Optional[RouteMatch]:
        routes = plain.get(scope['ctx_path'])
        if routes is not None:
            for route in routes:
                match, endpoint = route.match(scope)
                if endpoint is not None:
                    return match, endpoint
            return match, endpoint

    def _match_dynamic(self,
                       scope: Scope,
                       dynamic: Dynamic) -> Optional[RouteMatch]:
        for route in dynamic:
            match = route.match(scope)
            if match is not None:
                return match

    def _match_mounted(self,
                       scope: Scope) -> Optional[RouteMatch]:
        for route in self._mounted:
            is_equal = scope['ctx_path'] == route.path
            is_startswith = scope['ctx_path'].startswith(route.path + '/')
            if is_equal or is_startswith:
                return route.match(scope)

    # ---

    def __bind(self, route: BaseRoute) -> None:
        if isinstance(route, Mount):
            self._mounted.append(route)
            return

        if isinstance(route, HTTPRoute):
            routes = self._http
        elif isinstance(route, WebsocketRoute):
            routes = self._webs

        if isinstance(route, PlainRoute):
            routes['plain'][route.path].append(route)
        elif isinstance(route, DynamicRoute):
            routes['dynamic'].append(route)

    def _mount(self,
               path: str,
               routes: Optional[Sequence[BaseRoute]],
               app: Optional[ASGIApp],
               name: Optional[str]) -> None:
        self.__bind(mount(path, routes, app, name))

    def _route(self,
               path: str,
               endpoint: Callable,
               methods: Optional[Sequence[str]],
               name: Optional[str]) -> None:
        self.__bind(route(path, endpoint, methods, name))

    def _websocket(self,
                   path: str,
                   endpoint: Callable,
                   name: Optional[str]) -> None:
        self.__bind(websocket(path, endpoint, name))

    # ---

    def route(self,
              path: str,
              methods: Sequence[str] = None,
              name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> Callable:
            self._route(path, endpoint, methods, name)
            return endpoint
        return decorator

    def websocket(self,
                  path: str,
                  name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> Callable:
            self._websocket(path, endpoint, name)
            return endpoint
        return decorator

    # ---

    def __route_iter(self,
                     plain: Plain,
                     dynamic: Dynamic) -> Iterator[BaseRoute]:
        return chain(chain.from_iterable(plain.values()), dynamic)

    def url_path_for(self, name: str, **path_params: str) -> URLPath:
        http = self.__route_iter(**self._http)
        webs = self.__route_iter(**self._webs)
        for route in chain(http, webs, self._mounted):
            try:
                path = route.url_path_for(name)
                if path_params:
                    return path.format(**path_params)
                return path
            except NoMatchFound:
                pass
        raise NoMatchFound

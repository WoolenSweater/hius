from collections import namedtuple
from urllib.parse import unquote
from typing import (
    Callable,
    Optional,
    Sequence,
    Pattern,
    Tuple,
    Union,
    Dict,
    Set,
    Any
)
from enum import Enum
from .utils import parse_path
from .endpoint import Endpoint
from .exceptions import (
    MountError,
    RoutedPathError,
    RoutedMethodsError
)
from starlette.exceptions import HTTPException
from starlette.types import Scope, Receive, Send, ASGIApp


class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


Route = namedtuple('Route', 'path, endpoint, methods, name',
                   defaults=[None, None])
Mount = namedtuple('Mount', 'path, routes, app, name',
                   defaults=[None, None, None])

Routes = Sequence[Union[Route, Mount]]
RouteMatch = Tuple[Match, Optional[Callable]]


class ValidateMixin:
    def _check_path(self, path: str) -> str:
        self.__check_slash(path)
        return path.rstrip()

    def __check_slash(self, path: str) -> None:
        if not path.startswith('/'):
            raise RoutedPathError('routed path must start with "/"')

    def _check_methods(self, methods: Optional[Sequence[str]]) -> Set[str]:
        if methods is None:
            return {'GET', 'HEAD'}

        try:
            return {str(method).upper() for method in methods}
        except TypeError:
            raise RoutedMethodsError('methods must be an iterable')


class Router(ValidateMixin):

    __slots__ = 'plain', 'dynamic', 'mounted',

    def __init__(self, routes: Routes = None) -> None:
        self.plain = {}
        self.dynamic = []
        self.mounted = []

        if routes:
            self.__set_routes(routes)

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        self._set_ctx_path_and_method(scope)
        match, endpoint = self.match(scope, receive, send)

        if match == Match.FULL:
            await endpoint(scope, receive, send)
        elif match == Match.NONE:
            raise HTTPException(status_code=404)
        elif match == Match.PARTIAL:
            raise HTTPException(status_code=405)

    def _set_ctx_path_and_method(self, scope: Scope) -> None:
        scope['method'] = scope['method'].upper()
        if 'ctx_path' not in scope:
            scope['ctx_path'] = self._check_path(scope['path'])

    # ---

    def __set_routes(self, routes: Routes) -> None:
        for route in routes:
            if isinstance(route, Mount):
                self._mount(*route)
            else:
                self._bind(*route)

    def _mount(self,
               path: str,
               routes: Routes = None,
               app: ASGIApp = None,
               name: str = None) -> None:
        path = self._check_path(path)
        mount = _Mount(path, routes, app, name)
        self.mounted.append(mount)

    def _bind(self,
              path: str,
              endpoint: Callable,
              methods: Sequence[str] = None,
              name: str = None) -> None:
        path = self._check_path(path)
        methods = self._check_methods(methods)
        pattern, converters = parse_path(path)

        if converters:
            route = _DynamicRoute(endpoint, methods, name, pattern, converters)
            self.dynamic.append(route)
        else:
            route = _PlainRoute(endpoint, methods, name)
            self.plain[path] = route

    # ---

    def route(self,
              path: str,
              methods: Sequence[str] = None,
              name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> Callable:
            self._bind(path, endpoint, methods, name)
            return endpoint
        return decorator

    # ---

    def match(self,
              scope: Scope,
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

    def _match_plain(self, scope: Scope) -> Optional[RouteMatch]:
        route = self.plain.get(scope['ctx_path'])
        if route is not None:
            return route.match(scope['method'])

    def _match_mounted(self, scope: Scope) -> Optional[RouteMatch]:
        for mount in self.mounted:
            if scope['ctx_path'].startswith(mount.path):
                return mount.match(scope)

    def _match_dynamic(self, scope: Scope) -> Optional[RouteMatch]:
        for route in self.dynamic:
            match = route.match(scope['ctx_path'], scope['method'])
            if match is not None:
                return match


class _Mount:

    __slots__ = 'name', 'path', 'app'

    def __init__(self,
                 path: str,
                 routes: Routes = None,
                 app: ASGIApp = None,
                 name: str = None) -> None:
        self.name = name
        self.path = path
        self.app = self._set_app(app, routes)

    def _set_app(self, app: ASGIApp, routes: Routes) -> Union[ASGIApp, Router]:
        if all((app, routes)):
            raise MountError('either "app", or "routes" must be specified')
        return app or Router(routes)

    def _trim_path(self, scope: Scope) -> str:
        return scope['ctx_path'][len(self.path):]

    def match(self, scope: Scope) -> RouteMatch:
        scope['ctx_path'] = self._trim_path(scope)
        return Match.FULL, self.app


class _BaseRoute:

    __slots__ = 'methods', 'endpoint', 'name'

    def __init__(self,
                 endpoint: Callable,
                 methods: Sequence[str] = None,
                 name: str = None) -> None:
        self.methods = methods
        self.endpoint = Endpoint(endpoint)
        self.name = name or self.endpoint.name

    def _match_method(self, method: str) -> bool:
        return method in self.methods


class _PlainRoute(_BaseRoute):

    def __init__(self,
                 endpoint: Callable,
                 methods: Sequence[str] = None,
                 name: str = None) -> None:
        super().__init__(endpoint, methods, name)

    def match(self, method: str) -> RouteMatch:
        if self._match_method(method):
            return Match.FULL, self.endpoint
        return Match.PARTIAL, None


class _DynamicRoute(_BaseRoute):

    __slots__ = 'pattern', 'converters',

    def __init__(self,
                 endpoint: Callable,
                 methods: Sequence[str] = None,
                 name: str = None,
                 pattern: Pattern = None,
                 converters: Dict[str, Callable] = None) -> None:
        super().__init__(endpoint, methods, name)
        self.pattern = pattern
        self.converters = converters

    def match(self, path: str, method: str) -> Optional[RouteMatch]:
        match = self.pattern.match(path)
        if match is None:
            return

        if self._match_method(method):
            self.endpoint.set_path_params(self._convert_params(match))
            return Match.FULL, self.endpoint
        return Match.PARTIAL, None

    def _convert_params(self, matched_params) -> Dict[str, Any]:
        converted_params = {}
        for param_name, param_value in matched_params.groupdict().items():
            converter = self.converters.get(param_name)
            converted_params[param_name] = converter(unquote(param_value))
        return converted_params

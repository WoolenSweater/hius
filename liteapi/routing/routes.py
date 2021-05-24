from urllib.parse import unquote
from typing import (
    Match as PatternMatch,
    Callable,
    Optional,
    Sequence,
    Pattern,
    Union,
    Tuple,
    Type,
    Dict,
    Set,
    Any
)
from starlette.types import ASGIApp
from liteapi.types import AttrScope
from liteapi.routing.utils import Match
from liteapi.routing.parser import parse_path
from liteapi.routing.endpoint import (
    BaseEndpoint,
    get_http_endpoint,
    get_websocket_endpoint
)
from liteapi.routing.exceptions import (
    MountError,
    RoutedPathError,
    RoutedMethodsError
)
import liteapi.routing as router

RouteMatch = Tuple[Match, Optional[Callable]]


class BaseRoute:

    __slots__ = 'path', 'endpoint', 'name'

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 name: str = None) -> None:
        self.path = path
        self.endpoint = self._prepare_endpoint(endpoint)
        self.name = self._prepare_name(name)

    def match(self, scope: AttrScope) -> None:
        raise NotImplementedError

    def _prepare_endpoint(self, endpoint: Callable) -> Type[BaseEndpoint]:
        if isinstance(self, HTTPRoute):
            return get_http_endpoint(endpoint)
        elif isinstance(self, WebsocketRoute):
            return get_websocket_endpoint(endpoint)

    def _prepare_name(self, name: Optional[str]) -> str:
        return name or self.endpoint.name

    def _prepare_methods(self, methods: Optional[Sequence[str]]) -> Set[str]:
        if methods is None:
            return {'GET', 'HEAD'}

        try:
            return {str(method).upper() for method in methods}
        except TypeError:
            raise RoutedMethodsError('methods must be an iterable')


class DynamicBaseRoute(BaseRoute):

    __slots__ = 'pattern', 'converters',

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 pattern: Pattern,
                 converters: Dict[str, Callable],
                 name: Optional[str] = None) -> None:
        super().__init__(path, endpoint, name)
        self.pattern = pattern
        self.converters = converters

    def _convert_params(self, matched_params: PatternMatch) -> Dict[str, Any]:
        converted_params = {}
        for param_name, param_value in matched_params.groupdict().items():
            converter = self.converters.get(param_name)
            converted_params[param_name] = converter(unquote(param_value))
        return converted_params


class Mount:

    __slots__ = 'path', 'app', 'name',

    def __init__(self,
                 path: str,
                 routes: Sequence[BaseRoute] = None,
                 app: ASGIApp = None,
                 name: Optional[str] = None) -> None:
        self.path = path
        self.app = self._prepare_app(app, routes)
        self.name = self._prepare_name(name)

    def _prepare_app(self,
                     app: Optional[ASGIApp],
                     routes: Optional[Sequence[BaseRoute]]) -> Callable:
        if all((app, routes)):
            raise MountError('either "app", or "routes" must be specified')
        return app or router.Router(routes=routes)

    def _prepare_name(self, name: Optional[str]) -> str:
        return name or self.app.__class__.__name__

    def _trim_path(self, scope: AttrScope) -> str:
        return scope.ctx['path'][len(self.path):]

    def match(self, scope: AttrScope) -> RouteMatch:
        scope.ctx['path'] = self._trim_path(scope)
        return Match.FULL, self.app


# ---


class PlainHTTPRoute(BaseRoute):

    __slots__ = 'methods',

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 methods: Sequence[str] = None,
                 name: str = None) -> None:
        super().__init__(path, endpoint, name)
        self.methods = self._prepare_methods(methods)

    def match(self, scope: AttrScope) -> RouteMatch:
        if scope['method'] in self.methods:
            return Match.FULL, self.endpoint
        return Match.PARTIAL, None


class PlainWebsocketRoute(BaseRoute):

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 name: str = None) -> None:
        super().__init__(path, endpoint, name)

    def match(self, scope: AttrScope) -> RouteMatch:
        return Match.FULL, self.endpoint


# ---


class DynamicHTTPRoute(DynamicBaseRoute):

    __slots__ = 'methods',

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 pattern: Pattern,
                 converters: Dict[str, Callable],
                 methods: Sequence[str] = None,
                 name: str = None) -> None:
        super().__init__(path, endpoint, pattern, converters, name)
        self.methods = self._prepare_methods(methods)

    def match(self, scope: AttrScope) -> Optional[RouteMatch]:
        match = self.pattern.match(scope.ctx['path'])
        if match is None:
            return

        if scope['method'] in self.methods:
            scope['path_params'] = self._convert_params(match)
            return Match.FULL, self.endpoint
        return Match.PARTIAL, None


class DynamicWebsocketRoute(DynamicBaseRoute):

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 pattern: Pattern,
                 converters: Dict[str, Callable],
                 name: str = None) -> None:
        super().__init__(path, endpoint, pattern, converters, name)

    def match(self, scope: AttrScope) -> Optional[RouteMatch]:
        match = self.pattern.match(scope.ctx['path'])
        if match is None:
            return

        scope['path_params'] = self._convert_params(match)
        return Match.FULL, self.endpoint


# ---


PlainRoute = (PlainHTTPRoute, PlainWebsocketRoute)
DynamicRoute = (DynamicHTTPRoute, DynamicWebsocketRoute)

HTTPRoute = (PlainHTTPRoute, DynamicHTTPRoute)
WebsocketRoute = (PlainWebsocketRoute, DynamicWebsocketRoute)


# ---


def __prepare_path(path: str) -> str:
    if not path.startswith('/'):
        raise RoutedPathError('routed path must start with "/"')
    return path.rstrip()


def route(path: str,
          endpoint: Callable,
          methods: Sequence[str] = None,
          name: str = None) -> Union[HTTPRoute]:
    pattern, converters = parse_path(__prepare_path(path))

    if not converters:
        return PlainHTTPRoute(path, endpoint, methods, name)
    return DynamicHTTPRoute(path, endpoint, pattern, converters, methods, name)


def mount(path: str,
          routes: Sequence[BaseRoute] = None,
          app: ASGIApp = None,
          name: Optional[str] = None) -> Mount:
    return Mount(path, routes, app, name)


def websocket(path: str,
              endpoint: Callable,
              name: str = None) -> Union[WebsocketRoute]:
    pattern, converters = parse_path(__prepare_path(path))

    if not converters:
        return PlainWebsocketRoute(path, endpoint, name)
    return DynamicWebsocketRoute(path, endpoint, pattern, converters, name)

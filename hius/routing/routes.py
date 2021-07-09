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
from starlette.types import Scope, ASGIApp
from hius.routing.utils import Match, URLPath
from hius.routing.parser import parse_path
from hius.routing.endpoint import (
    BaseEndpoint,
    get_http_endpoint,
    get_websocket_endpoint
)
from hius.routing.exceptions import (
    MountError,
    RoutedPathError,
    RoutedMethodsError,
    NoMatchFound
)
import hius.routing as router

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

    def match(self, scope: Scope) -> None:
        raise NotImplementedError  # pragma: no cover

    def url_path_for(self, name: str) -> None:
        raise NotImplementedError  # pragma: no cover

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

        if isinstance(methods, (list, tuple, set)):
            return {str(method).upper() for method in methods}

        raise RoutedMethodsError('"methods" must be list, '
                                 'tuple, set or None type')


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

    def _trim_path(self, scope: Scope) -> str:
        return scope['ctx_path'][len(self.path):]

    def url_path_for(self, name: str) -> URLPath:
        if hasattr(self.app, 'url_path_for'):
            return self.app.url_path_for(name).appendleft(self.path)
        elif self.name == name:
            return URLPath(path=self.path)
        raise NoMatchFound

    def match(self, scope: Scope) -> RouteMatch:
        scope['ctx_path'] = self._trim_path(scope)
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

    def match(self, scope: Scope) -> RouteMatch:
        if scope['method'] in self.methods:
            return Match.FULL, self.endpoint
        return Match.PARTIAL, None

    def url_path_for(self, name: str) -> URLPath:
        if self.name == name:
            return URLPath(path=self.path, protocol='http')
        raise NoMatchFound


class PlainWebsocketRoute(BaseRoute):

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 name: str = None) -> None:
        super().__init__(path, endpoint, name)

    def match(self, scope: Scope) -> RouteMatch:
        return Match.FULL, self.endpoint

    def url_path_for(self, name: str) -> URLPath:
        if self.name == name:
            return URLPath(path=self.path, protocol='websocket')
        raise NoMatchFound


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

    def match(self, scope: Scope) -> Optional[RouteMatch]:
        match = self.pattern.match(scope['ctx_path'])
        if match is None:
            return

        if scope['method'] in self.methods:
            scope['path_params'] = self._convert_params(match)
            return Match.FULL, self.endpoint
        return Match.PARTIAL, None

    def url_path_for(self, name: str) -> URLPath:
        if self.name == name:
            return URLPath(path=self.path, protocol='http')
        raise NoMatchFound


class DynamicWebsocketRoute(DynamicBaseRoute):

    def __init__(self,
                 path: str,
                 endpoint: Callable,
                 pattern: Pattern,
                 converters: Dict[str, Callable],
                 name: str = None) -> None:
        super().__init__(path, endpoint, pattern, converters, name)

    def match(self, scope: Scope) -> Optional[RouteMatch]:
        match = self.pattern.match(scope['ctx_path'])
        if match is None:
            return

        scope['path_params'] = self._convert_params(match)
        return Match.FULL, self.endpoint

    def url_path_for(self, name: str) -> URLPath:
        if self.name == name:
            return URLPath(path=self.path, protocol='websocket')
        raise NoMatchFound


# ---


PlainRoute = (PlainHTTPRoute, PlainWebsocketRoute)
DynamicRoute = (DynamicHTTPRoute, DynamicWebsocketRoute)

HTTPRoute = (PlainHTTPRoute, DynamicHTTPRoute)
WebsocketRoute = (PlainWebsocketRoute, DynamicWebsocketRoute)


# ---


def __check_and_strip_path(path: str) -> str:
    if not path.startswith('/'):
        raise RoutedPathError('routed path must start with "/"')
    return path.rstrip()


def route(path: str,
          endpoint: Callable,
          methods: Sequence[str] = None,
          name: str = None) -> Union[HTTPRoute]:
    path, pattern, converters = parse_path(__check_and_strip_path(path))

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
    path, pattern, converters = parse_path(__check_and_strip_path(path))

    if not converters:
        return PlainWebsocketRoute(path, endpoint, name)
    return DynamicWebsocketRoute(path, endpoint, pattern, converters, name)

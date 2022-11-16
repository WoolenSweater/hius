from typing import (
    Callable,
    Sequence,
    Union,
    Dict,
    Type,
    Any
)
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.types import Scope, Receive, Send, ASGIApp
from hius.types import ExceptionHandlers, LifespanGenerator
from hius.handlers.exceptions import validation_error_handler
from hius.openapi.middleware import OpenAPIMiddleware
from hius.openapi.config import OpenAPIConfig
from hius.routing.exceptions import HTTPValidationError
from hius.routing.lifespan import Lifespan
from hius.routing.routes import BaseRoute
from hius.routing.utils import URLPath
from hius.routing import Router


class Hius:
    def __init__(self,
                 debug: bool = False,
                 routes: Sequence[BaseRoute] = None,
                 exception_handlers: ExceptionHandlers = None,
                 on_startup: Sequence[Callable] = None,
                 on_shutdown: Sequence[Callable] = None,
                 on_lifespan: Sequence[LifespanGenerator] = None,
                 openapi_config: OpenAPIConfig = None) -> None:
        self.debug = debug
        self.openapi_config = openapi_config or OpenAPIConfig()

        lifespan = Lifespan(on_startup, on_shutdown, on_lifespan)
        self.router = Router(routes=routes, lifespan=lifespan)

        self.exception_handlers = self.set_exc_handlers(exception_handlers)

        self.baggage = {}

        self.middleware = []
        self.middleware_stack = self.build_middleware_stack()

    def __setitem__(self, key: str, value: Any) -> None:
        self.baggage[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.baggage[key]

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        self._set_scope_self(scope)
        await self.middleware_stack(scope, receive, send)

    def _set_scope_self(self, scope: Scope) -> None:
        if 'app' not in scope:
            scope['app'] = self

    def set_exc_handlers(self,
                         handlers: ExceptionHandlers) -> ExceptionHandlers:
        return {
            HTTPValidationError: validation_error_handler,
            **(handlers or {})
        }

    def build_middleware_stack(self) -> ASGIApp:
        debug = self.debug
        err_handler = None
        exc_handlers = {}

        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                err_handler = value
            else:
                exc_handlers[key] = value

        middleware = (
            (ServerErrorMiddleware, {'handler': err_handler, 'debug': debug}),
            (OpenAPIMiddleware, {'router': self.router,
                                 'config': self.openapi_config}),
            *self.middleware,
            (ExceptionMiddleware, {'handlers': exc_handlers, 'debug': debug})
        )

        app = self.router
        for cls, options in reversed(middleware):
            app = cls(app=app, **options)
        return app

    def url_path_for(self, name: str, **path_params: str) -> URLPath:
        return self.router.url_path_for(name, **path_params)

    # ---

    def add_routes(self, routes: Sequence[BaseRoute]) -> None:
        self.router._bind_routes(routes)

    def add_route(self,
                  path: str,
                  endpoint: Callable,
                  methods: Sequence[str] = None,
                  name: str = None) -> None:
        self.router._route(path, endpoint, methods, name)

    def add_websocket(self,
                      path: str,
                      endpoint: Callable,
                      name: str = None) -> None:
        self.router._websocket(path, endpoint, name)

    def add_middleware(self,
                       mw_cls: ASGIApp,
                       **mw_options: Dict[str, Any]) -> None:
        self.middleware.append((mw_cls, mw_options))
        self.middleware_stack = self.build_middleware_stack()

    def add_exception_handler(self,
                              exc: Union[int, Type[Exception]],
                              handler: Callable) -> None:
        self.exception_handlers[exc] = handler
        self.middleware_stack = self.build_middleware_stack()

    def mount(self,
              path: str,
              app: ASGIApp,
              name: str = None) -> None:
        self.router._mount(path, None, app, name)

    # ---

    def route(self,
              path: str,
              methods: Sequence[str] = None,
              name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> None:
            self.router._route(path, endpoint, methods, name)
        return decorator

    def websocket(self,
                  path: str,
                  name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> None:
            self.router._websocket(path, endpoint, name)
        return decorator

    def exception_handler(self,
                          exc: Union[int, Type[Exception]]) -> Callable:
        def decorator(func: Callable) -> None:
            self.add_exception_handler(exc, func)
        return decorator

    # ---

    def on_startup(self) -> Callable:
        def decorator(func: Callable) -> None:
            self.router.lifespan.on_startup.append(func)
        return decorator

    def on_shutdown(self) -> Callable:
        def decorator(func: Callable) -> None:
            self.router.lifespan.on_shutdown.append(func)
        return decorator

    def on_lifespan(self) -> Callable:
        def decorator(func: Callable) -> None:
            self.router.lifespan.on_lifespan.append(func)
        return decorator

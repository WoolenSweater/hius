from typing import (
    NoReturn,
    Callable,
    Sequence,
    Union,
    Dict,
    Type,
    Any
)
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.exceptions import ExceptionMiddleware
from starlette.types import Scope, Receive, Send, ASGIApp
from hius.types import ExceptionHandlers, LifespanGenerator
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
                 on_lifespan: Sequence[LifespanGenerator] = None) -> None:
        self.debug = debug

        lifespan = Lifespan(on_startup, on_shutdown, on_lifespan)
        self.router = Router(routes=routes, lifespan=lifespan)

        self.exception_handlers = exception_handlers or {}

        self.baggage = {}

        self.middleware = []
        self.middleware_stack = self.build_middleware_stack()

    def __setitem__(self, key: str, value: Any) -> NoReturn:
        self.baggage[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.baggage[key]

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> NoReturn:
        self._set_scope_self(scope)
        await self.middleware_stack(scope, receive, send)

    def _set_scope_self(self, scope: Scope) -> NoReturn:
        if 'app' not in scope:
            scope['app'] = self

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

    def add_route(self,
                  path: str,
                  endpoint: Callable,
                  methods: Sequence[str] = None,
                  name: str = None) -> NoReturn:
        self.router._route(path, endpoint, methods, name)

    def add_websocket(self,
                      path: str,
                      endpoint: Callable,
                      name: str = None) -> NoReturn:
        self.router._websocket(path, endpoint, name)

    def add_middleware(self,
                       mw_cls: ASGIApp,
                       **mw_options: Dict[str, Any]) -> NoReturn:
        self.middleware.append((mw_cls, mw_options))

    def add_exception_handler(self,
                              exc: Union[int, Type[Exception]],
                              handler: Callable) -> NoReturn:
        self.exception_handlers[exc] = handler
        self.middleware_stack = self.build_middleware_stack()

    def mount(self,
              path: str,
              app: ASGIApp,
              name: str = None) -> NoReturn:
        self.router._mount(path, None, app, name)

    # ---

    def route(self,
              path: str,
              methods: Sequence[str] = None,
              name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> NoReturn:
            self.router._route(path, endpoint, methods, name)
        return decorator

    def websocket(self,
                  path: str,
                  name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> NoReturn:
            self.router._websocket(path, endpoint, name)
        return decorator

    def exception_handler(self,
                          exc: Union[int, Type[Exception]]) -> Callable:
        def decorator(func: Callable) -> NoReturn:
            self.add_exception_handler(exc, func)
        return decorator

    # ---

    def on_startup(self) -> Callable:
        def decorator(func: Callable) -> NoReturn:
            self.router.lifespan.on_startup.append(func)
        return decorator

    def on_shutdown(self) -> Callable:
        def decorator(func: Callable) -> NoReturn:
            self.router.lifespan.on_shutdown.append(func)
        return decorator

    def on_lifespan(self) -> Callable:
        def decorator(func: Callable) -> NoReturn:
            self.router.lifespan.on_lifespan.append(func)
        return decorator

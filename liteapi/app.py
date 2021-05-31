from typing import (
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
from liteapi.types import ExceptionHandlers
from liteapi.routing.routes import BaseRoute
from liteapi.routing.utils import URLPath
from liteapi.routing import Router


class LiteAPI:
    def __init__(self,
                 debug: bool = False,
                 router: Router = None,
                 routes: Sequence[BaseRoute] = None,
                 exception_handlers: ExceptionHandlers = None) -> None:
        self.debug = debug
        self.router = self.__prepare_router(router, routes)

        self.exception_handlers = exception_handlers or {}

        self.middleware = []
        self.middleware_stack = self.build_middleware_stack()

    def __prepare_router(self,
                         router: Router,
                         routes: Sequence[BaseRoute]) -> Router:
        if all((router, routes)):
            raise RuntimeError('either "router", or '
                               '"routes" must be specified')
        return router or Router(routes=routes)

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        self._set_scope_self(scope)
        await self.middleware_stack(scope, receive, send)

    def _set_scope_self(self, scope: Scope) -> None:
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

    def add_exception_handler(self,
                              exc: Union[int, Type[Exception]],
                              handler: Callable) -> None:
        self.exception_handlers[exc] = handler
        self.middleware_stack = self.build_middleware_stack()

    # ---

    def route(self,
              path: str,
              methods: Sequence[str] = None,
              name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> Callable:
            self.router._route(path, endpoint, methods, name)
            return endpoint
        return decorator

    def websocket(self,
                  path: str,
                  name: str = None) -> Callable:
        def decorator(endpoint: Callable) -> Callable:
            self.router._websocket(path, endpoint, name)
            return endpoint
        return decorator

    def mount(self,
              path: str,
              app: ASGIApp,
              name: str = None) -> None:
        self.router._mount(path, None, app, name)

    def exception_handler(self,
                          exc: Union[int, Type[Exception]]) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_exception_handler(exc, func)
            return func
        return decorator

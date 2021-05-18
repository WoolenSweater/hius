from typing import Sequence, Dict, Union, Type, Callable
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from .routing import Routes, Router

ExceptionHandlers = Dict[Union[int, Type[Exception]], Callable]


class LiteAPI:
    def __init__(self,
                 debug: bool = False,
                 router: Router = None,
                 routes: Sequence[Routes] = None,
                 exception_handlers: ExceptionHandlers = None) -> None:
        self.debug = debug
        self.router = router or Router(routes=routes)

        self.exception_handlers = exception_handlers or {}

        self.middleware = []
        self.middleware_stack = self.build_middleware_stack()

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        scope['app'] = self
        await self.middleware_stack(scope, receive, send)

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

    # ---

    def add_route(self,
                  path: str,
                  endpoint: Callable,
                  methods: Sequence[str] = None,
                  name: str = None) -> None:
        self.router._bind(path, endpoint, methods, name)

    def add_middleware(self, md_cls, **md_options) -> None:
        self.middleware.append((md_cls, md_options))

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
            self.router._bind(path, endpoint, methods, name)
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

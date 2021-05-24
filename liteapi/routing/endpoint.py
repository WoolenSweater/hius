from typing import Optional, Callable, Type
from inspect import isclass, isfunction, iscoroutinefunction
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocket
from starlette.requests import Request
from starlette.types import Receive, Send
from liteapi.types import AttrScope


class BaseEndpoint:

    __slots__ = 'handler', 'name'

    def __init__(self, endpoint: Callable, *, name: str) -> None:
        self.handler = endpoint
        self.name = name

    async def __call__(self,
                       scope: AttrScope,
                       receive: Receive,
                       send: Send) -> None:
        raise NotImplementedError

    async def _handle(self,
                      handler: Callable,
                      request: Request) -> Optional[Callable]:
        if iscoroutinefunction(handler):
            return await handler(request)
        else:
            return await run_in_threadpool(handler, request)


class HTTPBaseEndpoint(BaseEndpoint):

    async def __call__(self,
                       scope: AttrScope,
                       receive: Receive,
                       send: Send) -> None:
        request = Request(scope, receive)
        handler = self._get_handler(request)
        response = await self._handle(handler, request)
        await response(scope, receive, send)


class WebsocketBaseEndpoint(BaseEndpoint):

    async def __call__(self,
                       scope: AttrScope,
                       receive: Receive,
                       send: Send) -> None:
        websocket = WebSocket(scope, receive, send)
        handler = self._get_handler(websocket)
        await self._handle(handler, websocket)


# ---


class HTTPFuncEndpoint(HTTPBaseEndpoint):

    def __init__(self, endpoint):
        super().__init__(endpoint, name=endpoint.__name__)

    def _get_handler(self, request: Request) -> Callable:
        return self.handler


class HTTPClassEndpoint(HTTPBaseEndpoint):

    def __init__(self, endpoint):
        super().__init__(endpoint, name=endpoint.__class__.__name__)

    def _get_handler(self, request: Request) -> Callable:
        return getattr(self.handler, request.method.lower())


class WebsocketFuncEndpoint(WebsocketBaseEndpoint):

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint, name=endpoint.__name__)

    def _get_handler(self, request: Request) -> Callable:
        return self.handler


class WebsocketClassEndpoint(WebsocketBaseEndpoint):

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint, name=endpoint.__class__.__name__)

    def _get_handler(self, request: Request) -> Callable:
        return self.handler


# ---


def get_http_endpoint(func_or_class) -> Type[BaseEndpoint]:
    return _get_endpoint(func_or_class,
                         func_endpoini=HTTPFuncEndpoint,
                         class_endpoint=HTTPClassEndpoint)


def get_websocket_endpoint(func_or_class) -> Type[BaseEndpoint]:
    return _get_endpoint(func_or_class,
                         func_endpoini=WebsocketFuncEndpoint,
                         class_endpoint=WebsocketClassEndpoint)


def _get_endpoint(func_or_class,
                  *,
                  func_endpoini,
                  class_endpoint) -> Type[BaseEndpoint]:
    if isfunction(func_or_class):
        return func_endpoini(func_or_class)

    if isclass(func_or_class):
        return class_endpoint(func_or_class())

    return class_endpoint(func_or_class)

from typing import Callable, Dict, Any
from inspect import isclass, isfunction, iscoroutinefunction
from starlette.concurrency import run_in_threadpool
from starlette.types import Receive, Scope, Send
from starlette.requests import Request


class Endpoint:
    def __init__(self, endpoint):
        self._path_params = {}
        self._handler = self.__prepare(endpoint)
        self._is_class = self.__is_class(endpoint)

        self._name = self.__get_name()

    def __prepare(self, endpoint: Callable) -> Callable:
        return endpoint() if isclass(endpoint) else endpoint

    def __is_class(self, endpoint: Callable) -> bool:
        return False if isfunction(endpoint) else True

    def __get_name(self) -> str:
        if self._is_class:
            return self._handler.__class__.__name__
        else:
            return self._handler.__name__

    @property
    def name(self):
        return self._name

    def set_path_params(self, path_params: Dict[str, Any]) -> None:
        self._path_params = path_params

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        scope['path_params'] = self._path_params
        request = Request(scope, receive)
        handler = self._get_handler(request)
        response = await self._handle(handler, request)
        await response(scope, receive, send)

    def _get_handler(self, request: Request) -> Callable:
        if self._is_class:
            return getattr(self._handler, request.method.lower())
        return self._handler

    async def _handle(self, handler: Callable, request: Request) -> None:
        if iscoroutinefunction(handler):
            return await handler(request)
        else:
            return await run_in_threadpool(handler, request)

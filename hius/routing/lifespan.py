from inspect import iscoroutinefunction, isasyncgenfunction
from traceback import format_exc
from typing import (
    Callable,
    Optional,
    Sequence,
    Dict,
    Any
)
from starlette.concurrency import run_in_threadpool
from starlette.types import Scope, Receive, Send, ASGIApp
from hius.types import LifespanGenerator


class Lifespan:

    __slots__ = ('on_startup', 'on_shutdown', 'on_lifespan',
                 '_started', '_launched')

    def __init__(self,
                 on_startup: Sequence[Callable] = None,
                 on_shutdown: Sequence[Callable] = None,
                 on_lifespan: Sequence[LifespanGenerator] = None) -> None:
        self.on_startup = on_startup or []
        self.on_shutdown = on_shutdown or []
        self.on_lifespan = on_lifespan or []

        self._started = False
        self._launched = []

    async def _handle(self, func: Callable, app: ASGIApp = None) -> Any:
        if iscoroutinefunction(func):
            return await func(app)
        return await run_in_threadpool(func, app)

    async def _handle_gen(self, func: Callable, is_async: bool) -> Any:
        try:
            if is_async:
                await func()
            else:
                func()
        except (StopIteration, StopAsyncIteration):
            pass
        else:
            if self._started:
                raise RuntimeError('lifespan context yielded multiple times')

    def _state_started(self) -> None:
        self._started = True

    def _error_message(self, state: str) -> Dict[str, str]:
        return {'type': f'lifespan.{state}.failed', 'message': format_exc()}

    def _success_message(self, state: str) -> Dict[str, str]:
        return {'type': f'lifespan.{state}.complete'}

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        try:
            app = scope.get('app')

            await receive()
            await self._startup(app)
            await self._startup_lifespan(app)
            await send(self._success_message('startup'))
            self._state_started()

            await receive()
            await self._shutdown_lifespan()
            await self._shutdown(app)
            await send(self._success_message('shutdown'))
        except Exception:
            if self._started:
                await send(self._error_message('shutdown'))
            else:
                await send(self._error_message('startup'))

    async def _startup(self, app: Optional[ASGIApp]) -> None:
        for func in self.on_startup:
            await self._handle(func, app)

    async def _startup_lifespan(self, app: Optional[ASGIApp]) -> None:
        for func in self.on_lifespan:
            if isasyncgenfunction(func):
                gen_next = func(app).__aiter__().__anext__
                is_async = True
            else:
                gen_next = func(app).__iter__().__next__
                is_async = False

            await self._handle_gen(gen_next, is_async=is_async)
            self._launched.append((gen_next, is_async))

    async def _shutdown_lifespan(self) -> None:
        for gen_next, is_async in reversed(self._launched):
            await self._handle_gen(gen_next, is_async=is_async)

    async def _shutdown(self, app: Optional[ASGIApp]) -> None:
        for func in self.on_shutdown:
            await self._handle(func, app)

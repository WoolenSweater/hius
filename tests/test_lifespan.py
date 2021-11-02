import pytest
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient as BaseTestClient
from hius.routing import Router as BaseRouter, route
from hius.routing.lifespan import Lifespan


class TestClient(BaseTestClient):
    startup_complete = False
    shutdown_complete = False

    async def wait_startup(self):
        await self._wait('startup')
        self.startup_complete = True

    async def wait_shutdown(self):
        await self._wait('shutdown')
        self.shutdown_complete = True

    async def _wait(self, state):
        await self.stream_receive.send({'type': f'lifespan.{state}'})
        message = await self.stream_send.receive()
        if message is None and state == 'shutdown':
            return
        assert message['type'] in (
            f'lifespan.{state}.complete',
            f'lifespan.{state}.failed'
        )


async def hello_world(request):
    return PlainTextResponse('hello, world')


async def async_func(app):
    return


def sync_func(app):
    return


async def async_generator(app):
    yield


def sync_generator(app):
    yield


def err_func(app):
    raise RuntimeError


def err_generator_startup(app):
    raise RuntimeError
    yield


def err_generator_shutdown(app):
    yield
    raise RuntimeError


def err_generator_multiple_yield(app):
    yield
    yield


class Router(BaseRouter):
    def __init__(self, lifespan):
        super().__init__(routes=[route('/', hello_world)], lifespan=lifespan)


# ---

_params_separate = [
    ({'on_startup': [async_func], 'on_shutdown': [async_func]}),
    ({'on_startup': [sync_func], 'on_shutdown': [sync_func]}),
    ({'on_startup': [async_func], 'on_shutdown': [sync_func]}),
    ({'on_startup': [sync_func], 'on_shutdown': [async_func]}),
    ({'on_lifespan': [async_generator]}),
    ({'on_lifespan': [sync_generator]})
]
_ids_separate = [
    'async-async',
    'sync-sync',
    'async-sync',
    'sync-async',
    'async-generator',
    'sync-generator',
]


@pytest.mark.parametrize('param', _params_separate, ids=_ids_separate)
def test_lifespan(param):
    app = Router(Lifespan(**param))
    client = TestClient(app)

    assert not client.startup_complete
    assert not client.shutdown_complete

    with client as cli:
        assert client.startup_complete
        assert not client.shutdown_complete
        cli.get('/')

    assert client.startup_complete
    assert client.shutdown_complete


# ---


_params_raise_on = [
    ('startup', {'on_startup': [err_func]}),
    ('shutdown', {'on_shutdown': [err_func]}),
    ('startup', {'on_lifespan': [err_generator_startup]}),
    ('shutdown', {'on_lifespan': [err_generator_shutdown]}),
    ('shutdown', {'on_lifespan': [err_generator_multiple_yield]})
]
_ids_raise_on = [
    'startup',
    'shutdown',
    'startup-lifespan',
    'shutdown-lifespan',
    'shutdown-multiple-yield'
]


@pytest.mark.parametrize('state, params', _params_raise_on, ids=_ids_raise_on)
def test_raise_on(state, params):
    flag = False

    router = Router(Lifespan(**params))

    async def app(scope, receive, send):
        async def _send(message):
            nonlocal flag
            if message['type'] == f'lifespan.{state}.failed':
                flag = True
            return await send(message)
        await router(scope, receive, _send)

    with TestClient(app):
        pass

    assert flag

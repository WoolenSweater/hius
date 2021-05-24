import os
import pytest
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from liteapi import LiteAPI
from liteapi.routing import Router
from liteapi.handlers import StaticFiles


app = LiteAPI()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['testserver'])


@app.exception_handler(500)
async def error_500(request, exc):
    return JSONResponse({'detail': 'Server Error'}, status_code=500)


@app.exception_handler(405)
async def method_not_allowed(request, exc):
    return JSONResponse({'detail': 'Custom message'}, status_code=405)


@app.exception_handler(HTTPException)
async def http_exception(request, exc):
    return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)


@app.route('/sync_func')
def sync_func_homepage(request):
    return PlainTextResponse('Hello, world! (SYNC)')


@app.route('/async_func')
async def async_func_homepage(request):
    return PlainTextResponse('Hello, world! (ASYNC)')


@app.route('/class', methods=['GET', 'POST'])
class Homepage:
    def get(self, request):
        return PlainTextResponse('Hello, world! (SYNC, GET)')

    async def post(self, request):
        return PlainTextResponse('Hello, world! (ASYNC, POST)')


users = Router()


@users.route('/')
def all_users_page(request):
    return PlainTextResponse('Hello, everyone!')


@users.route('/{username}')
def user_page(request):
    username = request.path_params['username']
    return PlainTextResponse(f'Hello, {username}!')


app.mount('/users', users)


@app.route('/500')
def runtime_error(request):
    raise RuntimeError()


@app.websocket('/ws')
async def websocket_endpoint(session):
    await session.accept()
    await session.send_text('Hello, world!')
    await session.close()


# ---


@pytest.fixture
def cli():
    return TestClient(app)


@pytest.fixture
def cli_exc():
    return TestClient(app, raise_server_exceptions=False)


# ---


def test_sync_func_route(cli):
    response = cli.get('/sync_func')
    assert response.status_code == 200
    assert response.text == 'Hello, world! (SYNC)'

    response = cli.head('/sync_func')
    assert response.status_code == 200
    assert response.text == ""


def test_async_func_route(cli):
    response = cli.get('/async_func')
    assert response.status_code == 200
    assert response.text == 'Hello, world! (ASYNC)'

    response = cli.head('/async_func')
    assert response.status_code == 200
    assert response.text == ''


def test_sync_class_get_route(cli):
    response = cli.get('/class')
    assert response.status_code == 200
    assert response.text == 'Hello, world! (SYNC, GET)'


def test_async_class_post_route(cli):
    response = cli.post('/class')
    assert response.status_code == 200
    assert response.text == 'Hello, world! (ASYNC, POST)'


# ---


def test_mounted_route(cli):
    response = cli.get('/users/')
    assert response.status_code == 200
    assert response.text == 'Hello, everyone!'


def test_mounted_route_path_params(cli):
    response = cli.get('/users/liteapi')
    assert response.status_code == 200
    assert response.text == 'Hello, liteapi!'


def test_websocket_route(cli):
    with cli.websocket_connect('/ws') as session:
        text = session.receive_text()
        assert text == 'Hello, world!'


# --


def test_400(cli):
    response = cli.get('/404')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Not Found'}


def test_405(cli):
    response = cli.post('/sync_func')
    assert response.status_code == 405
    assert response.json() == {'detail': 'Custom message'}

    response = cli.put('/class')
    assert response.status_code == 405
    assert response.json() == {'detail': 'Custom message'}


def test_500(cli_exc):
    response = cli_exc.get('/500')
    assert response.status_code == 500
    assert response.json() == {'detail': 'Server Error'}


# ---


def test_middleware():
    cli = TestClient(app, base_url='http://incorrecthost')

    response = cli.get('/sync_func')
    assert response.status_code == 400
    assert response.text == 'Invalid host header'


def test_app_debug():
    app = LiteAPI(debug=True)

    @app.route('/')
    async def homepage(request):
        raise RuntimeError()

    cli = TestClient(app, raise_server_exceptions=False)

    response = cli.get('/')
    assert response.status_code == 500
    assert 'RuntimeError' in response.text
    assert app.debug


def test_app_mount(tmpdir):
    path = os.path.join(tmpdir, 'example.txt')
    with open(path, 'w') as file:
        file.write('<file content>')

    app = LiteAPI()
    app.mount('/static', StaticFiles(directory=tmpdir))

    cli = TestClient(app)

    response = cli.get('/static/example.txt')
    assert response.status_code == 200
    assert response.text == '<file content>'

    response = cli.post('/static/example.txt')
    assert response.status_code == 405
    assert response.text == 'Method Not Allowed'


def test_app_add_route():
    app = LiteAPI()

    async def homepage(request):
        return PlainTextResponse('Hello, World!')

    app.add_route('/', homepage)

    cli = TestClient(app)

    response = cli.get('/')
    assert response.status_code == 200
    assert response.text == 'Hello, World!'


def test_app_add_websocket_route():
    app = LiteAPI()

    async def websocket_endpoint(session):
        await session.accept()
        await session.send_text('Hello, world!')
        await session.close()

    app.add_websocket('/ws', websocket_endpoint)

    cli = TestClient(app)

    with cli.websocket_connect('/ws') as session:
        text = session.receive_text()
        assert text == 'Hello, world!'

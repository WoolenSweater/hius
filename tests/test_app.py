import os
import pytest
import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from hius import Hius
from hius.routing import Router, route
from hius.handlers import StaticFiles
from hius.responses import JSONResponse, PlainTextResponse


app = Hius()
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


@app.on_startup()
async def startup(app):
    pass


@app.on_shutdown()
def shutdown(app):
    pass


@app.on_lifespan()
async def lifespan(app):
    yield


@app.route('/sync_func')
def sync_func_homepage(request):
    return PlainTextResponse('Hello, world! (SYNC)')


@app.route('/async_func', name='custom_name_for_async')
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
def user_page(request, username: str):
    return PlainTextResponse(f'Hello, {username}!')


app.mount('/users', users)


@app.route('/400')
def bad_request(request, username: str):
    pass


@app.route('/500')
def runtime_error(request):
    raise RuntimeError()


@app.websocket('/ws')
async def websocket_endpoint(ws, name: str = None):
    await ws.accept()
    await ws.send_text(f'Hello, {name}!')
    await ws.close()


# ---


@pytest.fixture
def cli():
    return TestClient(app)


@pytest.fixture
def cli_exc():
    return TestClient(app, raise_server_exceptions=False)


# ---


def test_baggage():
    app['variable'] = 'var'
    assert app.baggage == {'variable': 'var'}
    assert app['variable'] == 'var'


# ---


def test_url_path_for_func_name():
    assert app.url_path_for('sync_func_homepage') == '/sync_func'


def test_url_path_for_custom_name():
    assert app.url_path_for('custom_name_for_async') == '/async_func'


def test_url_path_for_mounted():
    assert app.url_path_for('user_page', username='alice') == '/users/alice'


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
    response = cli.get('/users/hius')
    assert response.status_code == 200
    assert response.text == 'Hello, hius!'


def test_websocket_route(cli):
    with cli.websocket_connect('/ws?name=Alice') as session:
        assert session.receive_text() == "Hello, Alice!"


# --

def test_400(cli):
    response = cli.get('/400')
    assert response.status_code == 400
    assert response.json() == [{
        'loc': ['username'],
        'msg': 'field required',
        'type': 'value_error.missing'
    }]


def test_404(cli):
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
    app = Hius(debug=True)

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

    app = Hius()
    app.mount('/static', StaticFiles(directory=tmpdir))

    cli = TestClient(app)

    response = cli.get('/static/example.txt')
    assert response.status_code == 200
    assert response.text == '<file content>'

    response = cli.post('/static/example.txt')
    assert response.status_code == 405
    assert response.text == 'Method Not Allowed'


def test_app_add_route():
    app = Hius()

    async def homepage(request):
        return PlainTextResponse('Hello, World!')

    app.add_route('/', homepage)

    cli = TestClient(app)

    response = cli.get('/')
    assert response.status_code == 200
    assert response.text == 'Hello, World!'


def test_app_add_routes():
    app = Hius()

    async def homepage(request):
        return PlainTextResponse('Hello, World!')

    app.add_routes([route('/', homepage)])

    cli = TestClient(app)

    response = cli.get('/')
    assert response.status_code == 200
    assert response.text == 'Hello, World!'


def test_app_add_websocket_route():
    app = Hius()

    async def websocket_endpoint(session):
        await session.accept()
        await session.send_text('Hello, world!')
        await session.close()

    app.add_websocket('/ws', websocket_endpoint)

    cli = TestClient(app)

    with cli.websocket_connect('/ws') as session:
        text = session.receive_text()
        assert text == 'Hello, world!'


# ---


class MultipartPost:

    async def post(self, req):
        await asyncio.sleep(0.1)
        form = await req.form()
        file = await form['file'].read()
        return PlainTextResponse(file)


def send(cli, data):
    return cli.post('/', files={'file': data.encode()}).content.decode()


def test_multipart_form():
    cli = TestClient(Hius(routes=[route('/', MultipartPost)]))
    data = sorted(f'data{n}' for n in range(20))

    with ThreadPoolExecutor() as pool:
        assert sorted(pool.map(partial(send, cli), data)) == data

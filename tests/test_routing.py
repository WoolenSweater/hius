from uuid import UUID
import pytest
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException
from starlette.websockets import WebSocketDisconnect
from starlette.responses import JSONResponse, PlainTextResponse, Response
from hius.routing import Router, route, mount, websocket
from hius.routing.exceptions import (
    NoMatchFound,
    RouteMethodsError,
    RoutePathError,
    MountError
)
from hius.app import Hius


def homepage(request):
    return Response('Hello, world', media_type='text/plain')


def users(request):
    return Response('All users', media_type='text/plain')


def user(request):
    content = 'User ' + request.path_params['username']
    return Response(content, media_type='text/plain')


def user_me(request):
    content = 'User fixed me'
    return Response(content, media_type='text/plain')


class CBV:

    def post(self, request):
        return Response('POST', media_type='text/plain')

    def put(self, request):
        return Response('PUT', media_type='text/plain')


router = Router(
    [
        route('/', endpoint=homepage, methods=['GET']),
        route('/func_manual', endpoint=homepage, methods=['GET']),
        route('/func_default', endpoint=homepage),
        route('/cbv_manual', endpoint=CBV, methods=['GET']),
        route('/cbv_auto', endpoint=CBV),
        mount(
            '/users',
            routes=[
                route('/', endpoint=users),
                route('/me', endpoint=user_me),
                route('/{username}', endpoint=user)
            ],
        ),
        mount('/static', app=Response('xxxxx', media_type='image/png')),
    ]
)


@router.route('/func')
def func_homepage(request):
    return Response('Hello, world!', media_type='text/plain')


@router.route('/func', methods=['POST'])
def contact(request):
    return Response('Hello, POST!', media_type='text/plain')


@router.route('/int/{param:int}', name='int-convertor')
def int_convertor(request):
    number = request.path_params['param']
    return JSONResponse({'int': number})


@router.route('/float/{param:float}', name='float-convertor')
def float_convertor(request):
    num = request.path_params['param']
    return JSONResponse({'float': num})


@router.route('/path/{param:path}', name='path-convertor')
def path_convertor(request):
    path = request.path_params['param']
    return JSONResponse({'path': path})


@router.route('/uuid/{param:uuid}', name='uuid-convertor')
def uuid_converter(request):
    uuid_param = request.path_params['param']
    return JSONResponse({'uuid': str(uuid_param)})


@router.route('/path-with-parentheses({param:int})', name='path-with-parentheses')
def path_with_parentheses(request):
    number = request.path_params['param']
    return JSONResponse({'int': number})


@router.websocket('/ws')
async def websocket_endpoint(session):
    await session.accept()
    await session.send_text('Hello, world!')
    await session.close()


@router.websocket('/ws/{room}')
async def websocket_params(session):
    await session.accept()
    await session.send_text(f'Hello, {session.path_params["room"]}!')
    await session.close()


cli = TestClient(router)


# ---


def test_cbv_methods():
    assert router._http['plain']['/cbv_manual'][0].methods == {'GET'}
    assert router._http['plain']['/cbv_auto'][0].methods == {'POST', 'PUT'}


def test_func_methods():
    assert router._http['plain']['/func_manual'][0].methods == {'GET'}
    assert router._http['plain']['/func_default'][0].methods == {'GET', 'HEAD'}

# ---


_params_router_success = [
    ('get', '/', 'Hello, world'),
    ('get', '/users/hius', 'User hius'),
    ('get', '/users/me', 'User fixed me'),
    ('get', '/static/123', 'xxxxx'),
]
_ids_router_success = [
    '200-root',
    '200-specific-user',
    '200-fixed-user',
    '200-static'
]


@pytest.mark.parametrize('method, url, text',
                         _params_router_success, ids=_ids_router_success)
def test_router_success(method, url, text):
    response = getattr(cli, method)(url)
    assert response.status_code == 200
    assert response.text == text


_params_router_error = [
    ('post', '/', 405, 'Method Not Allowed'),
    ('post', '/int/1', 405, 'Method Not Allowed'),
    ('get', '/foo', 404, 'Not Found'),
    ('get', '/users', 404, 'Not Found'),
    ('get', '/users/hius/', 404, 'Not Found'),
]
_ids_router_error = [
    '405-method-not-allowed-plain',
    '405-method-not-allowed-dynamic',
    '404-not-found',
    '404-all-users-slash',
    '404-specific-user-slash'
]


@pytest.mark.parametrize('method, url, status, text',
                         _params_router_error, ids=_ids_router_error)
def test_router_error(method, url, status, text):
    with pytest.raises(HTTPException) as exc:
        getattr(cli, method)(url)

    assert exc.value.status_code == status
    assert exc.value.detail == text


_params_converters = [
    (
        '/int/5',
        {'int': 5},
        'int-convertor',
        5
    ),
    (
        '/path-with-parentheses(7)',
        {'int': 7},
        'path-with-parentheses',
        7
    ),
    (
        '/float/25.5',
        {'float': 25.5},
        'float-convertor',
        25.5
    ),
    (
        '/path/some/example',
        {'path': 'some/example'},
        'path-convertor',
        'some/example'
    ),
    (
        '/uuid/ec38df32-ceda-4cfa-9b4a-1aeb94ad551a',
        {'uuid': 'ec38df32-ceda-4cfa-9b4a-1aeb94ad551a'},
        'uuid-convertor',
        UUID('ec38df32-ceda-4cfa-9b4a-1aeb94ad551a')
    )
]
_ids_converters = [
    'int',
    'int-parentheses',
    'float',
    'path',
    'uuid'
]


@pytest.mark.parametrize('url, json, name, param',
                         _params_converters, ids=_ids_converters)
def test_route_converters(url, json, name, param):
    response = cli.get(url)
    assert response.status_code == 200
    assert response.json() == json
    assert router.url_path_for(name, param=param) == url


def test_router_add_route():
    response = cli.get('/func')
    assert response.status_code == 200
    assert response.text == 'Hello, world!'


def test_router_duplicate_path():
    response = cli.post('/func')
    assert response.status_code == 200
    assert response.text == 'Hello, POST!'


def test_router_add_websocket_route():
    with cli.websocket_connect('/ws') as session:
        text = session.receive_text()
        assert text == 'Hello, world!'

    with cli.websocket_connect('/ws/test') as session:
        text = session.receive_text()
        assert text == 'Hello, test!'


# ---


def http_endpoint(request):
    url = request.url_for('http_endpoint')
    return Response(f'URL: {url}', media_type='text/plain')


class WebSocketEndpoint:
    async def call(self, websocket):
        await websocket.accept()
        await websocket.send_json(self._get_json(websocket))
        await websocket.close()

    def _get_json(self, websocket):
        return {'URL': str(websocket.url_for('ws_endpoint'))}


mixed_protocol_router = Router(
    routes=[
        route('/', endpoint=http_endpoint),
        websocket('/', endpoint=WebSocketEndpoint(), name='ws_endpoint'),
    ]
)


def test_router_protocol_switch():
    client = TestClient(mixed_protocol_router)

    response = client.get('/')
    assert response.status_code == 200
    assert response.text == 'URL: http://testserver/'

    with client.websocket_connect('/') as session:
        assert session.receive_json() == {'URL': 'ws://testserver/'}

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/404') as session:
            session.receive_text()


ok = PlainTextResponse('OK')


# ---


def test_url_path_for():
    assert router.url_path_for('homepage') == '/'
    assert router.url_path_for('user', username='hius') == '/users/hius'
    assert router.url_path_for('websocket_endpoint') == '/ws'

    with pytest.raises(NoMatchFound):
        assert router.url_path_for('broken')


_params_url_for = [
    (
        'homepage',
        {},
        'https://example.org',
        'https://example.org/'
    ),
    (
        'homepage',
        {},
        'https://example.org/root_path/',
        'https://example.org/root_path/'
    ),
    (
        'user',
        {'username': 'hius'},
        'https://example.org',
        'https://example.org/users/hius'
    ),
    (
        'user',
        {'username': 'hius'},
        'https://example.org/root_path/',
        'https://example.org/root_path/users/hius'
    ),
    (
        'websocket_endpoint',
        {},
        'https://example.org',
        'wss://example.org/ws'
    )
]
_ids_url_for = [
    'domain', 'path', 'domain-param', 'path-param', 'websocket'
]


@pytest.mark.parametrize('name, params, base, result',
                         _params_url_for, ids=_ids_url_for)
def test_url_for(name, params, base, result):
    url = router.url_path_for(name, **params).make_absolute_url(base_url=base)
    assert url == result


def test_mount_urls():
    mounted = Router([mount('/users', app=ok, name='users')])
    client = TestClient(mounted)
    assert client.get('/users').status_code == 200
    assert client.get('/users').url == 'http://testserver/users'
    assert client.get('/users/').status_code == 200
    assert client.get('/users/a').status_code == 200

    with pytest.raises(HTTPException) as exc:
        client.get('/usersa')

    assert exc.value.status_code == 404


def test_mount_at_root():
    mounted = Router([mount('/', app=ok, name='users')])
    client = TestClient(mounted)
    assert client.get('/').status_code == 200


def test_mount_error():
    with pytest.raises(MountError):
        Router([mount('/', app=ok, routes=[route('/ok', ok)])])


# ---


async def echo_urls(request):
    return JSONResponse({
        'index': str(request.url_for('index')),
        'submount': str(request.url_for('submount')),
    })


echo_url_routes = [
    route('/', echo_urls, name='index'),
    mount('/submount', routes=[route('/', echo_urls, name='submount')]),
]


def test_url_for_with_root_path():
    app = Hius(routes=echo_url_routes)
    client = TestClient(app,
                        base_url='https://www.example.org/',
                        root_path='/sub_path')

    response = client.get('/')
    assert response.json() == {
        'index': 'https://www.example.org/sub_path/',
        'submount': 'https://www.example.org/sub_path/submount/',
    }

    response = client.get('/submount/')
    assert response.json() == {
        'index': 'https://www.example.org/sub_path/',
        'submount': 'https://www.example.org/sub_path/submount/',
    }


# ---


async def stub_app(scope, receive, send):
    pass  # pragma: no cover


double_mount_routes = [
    mount('/mount',
          routes=[mount('/static', app=stub_app, name='static')],
          name='mount'),
]


def test_url_for_with_double_mount():
    app = Hius(routes=double_mount_routes)
    assert app.url_path_for('static') == '/mount/static'


# ---


def test_duplicated_param_names():
    with pytest.raises(ValueError):
        route('/{id}/{id}', user)

    with pytest.raises(ValueError):
        route('/{id}/{name}/{id}/{name}', user)


# ---


def test_router_wrong_type_methods():
    with pytest.raises(RouteMethodsError):
        @router.route('/typeerror', methods='get, post')
        def typerror(request):
            pass


def test_router_route_without_slash():
    with pytest.raises(RoutePathError):
        @router.route('badroute')
        def badroute(request):
            pass

import os
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from liteapi import LiteAPI
from liteapi.routing import Router
from liteapi.handlers import StaticFiles


app = LiteAPI()
app.add_middleware(TrustedHostMiddleware,
                   allowed_hosts=["testserver", "*.example.org"])


@app.exception_handler(500)
async def error_500(request, exc):
    return JSONResponse({"detail": "Server Error"}, status_code=500)


@app.exception_handler(405)
async def method_not_allowed(request, exc):
    return JSONResponse({"detail": "Custom message"}, status_code=405)


@app.exception_handler(HTTPException)
async def http_exception(request, exc):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.route("/func")
def func_homepage(request):
    return PlainTextResponse("Hello, world!")


@app.route("/async")
async def async_homepage(request):
    return PlainTextResponse("Hello, world!")


@app.route("/class")
class Homepage:
    def get(self, request):
        return PlainTextResponse("Hello, world!")


users = Router()


@users.route("/")
def all_users_page(request):
    return PlainTextResponse("Hello, everyone!")


@users.route("/{username}")
def user_page(request):
    username = request.path_params["username"]
    return PlainTextResponse(f"Hello, {username}!")


app.mount("/users", users)


@app.route("/500")
def runtime_error(request):
    raise RuntimeError()


client = TestClient(app)


def test_func_route():
    response = client.get("/func")
    assert response.status_code == 200
    assert response.text == "Hello, world!"

    response = client.head("/func")
    assert response.status_code == 200
    assert response.text == ""


def test_async_route():
    response = client.get("/async")
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_class_route():
    response = client.get("/class")
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_mounted_route():
    response = client.get("/users/")
    assert response.status_code == 200
    assert response.text == "Hello, everyone!"


def test_mounted_route_path_params():
    response = client.get("/users/tomchristie")
    assert response.status_code == 200
    assert response.text == "Hello, tomchristie!"


def test_400():
    response = client.get("/404")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_405():
    response = client.post("/func")
    assert response.status_code == 405
    assert response.json() == {"detail": "Custom message"}

    response = client.post("/class")
    assert response.status_code == 405
    assert response.json() == {"detail": "Custom message"}


def test_500():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/500")
    assert response.status_code == 500
    assert response.json() == {"detail": "Server Error"}


def test_middleware():
    client = TestClient(app, base_url="http://incorrecthost")
    response = client.get("/func")
    assert response.status_code == 400
    assert response.text == "Invalid host header"


def test_app_mount(tmpdir):
    path = os.path.join(tmpdir, "example.txt")
    with open(path, "w") as file:
        file.write("<file content>")

    app = LiteAPI()
    app.mount("/static", StaticFiles(directory=tmpdir))

    client = TestClient(app)

    response = client.get("/static/example.txt")
    assert response.status_code == 200
    assert response.text == "<file content>"

    response = client.post("/static/example.txt")
    assert response.status_code == 405
    assert response.text == "Method Not Allowed"


def test_app_add_route():
    app = LiteAPI()

    async def homepage(request):
        return PlainTextResponse("Hello, World!")

    app.add_route("/", homepage)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello, World!"

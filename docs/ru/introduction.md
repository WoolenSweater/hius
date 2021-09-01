# Hius

Hius - минималистичный [ASGI](https://asgi.readthedocs.io/en/latest/) веб-фрэймворк, базирующийся на [Starlette](https://github.com/encode/starlette/) и использующий [Pydantic](https://github.com/samuelcolvin/pydantic/) для валидации параметров запроса.

## Требования

Python 3.7+

## Установка

```shell
$ pip install hius
```

или установка сразу с сервером uvicorn

```shell
$ pip install hius[uvicorn]
```

Если вы установили библиотеку без сервера, вам всё равно необходимо выбрать и установить один из них. Сейчас самыми известными являются следующие 3 сервера:

* [uvicorn](http://www.uvicorn.org/)
* [daphne](https://github.com/django/daphne/)
* [hypercorn](https://pgjones.gitlab.io/hypercorn/)


## Пример

**example.py**

```python
from hius import Hius
from hius.requests import Request
from hius.responses import PlainTextResponse

app = Hius()


def home(request: Request):
    return PlainTextResponse('Homepage')


async def user(request: Request, name: str):
    return PlainTextResponse(f'Hello, {name}!')


app.add_route('/', home)
app.add_route('/user/{name:str}', user)
```

Запускаем:

```shell
$ uvicorn example:app
```
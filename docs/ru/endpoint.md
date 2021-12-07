# Обработчик (Endpoint)

Обработчиком может быть:

* Обычная (sync/async) функция (Function Based View, FBV).
* Класс, в котором реализованы (sync/async) функции, обрабатываемых HTTP-методов (Class Based View, CBV).

Важные замечания:

* Каждый метод обработки запроса должен **обязательно** принимать хотя бы один параметр в котором будет объект запроса. У HTTP это Request, у веб-сокетов WebSocket.
* Особенностью CBV подхода является возможность обратиться к самому приложению следующим образом - `self.app`. Однако, поле будет установлено только если его ещё нет у endpoint'а и объект приложения доступен в scope запроса. Кроме того, оно **не переустанавливается** при каждом запросе.

=== "FBV"
    ```python
    from hius import Hius
    from hius.requests import Request
    from hius.responses import PlainTextResponse

    app = Hius()


    def get_page(request: Request):
        return PlainTextResponse('text')


    async def post_page(request: Request):
        return PlainTextResponse('ok')


    app.add_route('/page', get_page, methods=['GET'])
    app.add_route('/page', post_page, methods=['POST'])
    ```

=== "CBV"
    ```python
    from hius import Hius
    from hius.requests import Request
    from hius.responses import PlainTextResponse

    app = Hius()


    class Page:
        def get(self, request: Request):
            return PlainTextResponse('text')

        async def post(self, request: Request):
            return PlainTextResponse('ok')


    app.add_route('/page', Page)
    ```

## Валидация входящих параметров

Благодаря использованию [Pydantic](https://pydantic-docs.helpmanual.io/), можно валидировать входящие параметры. Валидации подвержены параметры как в самом пути, где использовались "шаблоны", так и параметры самого запроса, передаваемые после вопросительного знака `?param=1&param=2`.

Указание параметра и его типа происходит в сигнатуре метода, в котором его ожидают принять.

```python
def get_page(request: Request, number: int):
    return PlainTextResponse('text')
```

В этом примере метод ожидает получить параметр с именем `number` значение которого будет явно приведено к типу `int`.
Принятые, но не указанные в сигнатуре параметры, не валидируются, но доступны в объекте запроса.
Если какой-то параметр не прошёл валидацию, то вернется ошибка в JSON-формате со статус кодом 400 (Bad Request).

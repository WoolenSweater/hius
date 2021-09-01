# Роутинг (Routing)

Модуль создания роутов.

```python
from hius.routing import route, mount, websocket
```

## Описание

Методы модуля позволяют создать HTTP/Websocket роуты, а так же примонтировать к уже существующему приложению новое.

### Методы

Добавление HTTP роута.

**route**(path, endpoint, methods=None, name=None)

* **path** (str) - путь.
* **endpoint** (Callable) - обработчик роута.
* **methods** (Sequence[str]) - список методов, которые будут обрабатыватся на этом роуте.
* **name** (str) - имя роута.

---

Добавление Websocket роута.

**websocket**(path, endpoint, name=None)

* **path** (str) - путь.
* **endpoint** (Callable) - обработчик роута.
* **name** (str) - имя роута.

---

Монтирование суб-приложения.

**mount**(path, app, name=None)

* **path** (str) - путь.
* **endpoint** (ASGIApp) - инстанс суб-приложения.
* **name** (str) - имя cуб-приложения.


### Шаблоны пути

Вы можете использовать "шаблоны" для получения компонентов пути.

```python
route('/users/{name}', user)
```
Такой шаблон позволит получить из пути имя пользователя, не учитывая принадлежность его к какому то типу.

Существует возможность указать тип ожидаемого параметра или регулярное выражение, которому он должен соответствовать.

Доступные шаблоны:

* **str** - строковое значения.
* **int** - целочисленное значения.
* **float** - число с точкой.
* **uuid** - uuid в формате 36 символов с разделителем "-", регистронезависимый.
* **path** - весь оставшийся путь.
* **regex** - регулярное выражение.

```python
route('/page/{num:int}', page)
route('/id/{ident:uuid}', store)
route('/phone/{phone:\d{3}-\d{3}}', phonebook)
```
### Обработчик роута

[Подробнее в отдельном разделе (Endpoint)](endpoint.md)

### Имя роута

Имя необходимо для удобства получения роута внутри приложения для организации редиректов. Для этого в приложении реализован метод [url_path_for](app.md#_4).
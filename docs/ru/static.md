# Статические файлы (Static Files)

Класс позволяющий возвращать файлы из заданной директории.

```python
from hius.handlers import StaticFiles
```

## Описание

```python
class StaticFiles(directory=None,
                  packages=None,
                  check_dir=True)
```

### Параметры

* **directory** (_Union[str, os.Pathlike]_) - путь к директории.
* **packages** (_Sequence[str]_) - список питон пакетов.
* **check_dir** (_bool_) - флаг проверки существования директории.

### Использование

Инициализированный класс следует **монтировать** по пути, по которому вы хотите получать файлы.

```python
from hius import Hius
from hius.routing import mount
from hius.handlers import StaticFiles

app = Hius(routes=[mount('/static', endpoint=StaticFiles('static'))])
```
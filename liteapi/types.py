from typing import (
    AsyncGenerator,
    Callable,
    Union,
    Type,
    Dict
)
from starlette.types import ASGIApp

ExceptionHandlers = Dict[Union[int, Type[Exception]], Callable]
LifespanGenerator = Callable[[ASGIApp], AsyncGenerator]

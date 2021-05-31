from typing import (
    Callable,
    Union,
    Type,
    Dict
)

ExceptionHandlers = Dict[Union[int, Type[Exception]], Callable]

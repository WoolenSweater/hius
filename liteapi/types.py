from typing import (
    MutableMapping,
    Callable,
    Union,
    Type,
    Dict,
    Any
)

AttrScope = MutableMapping[str, Any]
ExceptionHandlers = Dict[Union[int, Type[Exception]], Callable]

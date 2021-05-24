from enum import Enum
from typing import Callable, Any
from dataclasses import dataclass


class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


@dataclass
class Converter:
    regex: str
    method: Callable[[Any], Any] = lambda v: v

    def __call__(self, value: Any) -> Any:
        return self.method(value)

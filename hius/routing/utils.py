from enum import Enum
from dataclasses import dataclass
from typing import (
    Callable,
    Optional,
    Union,
    Any
)
from starlette.datastructures import URL
from hius.routing.exceptions import ProtocolError

PROTOCOL_MAPPING = {
    'http': {True: 'https', False: 'http'},
    'websocket': {True: 'wss', False: 'ws'}
}


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


class URLPath:

    __slots__ = 'protocol', 'path', 'host',

    def __init__(self,
                 path: str,
                 protocol: str = None,
                 host: str = None) -> None:
        self.protocol = self.__check_protocol(protocol)
        self.path = path
        self.host = host

    def __eq__(self, other: Any) -> bool:
        return self.path == str(other)

    def __str__(self) -> str:
        return self.path

    def __check_protocol(self, protocol: str) -> Optional[str]:
        if protocol in ('http', 'websocket', None):
            return protocol
        raise ProtocolError('protocol should be "http", "websocket" or None')

    def format(self, **kwargs) -> 'URLPath':
        self.path = self.path.format(**kwargs)
        return self

    def appendleft(self, path: Union[str, 'URLPath']) -> 'URLPath':
        self.path = path + self.path
        return self

    def make_absolute_url(self, base_url: Union[str, URL]) -> URL:
        if isinstance(base_url, str):
            base_url = URL(base_url)

        if self.protocol:
            scheme = PROTOCOL_MAPPING[self.protocol][base_url.is_secure]
        else:
            scheme = base_url.scheme

        if self.host:
            netloc = self.host
        else:
            netloc = base_url.netloc

        path = base_url.path.rstrip('/') + self.path
        return URL(scheme=scheme, netloc=netloc, path=path)

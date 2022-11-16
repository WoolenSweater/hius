from pydantic import ValidationError


class MountError(Exception):
    '''Routes Error'''


class RoutePathError(Exception):
    '''Routes Error'''


class RouteMethodsError(Exception):
    '''Routes Error'''


class NoMatchFound(Exception):
    '''Router Error'''


class ProtocolError(Exception):
    '''URLPath Error'''


class HTTPValidationError(ValidationError):
    '''Wrapper for pydantic ValidationError for HTTP Endpoint'''

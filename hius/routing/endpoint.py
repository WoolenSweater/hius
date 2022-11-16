from typing import (
    Optional,
    Callable,
    Union,
    Tuple,
    List,
    Type,
    Dict,
    Any
)
from inspect import (
    Parameter,
    signature,
    iscoroutinefunction,
    isfunction,
    isclass,
    _empty as inspect_empty
)
from hius.requests import Request
from hius.routing.exceptions import HTTPValidationError
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.types import Scope, Receive, Send
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, create_model, ValidationError

HTTP_METHODS = ('get', 'head', 'post', 'put', 'delete',
                'connect', 'options', 'trace', 'patch')

Params = Tuple[Tuple[Union[None, Request, WebSocket]], Dict[str, Any]]
ModelFields = Dict[str, Tuple[Type, Any]]


class BaseEndpoint:

    __slots__ = 'endpoint', 'name',

    def __init__(self, endpoint: Callable, *, name: str) -> None:
        self._endpoint = endpoint

        self.name = name

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        raise NotImplementedError  # pragma: no cover

    async def _handle(self,
                      method: Callable,
                      args: Tuple[Any],
                      kwargs: Dict[str, Any]) -> Optional[Callable]:
        if iscoroutinefunction(method):
            return await method(*args, **kwargs)
        else:
            return await run_in_threadpool(method, *args, **kwargs)

    def _set_app(self, req_or_ws: Union[Request, WebSocket]) -> None:
        if not hasattr(self._endpoint, 'app') and 'app' in req_or_ws.scope:
            self._endpoint.app = req_or_ws.app

    # ---

    def __get_model_name(self, func: Callable) -> str:
        base_name = self.name.title().replace('_', '')

        if self.name != func.__name__:
            base_name += func.__name__.title()

        return base_name + 'Model'

    def __get_model_fields(self, func: Callable) -> ModelFields:
        model_fields = {}
        for param in self.__get_signature_params(func):
            default = self.__get_default(param)
            annotation = self.__get_annotation(param)

            model_fields[param.name] = (annotation, default)
        return model_fields

    def __get_signature_params(self, func: Callable) -> List:
        return list(signature(func).parameters.values())[1:]

    def __get_default(self, param: Parameter) -> Any:
        if param.default == inspect_empty:
            return ...
        return param.default

    def __get_annotation(self, param: Parameter) -> Type:
        if param.annotation == inspect_empty:
            raise RuntimeError(f'attribute type ({param.name}) not specified')
        return param.annotation

    # ---

    def _create_model(self, func: Callable) -> Type[BaseModel]:
        model_name = self.__get_model_name(func)
        model_fields = self.__get_model_fields(func)
        try:
            return create_model(model_name, **model_fields)
        except RuntimeError:
            raise RuntimeError(f'cannot create {model_name} with '
                               f'the following fields {model_fields}')

    def _create_models(self, cls: Any) -> Dict[str, Type[BaseModel]]:
        models = {}
        for method in HTTP_METHODS:
            if not hasattr(cls, method):
                continue
            models[method.upper()] = self._create_model(getattr(cls, method))
        return models

    # ---

    def _parse_params(self,
                      model: Type[BaseModel],
                      req_or_ws: Union[Request, WebSocket]) -> Dict[str, Any]:
        return model(**req_or_ws.get('path_params', {}),
                     **req_or_ws.query_params).dict()


# ---


class HTTPBaseEndpoint(BaseEndpoint):

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        try:
            request = Request(scope, receive)
            response = await self._handle(self._get_method(request),
                                          *self._get_params(request))
        except ValidationError as exc:
            raise HTTPValidationError(exc.raw_errors, exc.model)

        await response(scope, receive, send)

    def _get_params(self, req: Request) -> Params:
        return (req,), self._parse_params(self._get_model(req), req)


class HTTPFuncEndpoint(HTTPBaseEndpoint):

    __slots__ = 'model',

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint, name=endpoint.__name__)
        self.model = self._create_model(endpoint)

    def _get_method(self, _: Request) -> Callable:
        return self._endpoint

    def _get_model(self, _: Request) -> Type[BaseModel]:
        return self.model


class HTTPClassEndpoint(HTTPBaseEndpoint):

    __slots__ = 'models',

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint, name=endpoint.__class__.__name__)
        self.models = self._create_models(endpoint)

    def _get_method(self, req: Request) -> Callable:
        self._set_app(req)
        return getattr(self._endpoint, req.method.lower())

    def _get_model(self, req: Request) -> Type[BaseModel]:
        return self.models[req.method]


# ---


class WebSocketBaseEndpoint(BaseEndpoint):

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        try:
            websocket = WebSocket(scope, receive, send)
            await self._handle(self._get_method(websocket),
                               *self._get_params(websocket))
        except ValidationError:
            raise WebSocketDisconnect()

    def _get_params(self, ws: WebSocket) -> Params:
        return (ws,), self._parse_params(self.model, ws)


class WebSocketFuncEndpoint(WebSocketBaseEndpoint):

    __slots__ = 'model',

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint, name=endpoint.__name__)
        self.model = self._create_model(endpoint)

    def _get_method(self, _: WebSocket) -> Callable:
        return self._endpoint


class WebSocketClassEndpoint(WebSocketBaseEndpoint):

    __slots__ = 'model',

    def __init__(self, endpoint) -> None:
        super().__init__(endpoint, name=endpoint.__class__.__name__)
        self.model = self._create_model(endpoint.call)

    def _get_method(self, ws: WebSocket) -> Callable:
        self._set_app(ws)
        return self._endpoint.call


# ---


def get_http_endpoint(func_or_class) -> Type[BaseEndpoint]:
    return _get_endpoint(func_or_class,
                         func_endpoint=HTTPFuncEndpoint,
                         class_endpoint=HTTPClassEndpoint)


def get_websocket_endpoint(func_or_class) -> Type[BaseEndpoint]:
    return _get_endpoint(func_or_class,
                         func_endpoint=WebSocketFuncEndpoint,
                         class_endpoint=WebSocketClassEndpoint)


def _get_endpoint(func_or_class,
                  *,
                  func_endpoint,
                  class_endpoint) -> Type[BaseEndpoint]:
    if isfunction(func_or_class):
        return func_endpoint(func_or_class)

    if isclass(func_or_class):
        return class_endpoint(func_or_class())

    return class_endpoint(func_or_class)

from json import dumps
from typing import Union, Type
from pydantic import BaseModel
from starlette.types import ASGIApp, Scope, Receive, Send
from hius.responses import HTMLResponse, JSONResponse
from hius.routing.router import Router
from hius.routing.routes import BaseRoute
from hius.openapi.config import OpenAPIConfig
from hius.openapi.template import HEADER, BODY, HTML
from hius.openapi.models import (
    create_openapi_schema,
    create_operation,
    get_schema_paths
)


class FakeDict:
    def __init__(self, model: Type[BaseModel]) -> None:
        self.model = model

    def __getitem__(self, key) -> Type[BaseModel]:
        return self.model


class OpenAPIMiddleware:
    def __init__(self,
                 app: ASGIApp,
                 router: Router,
                 config: OpenAPIConfig) -> None:
        self.app = app
        self.router = router
        self.config = config

        self.header = self._make_html_header()
        self.html = None
        self.schema = None

    def _make_html_header(self) -> str:
        return HEADER.format(
            title=self.config.title,
            favicon=self.config.favicon,
        )

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        if scope['type'] == 'http' and scope['method'] == 'GET':
            if scope['path'] == self.config.doc_url:
                return await self.doc(scope, receive, send)
            elif scope['path'] == self.config.schema_url:
                return await self.json(scope, receive, send)

        await self.app(scope, receive, send)

    async def doc(self,
                  scope: Scope,
                  receive: Receive,
                  send: Send) -> None:
        response = HTMLResponse(self.html or self._create_html())

        await response(scope, receive, send)

    async def json(self,
                   scope: Scope,
                   receive: Receive,
                   send: Send) -> None:
        response = JSONResponse(self.schema or self._create_schema())

        await response(scope, receive, send)

    def _create_html(self) -> str:
        self.html = HTML.format(header=self.header, body=self._create_body())
        return self.html

    def _create_body(self) -> str:
        return BODY.format(schema=dumps(self.schema or self._create_schema()))

    def _create_schema(self) -> dict:
        schema = create_openapi_schema(self.config)
        for parents_paths, route in self.router.iter_http_routes():
            models = self._get_endpoint_models(route)
            schema_paths = get_schema_paths(schema, parents_paths, route)

            for method in route.methods:
                operation = create_operation(route, method, models[method])
                setattr(schema_paths, method.lower(), operation)

        self.schema = schema.dict(by_alias=True, exclude_none=True)
        return self.schema

    def _get_endpoint_models(self,
                             route: Type[BaseRoute]) -> Union[dict, FakeDict]:
        if hasattr(route.endpoint, 'models'):
            return route.endpoint.models
        return FakeDict(route.endpoint.model)

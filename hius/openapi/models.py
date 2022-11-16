from http import HTTPStatus
from pydantic_openapi_schema.v3_1_0 import (
    OpenAPI,
    Info,
    PathItem,
    Operation,
    Response
)


def create_openapi_schema(config) -> OpenAPI:
    return OpenAPI(
        info=Info(
            title=config.title,
            version=config.version,
            description=config.description,
        ),
        paths={}
    )


def create_operation(route, method, model) -> Operation:
    return Operation(
        operationId=f'{route.endpoint.name}_{method}'.lower(),
        summary=route.endpoint.name.title().replace('_', ' '),
        responses={
            '200': Response(description=HTTPStatus(200).description)
        }
    )


def get_schema_paths(schema, parents_paths, route) -> PathItem:
    path = ''.join(parents_paths) + route.path
    if path not in schema.paths:
        schema.paths[path] = PathItem()
    return schema.paths[path]

from pydantic import BaseModel, validator
from hius.routing.exceptions import RoutePathError


class OpenAPIConfig(BaseModel):
    title: str = 'Hius API'
    version: str = '1.0.0'
    favicon: str = '<meta/>'
    description: str = None

    doc_url: str = '/docs'
    schema_url: str = '/openapi.json'

    @validator('doc_url', 'schema_url')
    def _check_url(cls, value):
        if not value.startswith('/'):
            raise RoutePathError('path must start with "/"')

from hius.requests import Request
from hius.responses import JSONResponse
from hius.routing.exceptions import HTTPValidationError


def validation_error_handler(req: Request,
                             exc: HTTPValidationError) -> JSONResponse:
    return JSONResponse(exc.errors(), status_code=400)

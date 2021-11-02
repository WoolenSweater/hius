from starlette.exceptions import HTTPException


class HTTPExceptionTemplate(HTTPException):

    def __init__(self):
        super().__init__(self.status_code)


# --- 2xx ---


class HTTPOk(HTTPExceptionTemplate):
    status_code = 200


class HTTPCreated(HTTPExceptionTemplate):
    status_code = 201


class HTTPAccepted(HTTPExceptionTemplate):
    status_code = 202


class HTTPNonAuthoritativeInformation(HTTPExceptionTemplate):
    status_code = 203


class HTTPNoContent(HTTPExceptionTemplate):
    status_code = 204


class HTTPResetContent(HTTPExceptionTemplate):
    status_code = 205


class HTTPPartialContent(HTTPExceptionTemplate):
    status_code = 206


# --- 3xx ---


class HTTPMultipleChoices(HTTPExceptionTemplate):
    status_code = 300


class HTTPExceptionTemplatedPermanently(HTTPExceptionTemplate):
    status_code = 301


class HTTPFound(HTTPExceptionTemplate):
    status_code = 302


class HTTPSeeOther(HTTPExceptionTemplate):
    status_code = 303


class HTTPNotModified(HTTPExceptionTemplate):
    status_code = 304


class HTTPUseProxy(HTTPExceptionTemplate):
    status_code = 305


class HTTPTemporaryRedirect(HTTPExceptionTemplate):
    status_code = 307


class HTTPPermanentRedirect(HTTPExceptionTemplate):
    status_code = 308


# --- 4xx ---


class HTTPBadRequest(HTTPExceptionTemplate):
    status_code = 400


class HTTPUnauthorized(HTTPExceptionTemplate):
    status_code = 401


class HTTPPaymentRequired(HTTPExceptionTemplate):
    status_code = 402


class HTTPForbidden(HTTPExceptionTemplate):
    status_code = 403


class HTTPNotFound(HTTPExceptionTemplate):
    status_code = 404


class HTTPMethodNotAllowed(HTTPExceptionTemplate):
    status_code = 405


class HTTPNotAcceptable(HTTPExceptionTemplate):
    status_code = 406


class HTTPProxyAuthenticationRequired(HTTPExceptionTemplate):
    status_code = 407


class HTTPRequestTimeout(HTTPExceptionTemplate):
    status_code = 408


class HTTPConflict(HTTPExceptionTemplate):
    status_code = 409


class HTTPGone(HTTPExceptionTemplate):
    status_code = 410


class HTTPLengthRequired(HTTPExceptionTemplate):
    status_code = 411


class HTTPPreconditionFailed(HTTPExceptionTemplate):
    status_code = 412


class HTTPRequestEntityTooLarge(HTTPExceptionTemplate):
    status_code = 413


class HTTPRequestURITooLong(HTTPExceptionTemplate):
    status_code = 414


class HTTPUnsupportedMediaType(HTTPExceptionTemplate):
    status_code = 415


class HTTPRequestRangeNotSatisfiable(HTTPExceptionTemplate):
    status_code = 416


class HTTPExpectationFailed(HTTPExceptionTemplate):
    status_code = 417


class HTTPMisdirectedRequest(HTTPExceptionTemplate):
    status_code = 421


class HTTPUnprocessableEntity(HTTPExceptionTemplate):
    status_code = 422


class HTTPFailedDependency(HTTPExceptionTemplate):
    status_code = 424


class HTTPUpgradeRequired(HTTPExceptionTemplate):
    status_code = 426


class HTTPPreconditionRequired(HTTPExceptionTemplate):
    status_code = 428


class HTTPTooManyRequests(HTTPExceptionTemplate):
    status_code = 429


class HTTPRequestHeaderFieldsTooLarge(HTTPExceptionTemplate):
    status_code = 431


class HTTPUnavailableForLegalReasons(HTTPExceptionTemplate):
    status_code = 451


# --- 5xx ---


class HTTPInternalServerError(HTTPExceptionTemplate):
    status_code = 500


class HTTPNotImplemented(HTTPExceptionTemplate):
    status_code = 501


class HTTPBadGateway(HTTPExceptionTemplate):
    status_code = 502


class HTTPServiceUnavailable(HTTPExceptionTemplate):
    status_code = 503


class HTTPGatewayTimeout(HTTPExceptionTemplate):
    status_code = 504


class HTTPVersionNotSupported(HTTPExceptionTemplate):
    status_code = 505


class HTTPVariantAlsoNegotiates(HTTPExceptionTemplate):
    status_code = 506


class HTTPInsufficientStorage(HTTPExceptionTemplate):
    status_code = 507


class HTTPNotExtended(HTTPExceptionTemplate):
    status_code = 510


class HTTPNetworkAuthenticationRequired(HTTPExceptionTemplate):
    status_code = 511

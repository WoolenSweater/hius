# Ответ (Response)

Hius использует оригинальные объекты ответа из Starlette, однако для единообразия, импортировать их можно следующим образом:

```python
from hius.responses import PlainTextResponse, ...
```

Ознакомится с ними можно в [документации родительской библиотеки](https://www.starlette.io/responses/).

## HTTP ошибки

Если вам нужно вернуть клиенту определённый HTTP код с его стандартным описанием, вы можете импортировать вспомогательный класс и возбудить исключение в любом месте в процессе обработки запроса.

```python
from hius.httpcodes import HTTPUnauthorized
from hius.responses import PlainTextResponse


def handler(request, password: str):
    if password != 'super_password':
        raise HTTPUnauthorized()
    return PlainTextResponse('Allowed')
```

Ниже приведен список существующих шаблонов ответов.

* 200 - HTTPOk
* 201 - HTTPCreated
* 202 - HTTPAccepted
* 203 - HTTPNonAuthoritativeInformation
* 204 - HTTPNoContent
* 205 - HTTPResetContent
* 206 - HTTPPartialContent
* 300 - HTTPMultipleChoices
* 301 - HTTPExceptiondPermanently
* 302 - HTTPFound
* 303 - HTTPSeeOther
* 304 - HTTPNotModified
* 305 - HTTPUseProxy
* 307 - HTTPTemporaryRedirect
* 308 - HTTPPermanentRedirect
* 400 - HTTPBadRequest
* 401 - HTTPUnauthorized
* 402 - HTTPPaymentRequired
* 403 - HTTPForbidden
* 404 - HTTPNotFound
* 405 - HTTPMethodNotAllowed
* 406 - HTTPNotAcceptable
* 407 - HTTPProxyAuthenticationRequired
* 408 - HTTPRequestTimeout
* 409 - HTTPConflict
* 410 - HTTPGone
* 411 - HTTPLengthRequired
* 412 - HTTPPreconditionFailed
* 413 - HTTPRequestEntityTooLarge
* 414 - HTTPRequestURITooLong
* 415 - HTTPUnsupportedMediaType
* 416 - HTTPRequestRangeNotSatisfiable
* 417 - HTTPExpectationFailed
* 421 - HTTPMisdirectedRequest
* 422 - HTTPUnprocessableEntity
* 424 - HTTPFailedDependency
* 426 - HTTPUpgradeRequired
* 428 - HTTPPreconditionRequired
* 429 - HTTPTooManyRequests
* 431 - HTTPRequestHeaderFieldsTooLarge
* 451 - HTTPUnavailableForLegalReasons
* 500 - HTTPInternalServerError
* 501 - HTTPNotImplemented
* 502 - HTTPBadGateway
* 503 - HTTPServiceUnavailable
* 504 - HTTPGatewayTimeout
* 505 - HTTPVersionNotSupported
* 506 - HTTPVariantAlsoNegotiates
* 507 - HTTPInsufficientStorage
* 510 - HTTPNotExtended
* 511 - HTTPNetworkAuthenticationRequired
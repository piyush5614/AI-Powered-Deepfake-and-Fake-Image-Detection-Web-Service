import logging
import uuid
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger("truthlens")


class ApiException(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _error_response(status_code: int, code: str, message: str, headers: Mapping[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=dict(headers or {}),
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def api_exception_handler(_: Request, exc: ApiException) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("Request validation rejected: %s", exc.errors())
        return _error_response(422, "validation_error", "The request could not be validated.")

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return _error_response(
            429,
            "rate_limited",
            "Too many analysis requests. Please wait before trying again.",
            {"Retry-After": "60"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            return _error_response(exc.status_code, str(exc.detail["code"]), str(exc.detail["message"]), exc.headers)
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "The requested resource was not found." if exc.status_code == 404 else "The request could not be completed."
        return _error_response(exc.status_code, code, message, exc.headers)

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.exception("Unhandled request error (request_id=%s)", request_id, exc_info=exc)
        return _error_response(500, "internal_error", f"An unexpected error occurred. Reference: {request_id}")

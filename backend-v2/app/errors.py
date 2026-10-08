"""Centralized API error types and exception handlers (Phase 4).

Every handler returns a safe, structured body — no stack traces, no
internal exception text leaked to the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Base for all typed application errors."""

    status_code = 500
    error_code = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"


class AuthenticationError(AppError):
    status_code = 401
    error_code = "authentication_error"


class AuthorizationError(AppError):
    status_code = 403
    error_code = "authorization_error"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class DatabaseError(AppError):
    status_code = 500
    error_code = "database_error"


class QueueError(AppError):
    status_code = 503
    error_code = "queue_error"


class LLMError(AppError):
    status_code = 502
    error_code = "llm_error"


class AgentExecutionError(AppError):
    status_code = 500
    error_code = "agent_execution_error"


class ExternalServiceError(AppError):
    status_code = 502
    error_code = "external_service_error"


class ConcurrencyError(AppError):
    """Raised when a compare-and-update retries exhaust without converging
    (Phase 11: blackboard updates must never silently lose a write)."""

    status_code = 409
    error_code = "concurrency_error"


def _body(exc: AppError) -> dict:
    return {"error": exc.error_code, "message": exc.message, "details": exc.details}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("%s on %s: %s", exc.error_code, request.url.path, exc.message)
        return JSONResponse(status_code=exc.status_code, content=_body(exc))

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "An unexpected error occurred.", "details": {}},
        )

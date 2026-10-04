from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logging import logger


class MetaCheckException(Exception):
    """Base exception for all MetaCheck domain errors."""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class DatabaseConnectionException(MetaCheckException):
    """Raised when database connection encounters a fatal error."""
    def __init__(self, message: str = "Database connection unavailable"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_UNAVAILABLE",
        )


class AuthenticationException(MetaCheckException):
    """Raised on invalid credentials or token failure."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_FAILED",
        )


class AuthorizationException(MetaCheckException):
    """Raised on insufficient RBAC permissions."""
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN_RESOURCE",
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers for the FastAPI application."""

    @app.exception_handler(MetaCheckException)
    async def metacheck_exception_handler(
        request: Request, exc: MetaCheckException
    ) -> JSONResponse:
        logger.error(f"MetaCheck Exception [{exc.code}]: {exc.message} (status: {exc.status_code})")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(f"Request Validation Error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload structure.",
                    "details": exc.errors(),
                }
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        code = "HTTP_EXCEPTION"
        if exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 409:
            code = "CONFLICT"

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": code,
                    "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                    "details": exc.detail if isinstance(exc.detail, (dict, list)) else None,
                }
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(f"Unhandled server error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please contact support.",
                    "details": None,
                }
            }
        )

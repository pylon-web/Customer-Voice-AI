"""Global application exceptions and error handling structures."""

from typing import Any, Dict, Optional


class AppBaseException(Exception):
    """Base exception for all domain and application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppBaseException):
    """Resource not found error (HTTP 404)."""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' was not found.",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ValidationError(AppBaseException):
    """Input or entity validation error (HTTP 422)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=422, details=details)


class ServiceUnavailableError(AppBaseException):
    """Downstream or external dependency failure (HTTP 503)."""

    def __init__(self, service: str, reason: str):
        super().__init__(
            message=f"Service '{service}' is temporarily unavailable: {reason}",
            status_code=503,
            details={"service": service, "reason": reason},
        )

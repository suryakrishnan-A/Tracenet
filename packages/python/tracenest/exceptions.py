"""TraceNest SDK Exceptions."""

from typing import Optional


class TraceNestError(Exception):
    """Base exception for all TraceNest SDK errors."""
    pass


class TraceNestConfigError(TraceNestError):
    """Raised when client initialization configuration is invalid or missing."""
    pass


class TraceNestDeliveryError(TraceNestError):
    """Raised when telemetry delivery to the TraceNest backend fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.retry_after = retry_after


class TraceNestRateLimitError(TraceNestDeliveryError):
    """Raised when the TraceNest backend responds with HTTP 429 Too Many Requests."""
    pass

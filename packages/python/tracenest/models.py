"""TraceNest Data Transfer Models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of a telemetry event transmission attempt."""
    success: bool
    status_code: Optional[int] = None
    event_id: Optional[str] = None
    project_id: Optional[str] = None
    issue_id: Optional[str] = None
    fingerprint: Optional[str] = None
    error: Optional[str] = None
    retry_after: Optional[int] = None

    def __bool__(self) -> bool:
        return self.success


@dataclass
class EventPayload:
    """Structured telemetry event payload matching TraceNest REST API."""
    event_type: str
    severity: str
    message: str
    stack_trace: Optional[str] = None
    endpoint: Optional[str] = None
    http_status: Optional[int] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert payload to JSON-serializable dictionary."""
        out: Dict[str, Any] = {
            "event_type": self.event_type,
            "severity": self.severity,
            "message": self.message,
            "metadata": self.metadata,
        }
        if self.stack_trace is not None:
            out["stack_trace"] = self.stack_trace
        if self.endpoint is not None:
            out["endpoint"] = self.endpoint
        if self.http_status is not None:
            out["http_status"] = self.http_status
        if self.duration_ms is not None:
            out["duration_ms"] = self.duration_ms
        if self.timestamp is not None:
            out["timestamp"] = self.timestamp.isoformat()
        return out

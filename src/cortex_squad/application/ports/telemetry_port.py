"""Telemetric observability port."""

from typing import Any, Protocol


class TelemetryPort(Protocol):
    """Port for streaming squad deliberation and execution events."""

    def emit_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """Emits an observable execution event."""
        ...

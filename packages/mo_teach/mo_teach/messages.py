"""Message types exchanged over the broker."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ParameterValue:
    """A timestamped instance of a parameter (identity ≠ definition ≠ value)."""

    name: str  # entity key, e.g. "spacecraft.eps/BatteryVoltage"
    value: Any
    timestamp: datetime = field(default_factory=utcnow)
    validity: str = "VALID"


@dataclass(frozen=True)
class ProgressEvent:
    """One event in a PROGRESS-pattern action execution.

    ``status`` is one of ACKNOWLEDGED, IN_PROGRESS, COMPLETED, FAILED.
    ACKNOWLEDGED has stage 0; IN_PROGRESS events count 1..total_stages.
    """

    action: str
    action_id: int
    stage: int
    total_stages: int
    status: str
    detail: str = ""
    timestamp: datetime = field(default_factory=utcnow)

"""MO MC boilerplate — teaching skeleton for the CCSDS MO Monitor & Control labs.

PLACEHOLDER: replace this file with the real ``mo_mc_boilerplate.py``. In
Phase 3 this module is extended into the ``mo_teach`` package (broker,
Parameter/Action provider + consumer) that the lab grading harness runs
student submissions against.

The shapes here mirror MO concepts at teaching scale: an in-process broker
for PUB-SUB, a Parameter provider that publishes values, and a consumer that
subscribes to them. Entity separation (consumer / provider / broker) is the
rule students are graded on, so the classes are deliberately kept apart.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ParameterValue:
    """A single published value of a named parameter."""

    name: str
    value: Any
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


Subscriber = Callable[[ParameterValue], None]


class Broker:
    """Minimal in-process PUB-SUB broker.

    Publishers and subscribers meet here and never reference each other —
    the entity-separation rule the labs enforce.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}
        self._lock = threading.Lock()

    def subscribe(self, parameter_name: str, callback: Subscriber) -> None:
        with self._lock:
            self._subscribers.setdefault(parameter_name, []).append(callback)

    def publish(self, update: ParameterValue) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(update.name, ()))
        for callback in callbacks:
            callback(update)


class ParameterProvider:
    """Provider side of the Parameter service: owns values, publishes updates."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker
        self._values: dict[str, ParameterValue] = {}

    def set_value(self, name: str, value: Any) -> ParameterValue:
        update = ParameterValue(name=name, value=value)
        self._values[name] = update
        self._broker.publish(update)
        return update

    def get_value(self, name: str) -> ParameterValue | None:
        return self._values.get(name)


class ParameterConsumer:
    """Consumer side: subscribes via the broker, keeps a local latest-value cache."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker
        self.latest: dict[str, ParameterValue] = {}

    def monitor(self, parameter_name: str) -> None:
        self._broker.subscribe(parameter_name, self._on_update)

    def _on_update(self, update: ParameterValue) -> None:
        self.latest[update.name] = update


if __name__ == "__main__":
    broker = Broker()
    provider = ParameterProvider(broker)
    consumer = ParameterConsumer(broker)

    consumer.monitor("BATTERY_VOLTAGE")
    provider.set_value("BATTERY_VOLTAGE", 27.9)

    received = consumer.latest["BATTERY_VOLTAGE"]
    print(f"{received.name} = {received.value} @ {received.timestamp.isoformat()}")

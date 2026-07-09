"""Parameter service (teaching scale): provider owns values, consumers monitor.

Mirrors CCSDS 522.1 concepts: definitions are versionable metadata, values are
timestamped instances published over PUB-SUB (``monitorValue``), and
``get_value`` models the REQUEST-pattern fallback.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mo_teach.broker import Broker
from mo_teach.messages import ParameterValue


@dataclass(frozen=True)
class ParameterDefinition:
    name: str
    unit: str = ""
    description: str = ""


class ParameterProvider:
    """Provider side: defines parameters, publishes value updates to the broker."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker
        self._definitions: dict[str, ParameterDefinition] = {}
        self._values: dict[str, ParameterValue] = {}

    def define(
        self, name: str, unit: str = "", description: str = ""
    ) -> ParameterDefinition:
        definition = ParameterDefinition(name=name, unit=unit, description=description)
        self._definitions[name] = definition
        return definition

    def update(
        self, name: str, value: Any, validity: str = "VALID"
    ) -> ParameterValue:
        """Set a new value and publish it (monitorValue / PUB-SUB)."""
        if name not in self._definitions:
            raise KeyError(f"parameter {name!r} has no definition")
        pv = ParameterValue(name=name, value=value, validity=validity)
        self._values[name] = pv
        self._broker.publish(name, pv)
        return pv

    def get_value(self, name: str) -> ParameterValue | None:
        """REQUEST-pattern lookup of the latest value."""
        return self._values.get(name)

    def definitions(self) -> list[ParameterDefinition]:
        return list(self._definitions.values())


class ParameterConsumer:
    """Consumer side: subscribes via the broker, caches latest values."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker
        self.latest: dict[str, ParameterValue] = {}
        self._callbacks: list[Callable[[ParameterValue], None]] = []

    def monitor(
        self,
        pattern: str,
        callback: Callable[[ParameterValue], None] | None = None,
    ) -> None:
        """Subscribe to all parameters matching ``pattern`` (e.g. ``spacecraft.eps/*``)."""
        if callback is not None:
            self._callbacks.append(callback)
        self._broker.subscribe(pattern, self._on_update)

    def _on_update(self, topic: str, message: ParameterValue) -> None:
        self.latest[message.name] = message
        for callback in self._callbacks:
            callback(message)

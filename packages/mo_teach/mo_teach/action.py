"""Action service (teaching scale): SUBMIT + staged PROGRESS reporting.

A provider registers named actions with a stage count and optional
precondition. Submitting an action publishes ACKNOWLEDGED, then the handler
reports each stage (IN_PROGRESS events), then COMPLETED or FAILED — all on
the broker topic ``actions/<name>/<action_id>`` so any consumer can observe
execution without coupling to the provider.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import count
from typing import Any

from mo_teach.broker import Broker
from mo_teach.messages import ProgressEvent


class ActionError(Exception):
    """Raised when an action is rejected or fails during execution."""


class ProgressReporter:
    """Handed to action handlers; each ``report()`` publishes an IN_PROGRESS event."""

    def __init__(
        self, broker: Broker, topic: str, action: str, action_id: int, total_stages: int
    ) -> None:
        self._broker = broker
        self._topic = topic
        self._action = action
        self._action_id = action_id
        self.total_stages = total_stages
        self.stage = 0

    def report(self, detail: str = "") -> None:
        self.stage += 1
        self._broker.publish(
            self._topic,
            ProgressEvent(
                action=self._action,
                action_id=self._action_id,
                stage=self.stage,
                total_stages=self.total_stages,
                status="IN_PROGRESS",
                detail=detail,
            ),
        )


ActionHandler = Callable[[dict[str, Any], ProgressReporter], Any]
Precondition = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    handler: ActionHandler = field(repr=False)
    total_stages: int = 1
    precondition: Precondition | None = field(default=None, repr=False)


@dataclass(frozen=True)
class ActionExecution:
    action: str
    action_id: int
    status: str
    result: Any = None


class ActionProvider:
    """Provider side of the Action service."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker
        self._actions: dict[str, ActionDefinition] = {}
        self._ids = count(1)

    def register(
        self,
        name: str,
        handler: ActionHandler,
        total_stages: int = 1,
        precondition: Precondition | None = None,
    ) -> ActionDefinition:
        definition = ActionDefinition(
            name=name,
            handler=handler,
            total_stages=total_stages,
            precondition=precondition,
        )
        self._actions[name] = definition
        return definition

    def actions(self) -> list[str]:
        return sorted(self._actions)

    def submit(self, name: str, args: dict[str, Any] | None = None) -> ActionExecution:
        """SUBMIT an action: ack, execute with progress events, complete or fail."""
        args = args or {}
        definition = self._actions.get(name)
        if definition is None:
            raise ActionError(f"unknown action {name!r}")

        action_id = next(self._ids)
        topic = f"actions/{name}/{action_id}"

        def emit(stage: int, status: str, detail: str = "") -> None:
            self._broker.publish(
                topic,
                ProgressEvent(
                    action=name,
                    action_id=action_id,
                    stage=stage,
                    total_stages=definition.total_stages,
                    status=status,
                    detail=detail,
                ),
            )

        if definition.precondition is not None and not definition.precondition(args):
            emit(0, "FAILED", "precondition not met")
            raise ActionError(f"precondition not met for {name!r} with {args!r}")

        emit(0, "ACKNOWLEDGED")
        reporter = ProgressReporter(
            self._broker, topic, name, action_id, definition.total_stages
        )
        try:
            result = definition.handler(args, reporter)
        except ActionError as exc:
            emit(reporter.stage, "FAILED", str(exc))
            raise
        except Exception as exc:
            emit(reporter.stage, "FAILED", f"{type(exc).__name__}: {exc}")
            raise ActionError(f"action {name!r} failed: {exc}") from exc

        emit(definition.total_stages, "COMPLETED", str(result))
        return ActionExecution(
            action=name, action_id=action_id, status="COMPLETED", result=result
        )


class ActionConsumer:
    """Consumer side: observes action executions via the broker."""

    def __init__(self, broker: Broker) -> None:
        self._broker = broker
        self.events: list[ProgressEvent] = []

    def watch(self, action_pattern: str = "*") -> None:
        """Collect progress events for actions matching ``action_pattern``."""
        self._broker.subscribe(f"actions/{action_pattern}/*", self._on_event)

    def events_for(self, action: str) -> list[ProgressEvent]:
        return [e for e in self.events if e.action == action]

    def _on_event(self, topic: str, message: ProgressEvent) -> None:
        self.events.append(message)

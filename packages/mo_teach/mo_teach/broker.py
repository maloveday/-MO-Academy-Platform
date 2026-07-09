"""In-process PUB-SUB broker with wildcard topic subscriptions.

The broker is the only place publishers and subscribers meet — the
entity-separation rule the labs are graded on. Topic patterns use shell-style
wildcards, e.g. ``spacecraft.eps/*`` or ``actions/SetHeaterState/*``.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from itertools import count
from typing import Any

Callback = Callable[[str, Any], None]


@dataclass(frozen=True)
class Subscription:
    id: int
    pattern: str
    callback: Callback = field(repr=False, compare=False)


class Broker:
    def __init__(self) -> None:
        self._subscriptions: dict[int, Subscription] = {}
        self._ids = count(1)
        self._lock = threading.Lock()

    def subscribe(self, pattern: str, callback: Callback) -> Subscription:
        """Register ``callback(topic, message)`` for topics matching ``pattern``."""
        sub = Subscription(id=next(self._ids), pattern=pattern, callback=callback)
        with self._lock:
            self._subscriptions[sub.id] = sub
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        with self._lock:
            self._subscriptions.pop(subscription.id, None)

    def publish(self, topic: str, message: Any) -> int:
        """Deliver ``message`` to every matching subscriber; returns delivery count."""
        with self._lock:
            matching = [
                s for s in self._subscriptions.values()
                if fnmatchcase(topic, s.pattern)
            ]
        for sub in matching:
            sub.callback(topic, message)
        return len(matching)

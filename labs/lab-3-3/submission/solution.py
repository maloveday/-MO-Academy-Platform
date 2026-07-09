"""Lab 3.3 — Parameter dashboard via PUB-SUB.

Implement ParameterDashboard per README.md. The grader runs the reference
consumers in reference/test_lab.py against this file.
"""

from mo_teach import Broker, ParameterValue


class ParameterDashboard:
    """A pure consumer: subscribes to parameter updates and renders a table."""

    def __init__(self, broker: Broker, patterns: list[str]) -> None:
        self.latest: dict[str, ParameterValue] = {}
        # TODO: subscribe to every pattern via the broker (PUB-SUB).
        raise NotImplementedError

    def render(self) -> str:
        # TODO: one line per parameter, sorted by name: "NAME  VALUE  VALIDITY"
        raise NotImplementedError

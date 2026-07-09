"""Known-good solution for Lab 3.3 — used to self-test the grading harness."""

from mo_teach import Broker, ParameterValue


class ParameterDashboard:
    """A pure consumer: subscribes to parameter updates and renders a table."""

    def __init__(self, broker: Broker, patterns: list[str]) -> None:
        self.latest: dict[str, ParameterValue] = {}
        for pattern in patterns:
            broker.subscribe(pattern, self._on_update)

    def _on_update(self, topic: str, message: ParameterValue) -> None:
        self.latest[message.name] = message

    def render(self) -> str:
        return "\n".join(
            f"{pv.name}  {pv.value}  {pv.validity}"
            for _, pv in sorted(self.latest.items())
        )

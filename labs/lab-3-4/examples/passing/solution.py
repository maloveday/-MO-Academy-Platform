"""Known-good solution for Lab 3.4 — used to self-test the grading harness."""

from typing import Any

from mo_teach import ActionProvider, ProgressReporter


class Heater:
    """Simulated thermal-control heater."""

    def __init__(self) -> None:
        self.state = "OFF"


def register_set_heater_state(provider: ActionProvider, heater: Heater) -> None:
    """Register the 3-stage SetHeaterState action on ``provider``."""

    def precondition(args: dict[str, Any]) -> bool:
        return args.get("state") in ("ON", "OFF")

    def handler(args: dict[str, Any], progress: ProgressReporter) -> str:
        target = args["state"]
        progress.report(f"command validated: target={target}")
        heater.state = target
        progress.report("heater switched")
        progress.report(f"state verified: {heater.state}")
        return heater.state

    provider.register(
        "SetHeaterState", handler, total_stages=3, precondition=precondition
    )

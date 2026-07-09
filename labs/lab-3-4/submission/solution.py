"""Lab 3.4 — SetHeaterState with progress events.

Implement Heater and register_set_heater_state per README.md.
"""

from mo_teach import ActionProvider, ProgressReporter


class Heater:
    """Simulated thermal-control heater."""

    def __init__(self) -> None:
        self.state = "OFF"


def register_set_heater_state(provider: ActionProvider, heater: Heater) -> None:
    """Register the 3-stage SetHeaterState action on ``provider``."""

    def handler(args: dict, progress: ProgressReporter) -> str:
        # TODO: three progress.report(...) stages — prepare, switch, verify —
        # setting heater.state to args["state"] and returning the final state.
        raise NotImplementedError

    # TODO: provider.register("SetHeaterState", handler, total_stages=3,
    #                         precondition=...)
    raise NotImplementedError

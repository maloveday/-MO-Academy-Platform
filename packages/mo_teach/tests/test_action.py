"""Action service: SUBMIT, staged PROGRESS events, preconditions, failures."""

import pytest

from mo_teach import ActionConsumer, ActionError, ActionProvider, Broker


def _rig() -> tuple[ActionProvider, ActionConsumer]:
    broker = Broker()
    provider = ActionProvider(broker)
    consumer = ActionConsumer(broker)
    consumer.watch()
    return provider, consumer


def test_submit_runs_handler_with_progress_sequence() -> None:
    provider, consumer = _rig()

    def handler(args, progress):
        progress.report("step one")
        progress.report("step two")
        return "done"

    provider.register("Demo", handler, total_stages=2)
    execution = provider.submit("Demo")

    assert execution.status == "COMPLETED"
    assert execution.result == "done"
    statuses = [e.status for e in consumer.events]
    assert statuses == ["ACKNOWLEDGED", "IN_PROGRESS", "IN_PROGRESS", "COMPLETED"]
    assert [e.stage for e in consumer.events] == [0, 1, 2, 2]


def test_unknown_action_rejected() -> None:
    provider, _ = _rig()
    with pytest.raises(ActionError, match="unknown action"):
        provider.submit("Nope")


def test_precondition_failure_emits_failed_and_raises() -> None:
    provider, consumer = _rig()
    provider.register(
        "Guarded", lambda a, p: "ok", precondition=lambda args: args.get("go") is True
    )
    with pytest.raises(ActionError, match="precondition"):
        provider.submit("Guarded", {"go": False})
    assert [e.status for e in consumer.events] == ["FAILED"]


def test_handler_exception_becomes_failed_event() -> None:
    provider, consumer = _rig()

    def handler(args, progress):
        progress.report("about to blow")
        raise RuntimeError("boom")

    provider.register("Explode", handler, total_stages=2)
    with pytest.raises(ActionError, match="boom"):
        provider.submit("Explode")
    statuses = [e.status for e in consumer.events]
    assert statuses == ["ACKNOWLEDGED", "IN_PROGRESS", "FAILED"]
    assert "COMPLETED" not in statuses


def test_events_for_filters_by_action() -> None:
    provider, consumer = _rig()
    provider.register("A", lambda a, p: 1)
    provider.register("B", lambda a, p: 2)
    provider.submit("A")
    provider.submit("B")
    assert {e.action for e in consumer.events_for("A")} == {"A"}

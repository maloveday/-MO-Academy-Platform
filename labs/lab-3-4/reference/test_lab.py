"""Reference consumers for Lab 3.4 — SetHeaterState with progress events."""

import inspect

import pytest
from mo_teach import ActionConsumer, ActionError, ActionProvider, Broker

import solution


@pytest.fixture()
def rig() -> tuple[ActionProvider, ActionConsumer, "solution.Heater"]:
    broker = Broker()
    provider = ActionProvider(broker)
    consumer = ActionConsumer(broker)
    consumer.watch("SetHeaterState")
    heater = solution.Heater()
    solution.register_set_heater_state(provider, heater)
    return provider, consumer, heater


# --- correctness ---


def test_heater_starts_off() -> None:
    assert solution.Heater().state == "OFF"


def test_action_is_registered(rig) -> None:
    provider, _, _ = rig
    assert "SetHeaterState" in provider.actions()


def test_submit_on_switches_heater_and_returns_state(rig) -> None:
    provider, _, heater = rig
    execution = provider.submit("SetHeaterState", {"state": "ON"})
    assert execution.status == "COMPLETED"
    assert execution.result == "ON"
    assert heater.state == "ON"


def test_submit_off_after_on(rig) -> None:
    provider, _, heater = rig
    provider.submit("SetHeaterState", {"state": "ON"})
    provider.submit("SetHeaterState", {"state": "OFF"})
    assert heater.state == "OFF"


def test_invalid_state_rejected_by_precondition(rig) -> None:
    provider, consumer, heater = rig
    with pytest.raises(ActionError):
        provider.submit("SetHeaterState", {"state": "MAXIMUM"})
    assert heater.state == "OFF", "a rejected command must not touch the heater"
    statuses = [e.status for e in consumer.events_for("SetHeaterState")]
    assert "FAILED" in statuses
    assert "COMPLETED" not in statuses


# --- pattern usage ---


@pytest.mark.rubric("pattern_usage")
def test_progress_event_sequence(rig) -> None:
    """The PROGRESS pattern: ACK, then one IN_PROGRESS per stage, then COMPLETED."""
    provider, consumer, _ = rig
    provider.submit("SetHeaterState", {"state": "ON"})
    statuses = [e.status for e in consumer.events_for("SetHeaterState")]
    assert statuses == [
        "ACKNOWLEDGED",
        "IN_PROGRESS",
        "IN_PROGRESS",
        "IN_PROGRESS",
        "COMPLETED",
    ]


@pytest.mark.rubric("pattern_usage")
def test_stages_are_numbered_and_bounded(rig) -> None:
    provider, consumer, _ = rig
    provider.submit("SetHeaterState", {"state": "ON"})
    in_progress = [
        e for e in consumer.events_for("SetHeaterState") if e.status == "IN_PROGRESS"
    ]
    assert [e.stage for e in in_progress] == [1, 2, 3]
    assert all(e.total_stages == 3 for e in in_progress)


@pytest.mark.rubric("pattern_usage")
def test_reports_via_progress_reporter_not_print() -> None:
    source = inspect.getsource(solution)
    assert ".report(" in source, "stages must be reported via ProgressReporter"
    assert "print(" not in source, "report progress on the broker, not stdout"


# --- entity separation ---


@pytest.mark.rubric("entity_separation")
def test_provider_side_only() -> None:
    source = inspect.getsource(solution)
    assert "Broker(" not in source, (
        "the provider module must not construct its own broker — it is wired "
        "up by whoever composes the system"
    )
    assert "ActionConsumer" not in source, (
        "consumer entities live outside the provider module"
    )

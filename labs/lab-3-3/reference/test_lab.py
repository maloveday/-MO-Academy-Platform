"""Reference consumers for Lab 3.3 — parameter dashboard via PUB-SUB."""

import inspect

import pytest
from mo_teach import Broker, ParameterProvider

import solution


@pytest.fixture()
def rig() -> tuple[Broker, ParameterProvider, "solution.ParameterDashboard"]:
    broker = Broker()
    provider = ParameterProvider(broker)
    provider.define("spacecraft.eps/BatteryVoltage", unit="V")
    provider.define("spacecraft.eps/SolarArrayCurrent", unit="A")
    provider.define("spacecraft.aocs/WheelSpeed_X", unit="rpm")
    dashboard = solution.ParameterDashboard(broker, ["spacecraft.eps/*"])
    return broker, provider, dashboard


# --- correctness ---


def test_receives_published_value(rig) -> None:
    _, provider, dashboard = rig
    provider.update("spacecraft.eps/BatteryVoltage", 28.1)
    pv = dashboard.latest["spacecraft.eps/BatteryVoltage"]
    assert pv.value == 28.1
    assert pv.validity == "VALID"


def test_latest_keeps_most_recent_value(rig) -> None:
    _, provider, dashboard = rig
    provider.update("spacecraft.eps/BatteryVoltage", 28.1)
    provider.update("spacecraft.eps/BatteryVoltage", 27.4)
    assert dashboard.latest["spacecraft.eps/BatteryVoltage"].value == 27.4


def test_pattern_filters_other_domains(rig) -> None:
    _, provider, dashboard = rig
    provider.update("spacecraft.aocs/WheelSpeed_X", 3041)
    assert "spacecraft.aocs/WheelSpeed_X" not in dashboard.latest


def test_render_lists_parameters_sorted(rig) -> None:
    _, provider, dashboard = rig
    provider.update("spacecraft.eps/SolarArrayCurrent", 3.2)
    provider.update("spacecraft.eps/BatteryVoltage", 28.1)
    lines = dashboard.render().splitlines()
    assert len(lines) == 2
    assert "spacecraft.eps/BatteryVoltage" in lines[0]
    assert "28.1" in lines[0]
    assert "VALID" in lines[0]
    assert "spacecraft.eps/SolarArrayCurrent" in lines[1]


def test_render_empty_dashboard(rig) -> None:
    _, _, dashboard = rig
    assert dashboard.render() == ""


# --- pattern usage ---


@pytest.mark.rubric("pattern_usage")
def test_updates_arrive_after_construction(rig) -> None:
    """PUB-SUB, not a constructor-time snapshot: publishes after init must land."""
    _, provider, dashboard = rig
    assert dashboard.latest == {}
    provider.update("spacecraft.eps/BatteryVoltage", 27.9)
    assert dashboard.latest["spacecraft.eps/BatteryVoltage"].value == 27.9


@pytest.mark.rubric("pattern_usage")
def test_subscribes_via_broker_not_polling() -> None:
    source = inspect.getsource(solution)
    assert (
        ".subscribe(" in source or ".monitor(" in source
    ), "dashboard must subscribe through the broker (PUB-SUB)"
    assert "get_value" not in source, "monitorValue means PUB-SUB, not polling get_value"


# --- entity separation ---


@pytest.mark.rubric("entity_separation")
def test_consumer_does_not_touch_provider() -> None:
    source = inspect.getsource(solution)
    assert "ParameterProvider" not in source, (
        "the dashboard is a consumer entity; it must not create or reference "
        "a ParameterProvider"
    )


@pytest.mark.rubric("entity_separation")
def test_constructor_needs_only_broker_and_patterns() -> None:
    params = list(
        inspect.signature(solution.ParameterDashboard.__init__).parameters
    )
    assert params == ["self", "broker", "patterns"]

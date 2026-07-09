"""Parameter service: definitions, updates over PUB-SUB, REQUEST lookups."""

import pytest

from mo_teach import Broker, ParameterConsumer, ParameterProvider


def test_update_publishes_to_monitoring_consumer() -> None:
    broker = Broker()
    provider = ParameterProvider(broker)
    consumer = ParameterConsumer(broker)

    provider.define("spacecraft.eps/BatteryVoltage", unit="V")
    consumer.monitor("spacecraft.eps/*")

    provider.update("spacecraft.eps/BatteryVoltage", 28.1)
    pv = consumer.latest["spacecraft.eps/BatteryVoltage"]
    assert pv.value == 28.1
    assert pv.validity == "VALID"


def test_update_requires_definition() -> None:
    provider = ParameterProvider(Broker())
    with pytest.raises(KeyError):
        provider.update("spacecraft.eps/Undefined", 1)


def test_get_value_request_pattern() -> None:
    broker = Broker()
    provider = ParameterProvider(broker)
    provider.define("spacecraft.eps/BatteryVoltage")
    assert provider.get_value("spacecraft.eps/BatteryVoltage") is None
    provider.update("spacecraft.eps/BatteryVoltage", 27.4, validity="SUSPECT")
    pv = provider.get_value("spacecraft.eps/BatteryVoltage")
    assert pv is not None and pv.value == 27.4 and pv.validity == "SUSPECT"


def test_consumer_callback_invoked() -> None:
    broker = Broker()
    provider = ParameterProvider(broker)
    consumer = ParameterConsumer(broker)
    seen: list[float] = []

    provider.define("spacecraft.eps/BatteryVoltage")
    consumer.monitor("spacecraft.eps/*", callback=lambda pv: seen.append(pv.value))
    provider.update("spacecraft.eps/BatteryVoltage", 28.1)
    assert seen == [28.1]

"""MO MC boilerplate — the course's starting point, now grown into ``mo_teach``.

This module began as the single-file boilerplate handed out in Module 3 and
has been extended into the full ``mo_teach`` package (broker, Parameter and
Action providers/consumers, grading harness). It remains as a compatibility
entry point: everything importable here comes from ``mo_teach``.
"""

from mo_teach import (
    ActionConsumer,
    ActionError,
    ActionProvider,
    Broker,
    ParameterConsumer,
    ParameterProvider,
    ParameterValue,
    ProgressEvent,
    ProgressReporter,
)

__all__ = [
    "ActionConsumer",
    "ActionError",
    "ActionProvider",
    "Broker",
    "ParameterConsumer",
    "ParameterProvider",
    "ParameterValue",
    "ProgressEvent",
    "ProgressReporter",
]

if __name__ == "__main__":
    broker = Broker()
    provider = ParameterProvider(broker)
    consumer = ParameterConsumer(broker)

    provider.define("spacecraft.eps/BatteryVoltage", unit="V")
    consumer.monitor("spacecraft.eps/*")
    provider.update("spacecraft.eps/BatteryVoltage", 27.9)

    received = consumer.latest["spacecraft.eps/BatteryVoltage"]
    print(f"{received.name} = {received.value} @ {received.timestamp.isoformat()}")

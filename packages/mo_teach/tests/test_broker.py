"""Broker: subscribe, publish, wildcard patterns, unsubscribe."""

from mo_teach import Broker


def test_publish_reaches_matching_subscriber() -> None:
    broker = Broker()
    received: list[tuple[str, str]] = []
    broker.subscribe("tm/*", lambda topic, msg: received.append((topic, msg)))

    delivered = broker.publish("tm/volts", "28.1")
    assert delivered == 1
    assert received == [("tm/volts", "28.1")]


def test_pattern_filters_non_matching_topics() -> None:
    broker = Broker()
    received: list[str] = []
    broker.subscribe("spacecraft.eps/*", lambda t, m: received.append(t))

    broker.publish("spacecraft.aocs/WheelSpeed_X", 3041)
    assert received == []
    assert broker.publish("ground.mcs/Subscribers", 147) == 0


def test_multiple_subscribers_all_receive() -> None:
    broker = Broker()
    a: list[str] = []
    b: list[str] = []
    broker.subscribe("tm/*", lambda t, m: a.append(t))
    broker.subscribe("*", lambda t, m: b.append(t))

    assert broker.publish("tm/volts", 1) == 2
    assert a == ["tm/volts"]
    assert b == ["tm/volts"]


def test_unsubscribe_stops_delivery() -> None:
    broker = Broker()
    received: list[str] = []
    sub = broker.subscribe("tm/*", lambda t, m: received.append(t))
    broker.publish("tm/volts", 1)
    broker.unsubscribe(sub)
    broker.publish("tm/volts", 2)
    assert received == ["tm/volts"]

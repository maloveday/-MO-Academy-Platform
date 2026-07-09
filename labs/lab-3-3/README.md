# Lab 3.3 — Parameter dashboard via PUB-SUB

Build a live parameter dashboard: a **consumer** that monitors published
parameter values through the broker and renders them as a console table.

## Task

Edit `submission/solution.py` and implement `ParameterDashboard`:

- `__init__(self, broker, patterns)` — subscribe (via the broker's PUB-SUB,
  i.e. `broker.subscribe` or `mo_teach.ParameterConsumer.monitor`) to every
  entity-key pattern in `patterns`, e.g. `["spacecraft.eps/*"]`.
- `latest` — a dict mapping parameter name → the most recent
  `ParameterValue` received.
- `render()` — return a string with one line per known parameter, sorted by
  name, formatted `NAME  VALUE  VALIDITY`.

## Rules (this is what the rubric checks)

- **Correctness** — values arrive, the cache updates, `render()` output.
- **Pattern usage** — updates must arrive via PUB-SUB subscription. Do not
  poll `get_value` and do not snapshot values at construction time.
- **Entity separation** — the dashboard is a pure consumer. It must not
  create or reference a `ParameterProvider`; its only link to the telemetry
  is the broker passed in.

## Grade locally

```sh
grade submission/ --lab .
```

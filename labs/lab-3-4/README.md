# Lab 3.4 — SetHeaterState with progress events

Implement the provider side of an Action-service command: `SetHeaterState`,
executed in three reported stages with a precondition.

## Task

Edit `submission/solution.py` and implement:

- `class Heater` — starts `"OFF"`; its `state` attribute reflects the last
  commanded state.
- `register_set_heater_state(provider, heater)` — register an action named
  `SetHeaterState` on the given `mo_teach.ActionProvider` with
  **3 stages** and a **precondition** requiring `args["state"]` to be
  `"ON"` or `"OFF"`. The handler must:
  1. `progress.report(...)` — validate/prepare the command
  2. `progress.report(...)` — switch the heater (set `heater.state`)
  3. `progress.report(...)` — verify the new state
  and return the final state string.

## Rules (this is what the rubric checks)

- **Correctness** — submitting `{"state": "ON"}` flips the heater and
  returns `"ON"`; the event stream is ACKNOWLEDGED → 3× IN_PROGRESS →
  COMPLETED; an invalid state is rejected by the precondition (FAILED
  event, heater untouched).
- **Pattern usage** — progress must be reported through the
  `ProgressReporter` (the PROGRESS pattern), one event per stage — not
  printed, not skipped.
- **Entity separation** — this module is provider-side only: no `Broker()`
  construction, no `ActionConsumer`. Observers watch via the broker.

## Grade locally

```sh
grade submission/ --lab .
```

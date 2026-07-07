# MO in 30 Minutes
### The CCSDS Mission Operations Framework, explained for working engineers

*Free primer — [Your Business Name]. The full course takes you from this page to shipping a custom MO service.*

---

## 1. The problem MO solves (5 min)

Every mission historically reinvents its ground-to-space interface: bespoke packet layouts, bespoke ICDs, bespoke MCS adapters. Cross-support between agencies or operators means expensive translation layers.

CCSDS Mission Operations replaces "agree on bits" with "agree on services." A Parameter is a Parameter whether the provider is onboard software, a ground gateway, or another agency's MCS.

## 2. The architecture in one picture (5 min)

```
+--------------------------------------+
|  Applications (MCS, onboard SW, EGSE)|
+--------------------------------------+
|  MO Services (Parameter, Action, …)  |   <- CCSDS 522.x
+--------------------------------------+
|  Message Abstraction Layer (MAL)     |   <- CCSDS 521.0
+--------------------------------------+
|  Transport + Encoding (TCP, SPP, …)  |
+--------------------------------------+
```

Services are defined once, abstractly, on the MAL. Bindings map them to real languages and transports. Swap the transport; the service contract is untouched.

## 3. The MAL's six interaction patterns (8 min)

| Pattern | Shape | Typical use |
|---------|-------|-------------|
| SEND | one-way | fire-and-forget notification |
| SUBMIT | request + ack | submit an action for execution |
| REQUEST | request + response | fetch a parameter value |
| INVOKE | request + ack + response | longer operations needing early ack |
| PROGRESS | request + ack + updates + response | action execution reporting |
| PUB-SUB | publish/subscribe via broker | continuous telemetry monitoring |

If you remember one thing: telemetry monitoring is PUB-SUB, commanding is SUBMIT/PROGRESS.

## 4. Monitor & Control's core idea: identity ≠ definition ≠ value (7 min)

CCSDS 522.1 splits every parameter three ways:

- **Identity** — the stable name (`spacecraft.eps / BatteryVoltage`)
- **Definition** — its meaning right now: type, unit, validity expression (versionable over mission life)
- **Value** — a timestamped instance

This is why MO systems survive database updates mid-mission without breaking consumers: subscribers hold identities, not row IDs.

The M&C service set: **Parameter** (telemetry), **Action** (commanding), **Alert** (events), **Aggregation** (grouped sampling), **Check** (limit checking), **Statistic** (derived stats).

## 5. What implementation actually looks like (5 min)

- Reference implementation: ESA's Java MO framework and the NanoSat MO Framework (flown on OPS-SAT).
- Workflow: write an XML service description → generate stubs → implement provider logic → bind to a transport.
- A minimal Parameter provider is ~100 lines over the generated stubs.

## Next step

The full course (4 modules, 16 labs) takes you from here to designing and deploying your own MO service, graded against a reference consumer.

→ [Course link] · → Reply to this email with your mission's M&C pain point; I read every one.

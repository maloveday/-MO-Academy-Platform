# CCSDS MO Service Framework — Full Course Syllabus

Format: 4 modules × 4 lessons. Each lesson = 45–60 min video + lab + quiz.
Capstone: build and demo a custom MO service end-to-end.

---

## Module 1 — CCSDS MO Foundations

**Outcome:** Explain the MO architecture and justify it against packet-based TM/TC to a program manager.

| # | Lesson | Lab |
|---|--------|-----|
| 1.1 | Why MO exists: interoperability, cross-support, the cost of bespoke GDS interfaces | Case study: map a legacy TM/TC ICD's pain points to MO capabilities |
| 1.2 | Layered architecture: Applications → MO Services → MAL → Transport & Encoding | Diagram exercise: place 6 real mission functions into the correct layer |
| 1.3 | Spec landscape: 520.0 (concept), 521.0 (MAL), 522.x (M&C), service description conventions | Scavenger hunt through the Blue Books: find 8 defined terms |
| 1.4 | Service-oriented concepts: providers, consumers, capability sets, domains | Write a one-page MO adoption memo for a fictional smallsat operator |

**Assessment:** 20-question quiz + memo peer review.

---

## Module 2 — The Message Abstraction Layer (MAL)

**Outcome:** Select correct interaction patterns and MAL data structures for a given operational need.

| # | Lesson | Lab |
|---|--------|-----|
| 2.1 | The six interaction patterns: SEND, SUBMIT, REQUEST, INVOKE, PROGRESS, PUB-SUB | Pattern-matching drill: 12 ops scenarios → correct pattern + rationale |
| 2.2 | MAL data model: Attributes, Composites, Lists, Elements; nullability and polymorphism | Model 3 telemetry structures as MAL Composites |
| 2.3 | Addressing & subscriptions: URIs, subscription filtering, entity keys, QoS levels | Configure subscriptions to receive a filtered parameter subset |
| 2.4 | Bindings: language mappings (Java API), transport bindings (MAL/TCP, MAL/SPP), encodings | Trace one message from consumer API call to wire bytes |

**Assessment:** Pattern-selection exam + data-modeling submission.

---

## Module 3 — Monitor & Control Services

**Outcome:** Implement a working Parameter + Action provider and consumer.

| # | Lesson | Lab |
|---|--------|-----|
| 3.1 | M&C service set overview: Parameter, Action, Alert, Aggregation, Check, Statistic | Map a real EPS subsystem's telemetry/commands onto the six services |
| 3.2 | Data entities: identity / definition / instance separation; versioned definitions | Extend the course boilerplate: add definitions with validity expressions |
| 3.3 | Parameter service deep dive: monitorValue (PUB-SUB), getValue, setValue | Build a live parameter dashboard consuming published values |
| 3.4 | Action service: submitAction (SUBMIT), preconditions, progress & completion reporting | Implement SetHeaterState with staged progress events |

**Assessment:** Working provider/consumer pair graded against a test harness.

---

## Module 4 — Advanced MO Service Interface Design

**Outcome:** Design, specify, and deploy a custom MO service that interoperates with reference tooling.

| # | Lesson | Lab |
|---|--------|-----|
| 4.1 | Designing custom services: operations, capability sets, versioning strategy | Draft a service spec for an orbit-determination request service |
| 4.2 | Service description: XML service definitions, code generation workflows | Generate provider/consumer stubs from your XML spec |
| 4.3 | Deployment architectures: onboard vs. ground providers, NanoSat MO Framework patterns | Deploy your service in an NMF-style supervisor/app layout |
| 4.4 | Interoperability & history: COM archive concepts, cross-support testing, conformance | Run cross-implementation tests against the reference consumer |

**Assessment:** Capstone demo + design review (rubric: correctness, spec quality, interop).

---

## Delivery notes

- Labs 3.x/4.x run in a provided Docker environment (Java reference impl + course Python harness).
- Cohort edition adds weekly live design reviews; self-paced edition uses automated grading.
- Consulting upsell hook: Module 4 capstone doubles as a client's real service prototype.

"""Quiz seed data, keyed by lesson code.

Each entry: (prompt, choices, correct_index). The seeder only inserts
questions for lessons that have none yet, so edits made in the DB survive
re-seeding. Extend this dict to add quizzes to more lessons.
"""

QUIZZES: dict[str, list[tuple[str, list[str], int]]] = {
    "1.1": [
        (
            "What problem does the CCSDS MO framework primarily address?",
            [
                "Radiation-hardening of onboard processors",
                "Interoperability of mission operations functions across agencies and systems",
                "Compression of telemetry downlink streams",
                "Orbit determination accuracy",
            ],
            1,
        ),
        (
            "MO replaces 'agree on bits' with what?",
            [
                "Agree on services",
                "Agree on packet layouts",
                "Agree on radio frequencies",
                "Agree on database schemas",
            ],
            0,
        ),
    ],
    "1.2": [
        (
            "Which layer sits directly below the MO services?",
            [
                "Applications",
                "Transport and encoding",
                "The Message Abstraction Layer (MAL)",
                "The COM archive",
            ],
            2,
        ),
        (
            "Swapping the transport binding requires what change to the service contract?",
            [
                "A full redefinition of every operation",
                "None — the service definition is transport-independent",
                "Re-versioning all parameter definitions",
                "Regenerating the spacecraft database",
            ],
            1,
        ),
    ],
    "2.1": [
        (
            "Continuous telemetry monitoring should use which interaction pattern?",
            ["SEND", "REQUEST", "PUB-SUB", "INVOKE"],
            2,
        ),
        (
            "Which pattern returns an acknowledgement, progress updates, and a final response?",
            ["SUBMIT", "PROGRESS", "REQUEST", "SEND"],
            1,
        ),
        (
            "Submitting an action for execution maps naturally to which pattern?",
            ["SUBMIT", "SEND", "REQUEST", "PUB-SUB"],
            0,
        ),
    ],
    "3.2": [
        (
            "In CCSDS 522.1, a parameter's stable name is its…",
            ["Definition", "Identity", "Value", "Aggregation"],
            1,
        ),
        (
            "Why can MO consumers survive mid-mission database updates?",
            [
                "Subscribers hold identities, not row IDs",
                "The broker caches all historical values",
                "Definitions are immutable for the mission lifetime",
                "Consumers poll instead of subscribing",
            ],
            0,
        ),
    ],
    "3.3": [
        (
            "The Parameter service operation for continuous value monitoring is…",
            ["getValue", "setValue", "monitorValue", "listDefinition"],
            2,
        ),
        (
            "monitorValue is built on which MAL interaction pattern?",
            ["PUB-SUB", "REQUEST", "INVOKE", "SUBMIT"],
            0,
        ),
    ],
    "3.4": [
        (
            "Action execution reporting (staged progress then completion) uses…",
            ["SEND", "the PROGRESS pattern", "polling with REQUEST", "PUB-SUB only"],
            1,
        ),
        (
            "Before executing an action, a provider should check its…",
            ["preconditions", "archive retention policy", "encoding format", "cohort seat count"],
            0,
        ),
    ],
}

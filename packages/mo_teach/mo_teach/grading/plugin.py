"""Pytest plugin used inside graded runs.

Reference test suites tag tests with ``@pytest.mark.rubric("<category>")``
(untagged tests count as ``correctness``). When the ``MO_GRADE_RESULTS``
environment variable is set, per-test outcomes are written there as JSON at
session end; the grader parses that file to build the rubric.
"""

import json
import os
from typing import Any

_CATEGORIES: dict[str, str] = {}
_RESULTS: list[dict[str, Any]] = []


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers", "rubric(category): grading rubric category for this test"
    )


def pytest_collection_modifyitems(items: list[Any]) -> None:
    for item in items:
        marker = item.get_closest_marker("rubric")
        _CATEGORIES[item.nodeid] = marker.args[0] if marker else "correctness"


def pytest_runtest_logreport(report: Any) -> None:
    # One record per test: its call phase, or a failed/errored setup phase.
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        _RESULTS.append(
            {
                "id": report.nodeid,
                "category": _CATEGORIES.get(report.nodeid, "correctness"),
                "outcome": report.outcome,
            }
        )


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    path = os.environ.get("MO_GRADE_RESULTS")
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"tests": _RESULTS, "exitstatus": int(exitstatus)}, fh)

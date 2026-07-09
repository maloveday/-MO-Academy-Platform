"""Grade a lab submission against its reference test suite.

A lab directory looks like:

    lab-3-3/
      lab.json          — slug, lesson, title, rubric weights, pass threshold
      reference/        — pytest reference consumers (test_lab.py, ...)
      submission/       — starter template handed to students
      examples/passing/ — a known-good submission (harness self-test / demo)

Grading copies the student's submission files plus the reference tests into a
scratch workdir and runs pytest there with the rubric plugin enabled:

- ``subprocess`` mode: a fresh Python subprocess (dev/tests; NOT a security
  sandbox — student code runs with the API's privileges).
- ``docker`` mode: ``docker run --rm --network=none`` with CPU/memory limits
  in the ``mo-academy-grader`` image — the production sandbox.

The result is a rubric dict: per-category pass counts and weighted total.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import mo_teach

RESULTS_FILENAME = "_results.json"
CONFTEST = 'pytest_plugins = ["mo_teach.grading.plugin"]\n'


def _error_rubric(spec: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "lab": spec.get("slug", "unknown"),
        "title": spec.get("title", ""),
        "score": 0.0,
        "passed": False,
        "categories": {},
        "tests": [],
        "error": message,
    }


def _compute_rubric(
    spec: dict[str, Any], tests: list[dict[str, Any]]
) -> dict[str, Any]:
    weights: dict[str, float] = spec.get("weights", {})
    by_category: dict[str, dict[str, int]] = {}
    for test in tests:
        bucket = by_category.setdefault(
            test["category"], {"passed": 0, "total": 0}
        )
        bucket["total"] += 1
        if test["outcome"] == "passed":
            bucket["passed"] += 1

    categories: dict[str, Any] = {}
    weighted_sum = 0.0
    weight_total = 0.0
    for category, bucket in sorted(by_category.items()):
        weight = float(weights.get(category, 0.0))
        cat_score = bucket["passed"] / bucket["total"] if bucket["total"] else 0.0
        categories[category] = {
            "passed": bucket["passed"],
            "total": bucket["total"],
            "score": round(cat_score, 3),
            "weight": weight,
        }
        weighted_sum += weight * cat_score
        weight_total += weight

    score = weighted_sum / weight_total if weight_total else 0.0
    threshold = float(spec.get("pass_threshold", 0.7))
    return {
        "lab": spec["slug"],
        "title": spec.get("title", ""),
        "score": round(score, 3),
        "passed": score >= threshold,
        "pass_threshold": threshold,
        "categories": categories,
        "tests": tests,
        "error": None,
    }


def _run_subprocess(workdir: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["MO_GRADE_RESULTS"] = str(workdir / RESULTS_FILENAME)
    # Make mo_teach importable in the child even without an installed copy.
    mo_teach_parent = str(Path(mo_teach.__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (mo_teach_parent, env.get("PYTHONPATH", "")) if p
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_docker(
    workdir: Path, timeout: int, image: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--memory=512m",
            "--cpus=1",
            "--pids-limit=128",
            "--env",
            f"MO_GRADE_RESULTS=/grade/{RESULTS_FILENAME}",
            "--volume",
            f"{workdir}:/grade",
            "--workdir",
            "/grade",
            image,
            "python",
            "-m",
            "pytest",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def grade_submission(
    submission_dir: Path,
    lab_dir: Path,
    *,
    mode: str = "subprocess",
    timeout: int = 180,
    docker_image: str = "mo-academy-grader",
) -> dict[str, Any]:
    """Grade ``submission_dir`` against ``lab_dir``; returns the rubric dict."""
    lab_json = lab_dir / "lab.json"
    if not lab_json.exists():
        return _error_rubric({"slug": lab_dir.name}, f"no lab.json in {lab_dir}")
    spec: dict[str, Any] = json.loads(lab_json.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="mo-grade-") as tmp:
        workdir = Path(tmp)
        for filename in spec.get("submission_files", ["solution.py"]):
            source = Path(submission_dir) / filename
            if not source.exists():
                return _error_rubric(
                    spec, f"submission is missing required file {filename!r}"
                )
            shutil.copy(source, workdir / filename)
        for reference_file in sorted((lab_dir / "reference").iterdir()):
            if reference_file.is_file():
                shutil.copy(reference_file, workdir / reference_file.name)
        (workdir / "conftest.py").write_text(CONFTEST, encoding="utf-8")

        try:
            if mode == "docker":
                proc = _run_docker(workdir, timeout, docker_image)
            elif mode == "subprocess":
                proc = _run_subprocess(workdir, timeout)
            else:
                return _error_rubric(spec, f"unknown grader mode {mode!r}")
        except subprocess.TimeoutExpired:
            return _error_rubric(spec, f"grading timed out after {timeout}s")
        except FileNotFoundError as exc:
            return _error_rubric(spec, f"grader runtime unavailable: {exc}")

        results_path = workdir / RESULTS_FILENAME
        if not results_path.exists():
            tail = (proc.stdout + proc.stderr)[-2000:]
            return _error_rubric(
                spec, f"grader produced no results (exit {proc.returncode}):\n{tail}"
            )
        raw = json.loads(results_path.read_text(encoding="utf-8"))

    return _compute_rubric(spec, raw["tests"])

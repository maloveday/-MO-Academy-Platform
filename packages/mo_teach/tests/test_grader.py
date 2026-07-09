"""Grading harness self-test against the shipped labs."""

from pathlib import Path

from mo_teach.grading.grader import grade_submission

LABS_ROOT = Path(__file__).resolve().parents[3] / "labs"


def test_passing_submission_scores_full_marks_lab_33() -> None:
    lab = LABS_ROOT / "lab-3-3"
    rubric = grade_submission(lab / "examples" / "passing", lab)

    assert rubric["error"] is None
    assert rubric["lab"] == "lab-3-3"
    assert rubric["score"] == 1.0
    assert rubric["passed"] is True
    assert set(rubric["categories"]) == {
        "correctness",
        "pattern_usage",
        "entity_separation",
    }
    correctness = rubric["categories"]["correctness"]
    assert correctness["passed"] == correctness["total"] > 0


def test_passing_submission_scores_full_marks_lab_34() -> None:
    lab = LABS_ROOT / "lab-3-4"
    rubric = grade_submission(lab / "examples" / "passing", lab)
    assert rubric["error"] is None
    assert rubric["score"] == 1.0
    assert rubric["passed"] is True


def test_starter_template_fails_correctness_but_grades_cleanly() -> None:
    lab = LABS_ROOT / "lab-3-3"
    rubric = grade_submission(lab / "submission", lab)

    assert rubric["error"] is None
    assert rubric["passed"] is False
    assert rubric["categories"]["correctness"]["passed"] == 0
    # Static source checks still run against the template.
    assert rubric["categories"]["entity_separation"]["total"] > 0


def test_missing_submission_file_is_reported(tmp_path: Path) -> None:
    rubric = grade_submission(tmp_path, LABS_ROOT / "lab-3-3")
    assert rubric["passed"] is False
    assert "missing required file" in rubric["error"]


def test_unknown_lab_dir_is_reported(tmp_path: Path) -> None:
    rubric = grade_submission(tmp_path, tmp_path / "nope")
    assert rubric["passed"] is False
    assert "lab.json" in rubric["error"]

"""The grade CLI: exit codes, human output, JSON output."""

import json
from pathlib import Path

from mo_teach.grading.cli import main

LABS_ROOT = Path(__file__).resolve().parents[3] / "labs"


def test_cli_pass(tmp_path: Path, capsys) -> None:
    lab = LABS_ROOT / "lab-3-3"
    out_json = tmp_path / "rubric.json"
    code = main(
        [str(lab / "examples" / "passing"), "--lab", str(lab), "--json", str(out_json)]
    )
    assert code == 0

    printed = capsys.readouterr().out
    assert "lab-3-3" in printed
    assert "PASS" in printed

    rubric = json.loads(out_json.read_text())
    assert rubric["score"] == 1.0


def test_cli_fail_exit_code(capsys) -> None:
    lab = LABS_ROOT / "lab-3-4"
    code = main([str(lab / "submission"), "--lab", str(lab)])
    assert code == 1
    assert "FAIL" in capsys.readouterr().out

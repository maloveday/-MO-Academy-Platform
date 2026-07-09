"""``grade`` CLI: grade a submission directory against a lab.

    grade path/to/submission --lab labs/lab-3-3
    grade submission/ --lab labs/lab-3-4 --mode docker --json rubric.json
"""

import argparse
import json
import sys
from pathlib import Path

from mo_teach.grading.grader import grade_submission


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="grade", description="Grade a lab submission against its reference tests."
    )
    parser.add_argument(
        "submission_dir", type=Path, help="directory containing the student's files"
    )
    parser.add_argument(
        "--lab",
        type=Path,
        required=True,
        help="lab directory (contains lab.json and reference/)",
    )
    parser.add_argument(
        "--mode",
        choices=["subprocess", "docker"],
        default="subprocess",
        help="sandbox mode (docker is the production sandbox)",
    )
    parser.add_argument(
        "--timeout", type=int, default=180, help="grading timeout in seconds"
    )
    parser.add_argument(
        "--docker-image", default="mo-academy-grader", help="grader image for docker mode"
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="also write the rubric JSON to this path"
    )
    args = parser.parse_args(argv)

    rubric = grade_submission(
        args.submission_dir,
        args.lab,
        mode=args.mode,
        timeout=args.timeout,
        docker_image=args.docker_image,
    )

    if args.json:
        args.json.write_text(json.dumps(rubric, indent=2), encoding="utf-8")

    print(f"LAB {rubric['lab']} — {rubric.get('title', '')}")
    if rubric["error"]:
        print(f"ERROR: {rubric['error']}")
        return 2
    for name, cat in rubric["categories"].items():
        print(
            f"  {name:<20} {cat['passed']}/{cat['total']:<3}"
            f"  score {cat['score']:.2f}  (weight {cat['weight']:.2f})"
        )
    verdict = "PASS" if rubric["passed"] else "FAIL"
    print(f"TOTAL {rubric['score']:.2f}  {verdict}"
          f"  (threshold {rubric['pass_threshold']:.2f})")
    return 0 if rubric["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

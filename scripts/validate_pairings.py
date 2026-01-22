#!/usr/bin/env python3
"""
Validate that grouped problems and solutions have 1:1 id matches.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Set


def load_ids(path: Path) -> Set[str]:
    ids: Set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("id"):
                ids.add(obj["id"])
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", required=True, help="Grouped problems JSONL")
    ap.add_argument("--solutions", required=True, help="Grouped solutions JSONL")
    ap.add_argument("--report", default="", help="Optional report output JSON")
    args = ap.parse_args()

    problems_path = Path(args.problems)
    solutions_path = Path(args.solutions)

    problem_ids = load_ids(problems_path)
    solution_ids = load_ids(solutions_path)

    missing = sorted(problem_ids - solution_ids)
    extra = sorted(solution_ids - problem_ids)

    report = {
        "problems": str(problems_path),
        "solutions": str(solutions_path),
        "problem_count": len(problem_ids),
        "solution_count": len(solution_ids),
        "missing_in_solutions": missing,
        "extra_in_solutions": extra,
    }

    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"problems={len(problem_ids)} solutions={len(solution_ids)}")
    print(f"missing_in_solutions={len(missing)} extra_in_solutions={len(extra)}")
    if missing:
        print("missing_ids_sample:", missing[:10])
    if extra:
        print("extra_ids_sample:", extra[:10])

    return 0 if not missing and not extra else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Merge problem drafts with solution drafts using anchor matching.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def norm_anchor(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not path.exists():
        return items
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", required=True, help="Problem draft JSONL")
    ap.add_argument("--solutions", required=True, help="Solution draft JSONL")
    ap.add_argument("--out", required=True, help="Merged JSONL output")
    ap.add_argument("--rejects", default="", help="Unmatched problems JSONL")
    args = ap.parse_args()

    problems_path = Path(args.problems)
    solutions_path = Path(args.solutions)
    out_path = Path(args.out)
    rejects_path = Path(args.rejects) if args.rejects else out_path.with_suffix(".unmatched.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    problems = load_jsonl(problems_path)
    solutions = load_jsonl(solutions_path)

    by_anchor: Dict[str, List[Dict[str, Any]]] = {}
    for sol in solutions:
        anchor = ((sol.get("meta") or {}).get("anchor") or sol.get("anchor") or "").strip()
        if not anchor:
            continue
        key = norm_anchor(anchor)
        by_anchor.setdefault(key, []).append(sol)

    matched = 0
    unmatched = 0
    with out_path.open("w", encoding="utf-8") as f_out, rejects_path.open("w", encoding="utf-8") as f_rej:
        for prob in problems:
            answer = prob.get("answer")
            if answer:
                f_out.write(json.dumps(prob, ensure_ascii=False) + "\n")
                matched += 1
                continue

            anchor = ((prob.get("meta") or {}).get("anchor") or prob.get("anchor") or "").strip()
            key = norm_anchor(anchor) if anchor else ""
            candidates = by_anchor.get(key, [])

            chosen: Optional[Dict[str, Any]] = None
            if candidates:
                if len(candidates) == 1:
                    chosen = candidates[0]
                else:
                    # Prefer exact source/year match when multiple candidates exist.
                    for cand in candidates:
                        if cand.get("source") == prob.get("source") and cand.get("year") == prob.get("year"):
                            chosen = cand
                            break
                    if not chosen:
                        chosen = candidates[0]

            if chosen and chosen.get("answer"):
                prob["answer"] = chosen.get("answer")
                prob_meta = prob.setdefault("meta", {})
                prob_meta["solution_anchor"] = ((chosen.get("meta") or {}).get("anchor") or chosen.get("anchor") or "")
                f_out.write(json.dumps(prob, ensure_ascii=False) + "\n")
                matched += 1
            else:
                f_rej.write(json.dumps(prob, ensure_ascii=False) + "\n")
                unmatched += 1

    print(f"matched={matched} unmatched={unmatched}")
    print(f"out={out_path}")
    print(f"unmatched={rejects_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

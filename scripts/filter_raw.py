#!/usr/bin/env python3
"""
Filter raw PDF-extracted JSONL pages to likely problem content.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PROBLEM_SKIP_PHRASES = [
    "solutions",
    "solution and marking",
    "solution",
    "answer key",
    "answers",
    "scoring",
    "marking scheme",
    "rules for writing out the solutions",
    "do not copy the problems",
    "registration #",
]

PROBLEM_KEEP_HINTS = [
    "problem",
    "question",
    "task",
    "translate",
    "match",
    "choose",
    "multiple choice",
]

SOLUTION_KEEP_HINTS = [
    "solution",
    "solutions",
    "answer key",
    "answers",
    "marking",
    "scoring",
]

def should_skip(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in PROBLEM_SKIP_PHRASES)


def should_keep(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in PROBLEM_KEEP_HINTS)


def should_keep_solution(text: str, filename: str) -> bool:
    t = text.lower()
    f = filename.lower()
    return any(p in t for p in SOLUTION_KEEP_HINTS) or "sol" in f or "solution" in f


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input raw JSONL")
    ap.add_argument("--out", dest="out_path", required=True, help="Output filtered JSONL")
    ap.add_argument("--mode", choices=["problems", "solutions", "all"], default="problems", help="Filter mode")
    ap.add_argument("--min-text", type=int, default=80, help="Minimum text length to keep")
    ap.add_argument("--require-keep-hint", action="store_true", help="Require keep-hint phrase (problems mode)")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    kept = skipped = 0
    with in_path.open("r", encoding="utf-8") as f_in, out_path.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            obj = json.loads(line)
            text = (obj.get("text") or "").strip()
            tables = obj.get("tables") or []
            filename = (obj.get("file") or "")
            if not text and not tables:
                skipped += 1
                continue
            if len(text) < args.min_text and not tables:
                skipped += 1
                continue
            if args.mode == "problems":
                if text and should_skip(text):
                    skipped += 1
                    continue
                if args.require_keep_hint and text and not should_keep(text):
                    skipped += 1
                    continue
            elif args.mode == "solutions":
                if text and not should_keep_solution(text, filename):
                    skipped += 1
                    continue
            f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            kept += 1

    print(f"kept={kept} skipped={skipped} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


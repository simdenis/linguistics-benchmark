#!/usr/bin/env python3
"""
Validate a reject log CSV for excluded PDF/pages.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


ALLOWED_SOURCES = {"IOL", "NACLO", "UKLO"}
ALLOWED_REASONS = {
    "non_latin_script",
    "image_only_scan",
    "low_quality_ocr",
    "non_autogradable",
    "missing_options",
    "multi_step_reasoning",
    "non_language_topic",
    "other",
}
REQUIRED_FIELDS = {"source", "year", "file", "page", "reason", "notes"}


def err(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="docs/reject_log.csv", help="Path to reject log CSV")
    ap.add_argument("--min-year", type=int, default=2010, help="Minimum year allowed")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        err(f"file not found: {path}")
        return 2

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            err("missing header row")
            return 2
        fields = {name.strip() for name in reader.fieldnames if name}
        missing = REQUIRED_FIELDS - fields
        extra = fields - REQUIRED_FIELDS
        if missing:
            err(f"missing fields: {sorted(missing)}")
        if extra:
            err(f"unexpected fields: {sorted(extra)}")
        if missing or extra:
            return 2

        rows = 0
        bad = 0
        for i, row in enumerate(reader, start=2):
            rows += 1
            source = (row.get("source") or "").strip()
            year_s = (row.get("year") or "").strip()
            file_s = (row.get("file") or "").strip()
            page_s = (row.get("page") or "").strip()
            reason = (row.get("reason") or "").strip()

            if source not in ALLOWED_SOURCES:
                err(f"row {i}: invalid source '{source}'")
                bad += 1
            try:
                year = int(year_s)
                if year < args.min_year:
                    err(f"row {i}: year {year} < {args.min_year}")
                    bad += 1
            except ValueError:
                err(f"row {i}: invalid year '{year_s}'")
                bad += 1

            if not file_s:
                err(f"row {i}: missing file")
                bad += 1

            if not page_s:
                err(f"row {i}: missing page")
                bad += 1

            if reason not in ALLOWED_REASONS:
                err(f"row {i}: invalid reason '{reason}'")
                bad += 1

        if bad:
            err(f"{bad} issue(s) found in {rows} rows")
            return 2

    print(f"ok: {rows} row(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

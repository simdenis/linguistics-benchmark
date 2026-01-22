#!/usr/bin/env python3
"""
Extract raw text + tables from PDFs into JSONL (one line per page).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except Exception as exc:  # pragma: no cover - optional dependency
    pdfplumber = None
    _IMPORT_ERR = exc


def err(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def parse_year(name: str) -> Optional[int]:
    m = re.search(r"(19|20)\d{2}", name)
    if m:
        return int(m.group(0))
    return None


def load_reject_log(path: Optional[str]) -> set[tuple[str, str, int]]:
    if not path:
        return set()
    p = Path(path)
    if not p.exists():
        err(f"reject log not found: {p}")
        return set()
    rows: set[tuple[str, str, int]] = set()
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = (row.get("source") or "").strip().upper()
            file_s = (row.get("file") or "").strip()
            page_s = (row.get("page") or "").strip()
            if not source or not file_s or not page_s:
                continue
            try:
                page = int(page_s)
            except ValueError:
                continue
            rows.add((source, file_s, page))
    return rows


def default_in_dir(source: str) -> Path:
    merged = Path(f"data/{source.lower()}_pdfs_merged")
    if merged.exists():
        return merged
    return Path(f"data/{source.lower()}_pdfs")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["iol", "naclo", "uklo"], required=True, help="Competition source")
    ap.add_argument("--in-dir", default="", help="Root directory containing PDFs")
    ap.add_argument("--out", default="", help="Output JSONL path")
    ap.add_argument("--min-year", type=int, default=2010, help="Minimum year to include")
    ap.add_argument("--max-pages", type=int, default=0, help="Max pages per PDF (0 = no limit)")
    ap.add_argument("--reject-log", default="docs/reject_log.csv", help="CSV of pages to skip")
    args = ap.parse_args()

    if pdfplumber is None:
        err(f"pdfplumber is required: {_IMPORT_ERR}")
        err("install with: python -m pip install pdfplumber")
        return 2

    source = args.source.upper()
    in_dir = Path(args.in_dir) if args.in_dir else default_in_dir(args.source)
    if not in_dir.exists():
        err(f"input directory not found: {in_dir}")
        return 2

    out_path = Path(args.out) if args.out else Path(f"data/raw/{args.source}_raw.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    reject = load_reject_log(args.reject_log)

    pdfs = sorted([p for p in in_dir.rglob("*.pdf") if p.is_file()])
    total_pages = 0
    with out_path.open("w", encoding="utf-8") as out_f:
        for pdf_path in pdfs:
            year = parse_year(pdf_path.name)
            if year is not None and year < args.min_year:
                continue
            try:
                with pdfplumber.open(str(pdf_path)) as pdf:
                    for idx, page in enumerate(pdf.pages, start=1):
                        if args.max_pages and idx > args.max_pages:
                            break
                        if (source, pdf_path.name, idx) in reject:
                            continue
                        text = page.extract_text() or ""
                        tables = page.extract_tables() or []
                        rec = {
                            "source": source,
                            "year": year,
                            "file": pdf_path.name,
                            "page": idx,
                            "text": text,
                            "tables": tables,
                            "meta": {
                                "path": str(pdf_path),
                            },
                        }
                        out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        total_pages += 1
            except Exception as exc:
                err(f"failed to read {pdf_path}: {exc}")

    print(f"Wrote {total_pages} page(s) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

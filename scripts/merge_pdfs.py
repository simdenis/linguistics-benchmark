#!/usr/bin/env python3
"""
Merge problem+solution PDFs into combined files for NACLO and IOL.
Keeps originals; writes merged PDFs to an output directory.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except Exception as exc:  # pragma: no cover - optional dependency
    PdfReader = None
    PdfWriter = None
    _IMPORT_ERR = exc


def err(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def iter_pdfs(root: Path) -> list[Path]:
    return sorted([p for p in root.rglob("*.pdf") if p.is_file()])


def naclo_pairs(files: list[Path]) -> list[tuple[Path, Path, str]]:
    by_name = {p.name: p for p in files}
    pairs: list[tuple[Path, Path, str]] = []
    for name, prob_path in by_name.items():
        if not name.lower().endswith(".pdf"):
            continue
        if name[-5:-4].lower() == "s" and name[-4:].lower() == ".pdf":
            # This is a solution file, skip here; we'll pair from the problem side.
            continue
        sol_name = name[:-4] + "S.pdf"
        sol_path = by_name.get(sol_name)
        if sol_path:
            out_name = name[:-4] + "_merged.pdf"
            pairs.append((prob_path, sol_path, out_name))
    return pairs


def iol_pairs(files: list[Path]) -> list[tuple[Path, Path, str]]:
    by_name = {p.name: p for p in files}
    pairs: list[tuple[Path, Path, str]] = []
    for name, prob_path in by_name.items():
        if "-prob." not in name:
            continue
        sol_name = name.replace("-prob.", "-sol.")
        sol_path = by_name.get(sol_name)
        if not sol_path:
            sol_name = name.replace("-prob.", "-solutions.")
            sol_path = by_name.get(sol_name)
        if sol_path:
            out_name = re.sub(r"-prob\.", "-merged.", name)
            pairs.append((prob_path, sol_path, out_name))
    return pairs


def merge_pair(prob_path: Path, sol_path: Path, out_path: Path, overwrite: bool) -> str:
    if out_path.exists() and not overwrite:
        return "skip"
    writer = PdfWriter()
    for src in (prob_path, sol_path):
        reader = PdfReader(str(src))
        for page in reader.pages:
            writer.add_page(page)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        writer.write(f)
    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["iol", "naclo"], help="Competition source")
    ap.add_argument("--in-dir", help="Root directory containing PDFs")
    ap.add_argument("--out-dir", default="", help="Output directory for merged PDFs")
    ap.add_argument("--all", action="store_true", help="Merge both IOL and NACLO with defaults")
    ap.add_argument("--iol-dir", default="data/iol_pdfs", help="IOL input directory (for --all)")
    ap.add_argument("--naclo-dir", default="data/naclo_pdfs", help="NACLO input directory (for --all)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite merged PDFs if they exist")
    ap.add_argument("--dry-run", action="store_true", help="Print pairs, do not write PDFs")
    args = ap.parse_args()

    if PdfReader is None or PdfWriter is None:
        err(f"pypdf is required: {_IMPORT_ERR}")
        return 2

    def run_one(source: str, in_dir: Path, out_dir: Path) -> tuple[int, int, int]:
        if not in_dir.exists():
            err(f"input directory not found: {in_dir}")
            return 0, 0, 1
        files = iter_pdfs(in_dir)
        pairs = naclo_pairs(files) if source == "naclo" else iol_pairs(files)
        if not pairs:
            print(f"{source}: no pairs found.")
            return 0, 0, 0
        ok = skip = fail = 0
        for prob_path, sol_path, out_name in pairs:
            out_path = out_dir / out_name
            if args.dry_run:
                print(f"{source} pair: {prob_path} + {sol_path} -> {out_path}")
                continue
            try:
                status = merge_pair(prob_path, sol_path, out_path, args.overwrite)
                if status == "ok":
                    ok += 1
                else:
                    skip += 1
                print(f"{source} {status:4s} {out_path}")
            except Exception as exc:
                fail += 1
                err(f"{source} failed to merge {prob_path} + {sol_path}: {exc}")
        return ok, skip, fail

    if args.all:
        total_ok = total_skip = total_fail = 0
        for source, in_dir in (("iol", Path(args.iol_dir)), ("naclo", Path(args.naclo_dir))):
            out_dir = Path(args.out_dir) if args.out_dir else Path(f"{str(in_dir).rstrip('/')}_merged")
            ok, skip, fail = run_one(source, in_dir, out_dir)
            total_ok += ok
            total_skip += skip
            total_fail += fail
        if args.dry_run:
            return 0
        print(f"Done. ok={total_ok}, skip={total_skip}, fail={total_fail}")
        return 0 if total_fail == 0 else 2

    if not args.source or not args.in_dir:
        err("--source and --in-dir are required unless --all is used")
        return 2

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir) if args.out_dir else Path(f"{args.in_dir.rstrip('/')}_merged")
    ok, skip, fail = run_one(args.source, in_dir, out_dir)
    if args.dry_run:
        return 0
    print(f"Done. ok={ok}, skip={skip}, fail={fail}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

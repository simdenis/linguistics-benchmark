#!/usr/bin/env python3
"""
Extract problems and solutions in one pass and assign shared pair_id values.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SYSTEM_PROMPT = """You extract auto-gradable subproblems and solutions from linguistics olympiad PDFs.
Output strict JSON only, with schema:
{
  "items": [
    {
      "kind": "problem" | "solution",
      "task_type": "matching" | "mcq" | "short_text",
      "prompt": "...",
      "answer": "... or JSON object for matching",
      "output_spec": {...},
      "anchor": "short title or unique snippet"
    }
  ]
}

Rules:
- Extract all auto-gradable items you can find. Err on the side of extracting.
- Auto-gradable types: matching, MCQ (single-letter), short exact answers (single word/phrase/number).
- If this page contains a problem statement, output kind="problem" with its prompt.
- If this page contains a solution/answer key, output kind="solution" with its answer.
- When solutions list only answers with labels (e.g., 1a, A-D), still extract as solution items.
- Use the same anchor for problem/solution pairs when possible. Prefer anchors from headings or the first line.
- Keep prompt minimal but sufficient (include tables/wordlists/options).
- Use ASCII only.

Important:
- If you see a list of subparts (a),(b),(c) on the same task, output separate items but reuse the same anchor.
- If a page mixes problems and solutions, output both kinds for the relevant parts.
"""


MODE_HINTS = {
    "problems": "This page is likely a PROBLEM page.",
    "solutions": "This page is likely a SOLUTION page.",
    "all": "This page may include problems or solutions.",
}


def build_output_spec(task_type: str) -> Dict[str, Any]:
    if task_type == "matching":
        return {"type": "matching", "format": "json", "key_type": "str", "value_type": "str"}
    if task_type == "mcq":
        return {"type": "mcq", "format": "letter"}
    return {"type": "short_text", "normalize": "lower,strip,space"}


def norm_anchor(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\\s+", " ", s).strip()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s


def run_ollama(model: str, payload: Dict[str, Any]) -> str:
    prompt = SYSTEM_PROMPT + "\\n\\n" + MODE_HINTS[payload["mode"]] + "\\n\\n" + json.dumps(payload["data"])
    proc = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ollama run failed")
    return proc.stdout


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def make_pair_id(source: str, year: Any, seq: int) -> str:
    return f"{source.lower()}-{year or 'unknown'}-{seq}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input raw JSONL")
    ap.add_argument("--problems-out", required=True, help="Problems JSONL output")
    ap.add_argument("--solutions-out", required=True, help="Solutions JSONL output")
    ap.add_argument("--rejects", default="", help="Rejects JSONL output")
    ap.add_argument("--model", default="qwen2.5:14b", help="Ollama model")
    ap.add_argument("--mode", choices=["problems", "solutions", "all"], default="all", help="Extraction mode hint")
    ap.add_argument("--max-pages", type=int, default=0, help="Max pages to process (0 = all)")
    ap.add_argument("--max-chars", type=int, default=0, help="Max characters of page text to send (0 = no limit)")
    ap.add_argument("--resume", action="store_true", help="Skip pages already processed in outputs/rejects")
    ap.add_argument("--sleep", type=float, default=0.2, help="Sleep between requests")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    problems_out = Path(args.problems_out)
    solutions_out = Path(args.solutions_out)
    rejects_path = Path(args.rejects) if args.rejects else problems_out.with_suffix(".rejects.jsonl")
    problems_out.parent.mkdir(parents=True, exist_ok=True)
    solutions_out.parent.mkdir(parents=True, exist_ok=True)

    seen_pages = set()
    if args.resume:
        for path in (problems_out, solutions_out, rejects_path):
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        meta = obj.get("meta") or {}
                        key = (
                            obj.get("source") or meta.get("source"),
                            meta.get("file"),
                            meta.get("page"),
                        )
                        if all(key):
                            seen_pages.add(tuple(key))
                    except Exception:
                        continue

    # (source, year) -> {anchor_norm: pair_id}, seq counter
    pair_map: Dict[Tuple[Any, Any], Dict[str, str]] = {}
    pair_seq: Dict[Tuple[Any, Any], int] = {}

    total = kept = rejected = 0
    out_mode = "a" if args.resume else "w"
    rej_mode = "a" if args.resume else "w"
    with in_path.open("r", encoding="utf-8") as f_in, \
        problems_out.open(out_mode, encoding="utf-8") as f_prob, \
        solutions_out.open(out_mode, encoding="utf-8") as f_sol, \
        rejects_path.open(rej_mode, encoding="utf-8") as f_rej:
        for line in f_in:
            total += 1
            if args.max_pages and total > args.max_pages:
                break
            obj = json.loads(line)
            key_page = (obj.get("source"), obj.get("file"), obj.get("page"))
            if args.resume and key_page in seen_pages:
                continue
            text = obj.get("text") or ""
            if args.max_chars and len(text) > args.max_chars:
                text = text[: args.max_chars]
            payload = {
                "mode": args.mode,
                "data": {
                    "hint": MODE_HINTS[args.mode],
                    "source": obj.get("source"),
                    "year": obj.get("year"),
                    "file": obj.get("file"),
                    "page": obj.get("page"),
                    "text": text,
                    "tables": obj.get("tables") or [],
                },
            }
            try:
                raw = run_ollama(args.model, payload)
                parsed = extract_json(raw)
                if not parsed or "items" not in parsed:
                    f_rej.write(json.dumps({"payload": payload["data"], "error": "no_items"}) + "\n")
                    rejected += 1
                else:
                    items = parsed.get("items", [])
                    if not items:
                        f_rej.write(json.dumps({"payload": payload["data"], "error": "empty_items"}) + "\n")
                        rejected += 1
                    else:
                        source = obj.get("source")
                        year = obj.get("year")
                        group_key = (source, year)
                        anchor_to_pair = pair_map.setdefault(group_key, {})
                        seq = pair_seq.get(group_key, 0)
                        for idx, it in enumerate(items, start=1):
                            kind = (it.get("kind") or "").strip()
                            task_type = (it.get("task_type") or "").strip()
                            if kind not in ("problem", "solution"):
                                continue
                            if task_type not in ("matching", "mcq", "short_text"):
                                continue
                            output_spec = it.get("output_spec") or build_output_spec(task_type)
                            anchor_raw = (it.get("anchor") or "").strip()
                            anchor_norm = norm_anchor(anchor_raw) or f"noanchor-{obj.get('file')}-p{obj.get('page')}-i{idx}"
                            pair_id = anchor_to_pair.get(anchor_norm)
                            if not pair_id:
                                seq += 1
                                pair_id = make_pair_id(source, year, seq)
                                anchor_to_pair[anchor_norm] = pair_id
                            rec = {
                                "id": pair_id,
                                "source": source,
                                "year": year,
                                "task_type": task_type,
                                "prompt": (it.get("prompt") or "").strip(),
                                "answer": it.get("answer"),
                                "output_spec": output_spec,
                                "meta": {
                                    "file": obj.get("file"),
                                    "page": obj.get("page"),
                                    "anchor": anchor_raw,
                                    "anchor_norm": anchor_norm,
                                },
                            }
                            if kind == "problem":
                                f_prob.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            else:
                                f_sol.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            kept += 1
                        pair_seq[group_key] = seq
            except Exception as exc:
                f_rej.write(json.dumps({"payload": payload["data"], "error": str(exc)}) + "\n")
                rejected += 1
            time.sleep(args.sleep)

    print(f"processed_pages={total} kept_items={kept} rejected_pages={rejected}")
    print(f"problems_out={problems_out}")
    print(f"solutions_out={solutions_out}")
    print(f"rejects={rejects_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

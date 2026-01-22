#!/usr/bin/env python3
"""
Use a local Ollama model to extract structured subproblems from filtered JSONL pages.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


SYSTEM_PROMPT = """You extract auto-gradable subproblems from linguistics olympiad PDFs.
Output strict JSON only, with schema:
{
  "items": [
    {
      "task_type": "matching" | "mcq" | "short_text",
      "prompt": "...",
      "answer": "... or JSON object for matching",
      "output_spec": {...},
      "anchor": "short title or unique snippet",
      "needs_solution": true|false
    }
  ]
}

Rules:
- Only extract if it is clearly auto-gradable (matching, MCQ, short exact answer).
- If the page does NOT include the answer, set needs_solution=true and answer=null.
- Keep prompt minimal but sufficient (include tables/wordlists/options).
- Use ASCII only.
"""


MODE_HINTS = {
    "problems": "This page is likely a PROBLEM page. Extract prompts; answers may be missing.",
    "solutions": "This page is likely a SOLUTION page. Extract answers and anchors; prompts may be missing.",
    "all": "This page may include problems or solutions. Extract what you can.",
}


def build_output_spec(task_type: str) -> Dict[str, Any]:
    if task_type == "matching":
        return {"type": "matching", "format": "json", "key_type": "str", "value_type": "str"}
    if task_type == "mcq":
        return {"type": "mcq", "format": "letter"}
    return {"type": "short_text", "normalize": "lower,strip,space"}


def postprocess_items(items: List[Dict[str, Any]], meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for idx, it in enumerate(items, start=1):
        task_type = (it.get("task_type") or "").strip()
        if task_type not in ("matching", "mcq", "short_text"):
            continue
        output_spec = it.get("output_spec") or build_output_spec(task_type)
        rec = {
            "id": f"{meta['source'].lower()}-{meta['year'] or 'unknown'}-{meta['file']}-p{meta['page']}-i{idx}",
            "source": meta["source"],
            "year": meta["year"],
            "task_type": task_type,
            "prompt": (it.get("prompt") or "").strip(),
            "answer": it.get("answer"),
            "output_spec": output_spec,
            "meta": {
                "file": meta["file"],
                "page": meta["page"],
                "anchor": (it.get("anchor") or "").strip(),
                "needs_solution": bool(it.get("needs_solution")),
            },
        }
        out.append(rec)
    return out


def run_ollama(model: str, payload: Dict[str, Any]) -> str:
    prompt = SYSTEM_PROMPT + "\n\n" + MODE_HINTS[payload["mode"]] + "\n\n" + json.dumps(payload["data"])
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input filtered JSONL")
    ap.add_argument("--out", dest="out_path", required=True, help="Output structured JSONL")
    ap.add_argument("--rejects", default="", help="Rejects JSONL output")
    ap.add_argument("--model", default="qwen2.5:14b", help="Ollama model")
    ap.add_argument("--mode", choices=["problems", "solutions", "all"], default="problems", help="Extraction mode hint")
    ap.add_argument("--max-pages", type=int, default=0, help="Max pages to process (0 = all)")
    ap.add_argument("--max-chars", type=int, default=0, help="Max characters of page text to send (0 = no limit)")
    ap.add_argument("--resume", action="store_true", help="Skip pages already processed in output/rejects")
    ap.add_argument("--sleep", type=float, default=0.2, help="Sleep between requests")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    rejects_path = Path(args.rejects) if args.rejects else out_path.with_suffix(".rejects.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seen_pages = set()
    if args.resume:
        for path in (out_path, rejects_path):
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        meta = obj.get("meta") or {}
                        key = (
                            obj.get("source") or meta.get("source"),
                            obj.get("file") or meta.get("file"),
                            obj.get("page") or meta.get("page"),
                        )
                        if all(key):
                            seen_pages.add(tuple(key))
                    except Exception:
                        continue

    total = kept = rejected = 0
    out_mode = "a" if args.resume else "w"
    rej_mode = "a" if args.resume else "w"
    with in_path.open("r", encoding="utf-8") as f_in, out_path.open(out_mode, encoding="utf-8") as f_out, rejects_path.open(rej_mode, encoding="utf-8") as f_rej:
        for line in f_in:
            total += 1
            if args.max_pages and total > args.max_pages:
                break
            obj = json.loads(line)
            key = (obj.get("source"), obj.get("file"), obj.get("page"))
            if args.resume and key in seen_pages:
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
                    items = postprocess_items(parsed.get("items", []), payload["data"])
                    if not items:
                        f_rej.write(json.dumps({"payload": payload["data"], "error": "empty_items"}) + "\n")
                        rejected += 1
                    else:
                        for it in items:
                            f_out.write(json.dumps(it, ensure_ascii=False) + "\n")
                            kept += 1
            except Exception as exc:
                f_rej.write(json.dumps({"payload": payload["data"], "error": str(exc)}) + "\n")
                rejected += 1
            time.sleep(args.sleep)

    print(f"processed_pages={total} kept_items={kept} rejected_pages={rejected}")
    print(f"out={out_path}")
    print(f"rejects={rejects_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

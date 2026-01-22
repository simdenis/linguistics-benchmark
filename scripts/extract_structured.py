#!/usr/bin/env python3
"""
Use OpenAI to extract structured subproblems from filtered JSONL pages.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


API_URL = "https://api.openai.com/v1/responses"


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


def call_openai(api_key: str, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
    }
    resp = requests.post(API_URL, headers=headers, data=json.dumps(body), timeout=120)
    if not resp.ok:
        raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")
    return resp.json()


def extract_json_from_response(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text += content.get("text", "")
    if not text:
        return None
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
    ap.add_argument("--model", default="gpt-5-mini", help="OpenAI model")
    ap.add_argument("--mode", choices=["problems", "solutions", "all"], default="problems", help="Extraction mode hint")
    ap.add_argument("--max-pages", type=int, default=0, help="Max pages to process (0 = all)")
    ap.add_argument("--sleep", type=float, default=0.4, help="Sleep between requests")
    args = ap.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("error: OPENAI_API_KEY is not set", file=sys.stderr)
        return 2

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    rejects_path = Path(args.rejects) if args.rejects else out_path.with_suffix(".rejects.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = kept = rejected = 0
    with in_path.open("r", encoding="utf-8") as f_in, out_path.open("w", encoding="utf-8") as f_out, rejects_path.open("w", encoding="utf-8") as f_rej:
        for line in f_in:
            total += 1
            if args.max_pages and total > args.max_pages:
                break
            obj = json.loads(line)
            payload = {
                "hint": MODE_HINTS[args.mode],
                "source": obj.get("source"),
                "year": obj.get("year"),
                "file": obj.get("file"),
                "page": obj.get("page"),
                "text": obj.get("text") or "",
                "tables": obj.get("tables") or [],
            }
            try:
                data = call_openai(api_key, args.model, payload)
                parsed = extract_json_from_response(data)
                if not parsed or "items" not in parsed:
                    f_rej.write(json.dumps({"payload": payload, "error": "no_items"}) + "\n")
                    rejected += 1
                else:
                    items = postprocess_items(parsed.get("items", []), payload)
                    if not items:
                        f_rej.write(json.dumps({"payload": payload, "error": "empty_items"}) + "\n")
                        rejected += 1
                    else:
                        for it in items:
                            f_out.write(json.dumps(it, ensure_ascii=False) + "\n")
                            kept += 1
            except Exception as exc:
                f_rej.write(json.dumps({"payload": payload, "error": str(exc)}) + "\n")
                rejected += 1
            time.sleep(args.sleep)

    print(f"processed_pages={total} kept_items={kept} rejected_pages={rejected}")
    print(f"out={out_path}")
    print(f"rejects={rejects_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

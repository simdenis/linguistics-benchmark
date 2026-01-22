#!/usr/bin/env python3
"""
Group structured items by source+file+page+anchor and emit grouped JSONL.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def norm_anchor(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def make_pair_id(item: Dict[str, Any], anchor_norm: str) -> str:
    meta = item.get("meta") or {}
    source = (item.get("source") or meta.get("source") or "unknown").lower()
    year = item.get("year") or meta.get("year") or "unknown"
    file = meta.get("file") or "unknown"
    page = meta.get("page") or "unknown"
    anchor_part = anchor_norm or f"noanchor-{item.get('id') or 'unknown'}"
    return f"{source}-{year}-{file}-p{page}-a{anchor_part}"


def combine_prompts(items: List[Dict[str, Any]]) -> str:
    if len(items) == 1:
        return items[0].get("prompt") or ""
    parts = []
    for idx, it in enumerate(items, start=1):
        prompt = (it.get("prompt") or "").strip()
        if not prompt:
            continue
        parts.append(f"Part {idx}:\n{prompt}")
    return "\n\n".join(parts)


def combine_output_spec(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(items) == 1:
        return items[0].get("output_spec") or {}
    return {
        "type": "list",
        "items": [it.get("output_spec") or {} for it in items],
    }


def combine_answers(items: List[Dict[str, Any]]) -> Any:
    if len(items) == 1:
        return items[0].get("answer")
    return [it.get("answer") for it in items]


def group_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    anchor_map: Dict[Tuple[Any, ...], str] = {}
    for it in items:
        meta = it.get("meta") or {}
        anchor_raw = (meta.get("anchor") or it.get("anchor") or "").strip()
        anchor_norm = norm_anchor(anchor_raw)
        key = (
            it.get("source") or meta.get("source"),
            it.get("year") or meta.get("year"),
            meta.get("file"),
            meta.get("page"),
            anchor_norm or f"noanchor-{it.get('id') or 'unknown'}",
        )
        grouped.setdefault(key, []).append(it)
        anchor_map[key] = anchor_raw

    out: List[Dict[str, Any]] = []
    for key, group in grouped.items():
        first = group[0]
        meta = first.get("meta") or {}
        anchor_raw = anchor_map.get(key, "")
        anchor_norm = norm_anchor(anchor_raw)
        pair_id = make_pair_id(first, anchor_norm)
        task_types = {it.get("task_type") for it in group if it.get("task_type")}
        rec = {
            "id": pair_id,
            "source": first.get("source"),
            "year": first.get("year"),
            "task_type": task_types.pop() if len(task_types) == 1 else "composite",
            "prompt": combine_prompts(group),
            "answer": combine_answers(group),
            "output_spec": combine_output_spec(group),
            "items": [
                {
                    "id": it.get("id"),
                    "task_type": it.get("task_type"),
                    "prompt": it.get("prompt"),
                    "answer": it.get("answer"),
                    "output_spec": it.get("output_spec"),
                }
                for it in group
            ],
            "meta": {
                "file": meta.get("file"),
                "page": meta.get("page"),
                "anchor": anchor_raw,
                "anchor_norm": anchor_norm,
            },
        }
        out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input structured JSONL")
    ap.add_argument("--out", dest="out_path", required=True, help="Output grouped JSONL")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    items = list(load_jsonl(in_path))
    grouped = group_items(items)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in grouped:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"grouped={len(grouped)} out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

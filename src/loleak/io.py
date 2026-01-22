from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class Example:
    """One auto-gradable subproblem."""

    id: str
    source: str
    year: Optional[int]
    task_type: str
    prompt: str
    answer: Any
    output_spec: Dict[str, Any]
    meta: Dict[str, Any]


def read_jsonl(path: str | Path) -> Iterator[Dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_no} of {path}: {e}") from e


def write_jsonl(path: str | Path, rows: List[Dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_examples(path: str | Path) -> List[Example]:
    examples: List[Example] = []
    for row in read_jsonl(path):
        missing = [k for k in ("id", "source", "task_type", "prompt", "answer", "output_spec") if k not in row]
        if missing:
            raise ValueError(f"Example missing required fields {missing}: {row.get('id', '<no id>')}")
        year = row.get("year")
        year_int: Optional[int] = None
        if year is not None:
            try:
                year_int = int(year)
            except Exception as e:
                raise ValueError(f"Invalid year for example {row['id']}: {year}") from e

        output_spec = row["output_spec"]
        if not isinstance(output_spec, dict):
            raise ValueError(f"output_spec must be an object for example {row['id']}")

        meta = row.get("meta", {})
        if meta is None:
            meta = {}
        if not isinstance(meta, dict):
            raise ValueError(f"meta must be an object for example {row['id']}")

        examples.append(
            Example(
                id=str(row["id"]),
                source=str(row["source"]),
                year=year_int,
                task_type=str(row["task_type"]),
                prompt=str(row["prompt"]),
                answer=row["answer"],
                output_spec=output_spec,
                meta=meta,
            )
        )
    return examples

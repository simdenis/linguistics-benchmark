from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tqdm import tqdm

from .grade import parse_prediction, score_example
from .io import Example, load_examples


def _read_run_output(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate stored model outputs.")
    ap.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    ap.add_argument("--rundir", required=True, help="Directory containing model subdirs")
    ap.add_argument("--report", required=True, help="Where to write report JSON")
    ap.add_argument("--include_details", action="store_true", help="Include per-example details")
    args = ap.parse_args()

    examples = load_examples(Path(args.dataset))
    ex_by_id = {ex.id: ex for ex in examples}

    rundir = Path(args.rundir)
    model_dirs = [p for p in rundir.iterdir() if p.is_dir()]
    model_dirs.sort(key=lambda p: p.name)

    report: Dict[str, Any] = {
        "dataset": str(args.dataset),
        "rundir": str(args.rundir),
        "models": {},
    }

    for mdir in model_dirs:
        model_name = mdir.name
        per_task_scores: Dict[str, List[float]] = defaultdict(list)
        per_source_scores: Dict[str, List[float]] = defaultdict(list)
        per_year_scores: Dict[str, List[float]] = defaultdict(list)
        scores: List[float] = []
        details: List[Dict[str, Any]] = []

        out_files = sorted(mdir.glob("*.json"))
        for f in tqdm(out_files, desc=f"eval {model_name}"):
            run = _read_run_output(f)
            ex_id = run.get("example_id")
            if ex_id not in ex_by_id:
                continue
            ex: Example = ex_by_id[ex_id]

            pred = parse_prediction(ex, run.get("response", ""))
            s, info = score_example(ex, pred)

            scores.append(s)
            per_task_scores[ex.task_type].append(s)
            per_source_scores[ex.source].append(s)
            per_year_scores[str(ex.year) if ex.year is not None else "unknown"].append(s)

            if args.include_details:
                details.append(
                    {
                        "id": ex.id,
                        "source": ex.source,
                        "year": ex.year,
                        "task_type": ex.task_type,
                        "score": s,
                        "parse": pred,
                        "info": info,
                    }
                )

        def avg(xs: List[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        model_entry: Dict[str, Any] = {
            "n": len(scores),
            "accuracy": avg(scores),
            "by_task": {k: avg(v) for k, v in per_task_scores.items()},
            "by_source": {k: avg(v) for k, v in per_source_scores.items()},
            "by_year": {k: avg(v) for k, v in per_year_scores.items()},
        }
        if args.include_details:
            model_entry["details"] = details

        report["models"][model_name] = model_entry

    out_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

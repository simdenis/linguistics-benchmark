from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def load_report(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _to_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute memorization gap (original - isomorphic).")
    ap.add_argument("--original", required=True)
    ap.add_argument("--isomorphic", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    orig = load_report(args.original)
    iso = load_report(args.isomorphic)

    orig_models: Dict[str, Any] = orig.get("models", {})
    iso_models: Dict[str, Any] = iso.get("models", {})

    out: Dict[str, Any] = {
        "original_path": args.original,
        "isomorphic_path": args.isomorphic,
        "models": {},
    }

    common = sorted(set(orig_models.keys()) & set(iso_models.keys()))
    for model in common:
        o = orig_models[model]
        i = iso_models[model]

        o_acc = _to_float(o.get("accuracy"))
        i_acc = _to_float(i.get("accuracy"))

        model_out: Dict[str, Any] = {
            "original_accuracy": o_acc,
            "isomorphic_accuracy": i_acc,
            "accuracy_gap": o_acc - i_acc,
            "original_n": o.get("n", 0),
            "isomorphic_n": i.get("n", 0),
            "by_task_gap": {},
            "by_source_gap": {},
        }

        o_bt = o.get("by_task", {}) or {}
        i_bt = i.get("by_task", {}) or {}
        for k in sorted(set(o_bt.keys()) & set(i_bt.keys())):
            model_out["by_task_gap"][k] = _to_float(o_bt.get(k)) - _to_float(i_bt.get(k))

        o_bs = o.get("by_source", {}) or {}
        i_bs = i.get("by_source", {}) or {}
        for k in sorted(set(o_bs.keys()) & set(i_bs.keys())):
            model_out["by_source_gap"][k] = _to_float(o_bs.get(k)) - _to_float(i_bs.get(k))

        out["models"][model] = model_out

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

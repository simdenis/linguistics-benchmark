from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from .io import Example


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_json_object(text: str) -> Dict[str, Any] | None:
    # Try direct JSON
    t = text.strip()
    if t.startswith("{") and t.endswith("}"):
        try:
            return json.loads(t)
        except Exception:
            pass

    # Otherwise, take the first {...} block
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def parse_prediction(example: Example, model_output: str) -> Any:
    """Parse model output to a canonical predicted value, based on example.output_spec."""
    spec = example.output_spec
    kind = spec.get("type")

    if kind == "json_mapping":
        obj = _extract_json_object(model_output)
        return obj

    if kind == "mcq_letter":
        # Return first standalone A-D (or broader range if specified)
        allowed = spec.get("allowed", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        # prefer a single capital letter token
        m = re.search(r"\b([A-Z])\b", model_output.upper())
        if not m:
            # fallback: any letter
            m = re.search(r"([A-Z])", model_output.upper())
        if not m:
            return None
        letter = m.group(1)
        return letter if letter in allowed else None

    if kind == "short_text":
        out = _normalize_ws(model_output)
        if spec.get("lower", True):
            out = out.lower()
        if spec.get("strip_punct", False):
            out = re.sub(r"[^\w\s]", "", out)
            out = _normalize_ws(out)
        return out

    # Unknown spec: return raw
    return _normalize_ws(model_output)


def score_example(example: Example, pred: Any) -> Tuple[float, Dict[str, Any]]:
    """Return (score in [0,1], details)."""
    spec = example.output_spec
    kind = spec.get("type")
    gold = example.answer

    if kind == "json_mapping":
        if not isinstance(gold, dict):
            raise ValueError(f"Gold answer for {example.id} must be dict for json_mapping")
        if not isinstance(pred, dict):
            return 0.0, {"reason": "pred_not_dict"}

        # Compare on expected keys if provided; else compare on gold keys
        keys = spec.get("keys") or list(gold.keys())
        total = 0
        correct = 0
        mismatches: List[Dict[str, Any]] = []
        for k in keys:
            ks = str(k)
            total += 1
            gv = str(gold.get(ks)).strip()
            pv = pred.get(ks)
            if pv is None:
                mismatches.append({"key": ks, "gold": gv, "pred": None})
                continue
            pv_s = str(pv).strip()
            if pv_s == gv:
                correct += 1
            else:
                mismatches.append({"key": ks, "gold": gv, "pred": pv_s})
        score = correct / total if total else 0.0
        return score, {"correct": correct, "total": total, "mismatches": mismatches[:20]}

    if kind == "mcq_letter":
        if pred is None:
            return 0.0, {"reason": "no_letter"}
        gv = str(gold).strip().upper()
        pv = str(pred).strip().upper()
        return (1.0, {}) if pv == gv else (0.0, {"gold": gv, "pred": pv})

    if kind == "short_text":
        # gold can be string or list of acceptable strings
        if pred is None:
            return 0.0, {"reason": "empty"}

        def norm(s: str) -> str:
            s2 = _normalize_ws(s)
            if spec.get("lower", True):
                s2 = s2.lower()
            if spec.get("strip_punct", False):
                s2 = re.sub(r"[^\w\s]", "", s2)
                s2 = _normalize_ws(s2)
            return s2

        pv = norm(str(pred))
        if isinstance(gold, list):
            gset = {norm(str(g)) for g in gold}
            return (1.0, {}) if pv in gset else (0.0, {"gold_any": sorted(list(gset))[:10], "pred": pv})
        else:
            gv = norm(str(gold))
            return (1.0, {}) if pv == gv else (0.0, {"gold": gv, "pred": pv})

    # Unknown type: strict equality
    return (1.0, {}) if pred == gold else (0.0, {"gold": gold, "pred": pred})

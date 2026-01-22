from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .io import read_jsonl, write_jsonl


_CONSONANTS = list("ptkbdgmnszrlfvjhw")
_VOWELS = list("aeiou")


def _rng_for(example_id: str, k: int) -> random.Random:
    h = hashlib.sha256(f"{example_id}::{k}".encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "little")
    return random.Random(seed)


def _pseudo_token(rng: random.Random, kind: str) -> str:
    # Kinds: 'l1' for mystery language tokens; 'en' for English gloss tokens; default 'tok'
    if kind == "en":
        return f"wug{rng.randint(10, 999)}"
    # pseudo 'language' token
    syls = rng.randint(1, 3)
    parts = []
    for _ in range(syls):
        c = rng.choice(_CONSONANTS)
        v = rng.choice(_VOWELS)
        parts.append(c + v)
    # sometimes end with consonant
    if rng.random() < 0.4:
        parts[-1] = parts[-1] + rng.choice(_CONSONANTS)
    return "".join(parts)


def _apply_span_replacements(text: str, spans: List[Dict[str, Any]], rng: random.Random) -> Tuple[str, Dict[str, str]]:
    mapping: Dict[str, str] = {}
    for s in spans:
        src = s.get("text")
        kind = s.get("kind", "l1")
        if not src or not isinstance(src, str):
            continue
        if src in mapping:
            continue
        mapping[src] = _pseudo_token(rng, kind)

    # Replace longest first to avoid subspan collisions
    for src in sorted(mapping.keys(), key=len, reverse=True):
        text = text.replace(src, mapping[src])
    return text, mapping


def _shuffle_enumerated_blocks(prompt: str, rng: random.Random) -> str:
    """Best-effort: shuffle lines starting with 'N.' and lines starting with 'A.' etc within each block."""
    lines = prompt.splitlines()

    def parse_block(start_pat: re.Pattern) -> List[Tuple[int, str, str]]:
        out = []
        for i, line in enumerate(lines):
            m = start_pat.match(line)
            if m:
                out.append((i, m.group(1), line))
        return out

    num_pat = re.compile(r"^\s*(\d+)\.\s+.*$")
    let_pat = re.compile(r"^\s*([A-Z])\.\s+.*$")

    for pat in (num_pat, let_pat):
        idxs = parse_block(pat)
        if len(idxs) >= 4:
            # shuffle in-place by permuting the matching lines only
            shuffled = idxs[:]
            rng.shuffle(shuffled)
            for (orig_i, _id, _line), (_, __id, new_line) in zip(idxs, shuffled):
                lines[orig_i] = new_line

    return "\n".join(lines)


def make_isomorphic_variants(dataset_rows: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    out_rows: List[Dict[str, Any]] = []

    for row in dataset_rows:
        out_rows.append(row)
        ex_id = str(row.get("id"))
        for j in range(1, k + 1):
            rng = _rng_for(ex_id, j)
            new_row = json.loads(json.dumps(row))  # deep copy
            new_row["id"] = f"{ex_id}__iso{j}"

            meta = new_row.get("meta") or {}
            meta["iso_of"] = ex_id
            meta["iso_k"] = j

            prompt = new_row.get("prompt", "")

            # Style 1: span replacements if provided
            spans = (((meta.get("variantable") or {}).get("spans")) or [])
            if isinstance(spans, list) and spans:
                prompt, mapping = _apply_span_replacements(prompt, spans, rng)
                meta["iso_span_mapping"] = mapping
            else:
                # Style 2: shuffle enumerated blocks as a fallback
                prompt = _shuffle_enumerated_blocks(prompt, rng)

            new_row["prompt"] = prompt
            new_row["meta"] = meta
            out_rows.append(new_row)

    return out_rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate isomorphic variants for leakage stress testing.")
    ap.add_argument("--dataset", required=True, help="Input JSONL")
    ap.add_argument("--out", required=True, help="Output JSONL")
    ap.add_argument("--k", type=int, default=3, help="How many variants per example")
    args = ap.parse_args()

    rows = list(read_jsonl(Path(args.dataset)))
    new_rows = make_isomorphic_variants(rows, k=max(0, int(args.k)))
    write_jsonl(Path(args.out), new_rows)


if __name__ == "__main__":
    main()

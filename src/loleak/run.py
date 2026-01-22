from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

from tqdm import tqdm

from .io import load_examples
from .ollama import OllamaClient


def _sanitize_model_name(name: str) -> str:
    # Safe path component
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run models on LO-Leakage-Bench examples using Ollama.")
    ap.add_argument("--models", nargs="+", required=True, help="Ollama model tags (e.g., qwen2.5:7b)")
    ap.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    ap.add_argument("--outdir", default="runs", help="Directory to write model outputs")
    ap.add_argument("--base_url", default="http://localhost:11434", help="Ollama base URL")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--top_p", type=float, default=1.0)
    ap.add_argument("--num_ctx", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="If >0, only run first N examples")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    args = ap.parse_args()

    dataset_path = Path(args.dataset)
    examples = load_examples(dataset_path)
    if args.limit and args.limit > 0:
        examples = examples[: args.limit]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    client = OllamaClient(base_url=args.base_url)

    for model in args.models:
        model_dir = outdir / _sanitize_model_name(model)
        model_dir.mkdir(parents=True, exist_ok=True)

        for ex in tqdm(examples, desc=f"{model}"):
            out_path = model_dir / f"{ex.id}.json"
            if out_path.exists() and not args.overwrite:
                continue

            resp = client.generate(
                model=model,
                prompt=ex.prompt,
                temperature=args.temperature,
                top_p=args.top_p,
                num_ctx=args.num_ctx,
                seed=args.seed,
            )

            payload = {
                "example_id": ex.id,
                "model": model,
                "response": resp.response,
                "prompt_eval_count": resp.prompt_eval_count,
                "eval_count": resp.eval_count,
                "total_duration_ns": resp.total_duration_ns,
            }

            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

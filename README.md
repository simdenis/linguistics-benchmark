# LO-Leakage-Bench (v0.1)

A lightweight, **fully reproducible** benchmark runner for Linguistics Olympiad–style problems, plus a **leakage stress test** suite (isomorphic variants + memorization gap). Designed to run **free/open models locally** on Apple Silicon via **Ollama**.

This repo is intentionally minimal so you can ship quickly.

## Core idea
1) Benchmark models on **auto-gradable** Olympiad subproblems (matchings, short fill-ins, MCQs).
2) Generate **isomorphic variants** that preserve the underlying logic but change surface form.
3) Measure a model’s **memorization gap**:

> gap = score(original) − score(isomorphic)

Large gaps suggest recall/leakage; small gaps suggest true generalization.

---

## Quickstart (Mac M1 Pro)

### 0) Install
- Python 3.10+ (recommended: 3.11)
- Ollama

```bash
brew install ollama
ollama serve
```

### 1) Pull models (free/open)
Edit `scripts/pull_models.sh` if you want a different lineup.

```bash
bash scripts/pull_models.sh
```

### 2) Install python deps
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 3) Run on example problems
```bash
python -m loleak.run \
  --models qwen2.5:7b llama3.1:8b mistral:7b \
  --dataset data/examples/example_dataset.jsonl \
  --outdir runs

python -m loleak.eval \
  --dataset data/examples/example_dataset.jsonl \
  --rundir runs \
  --report results/report.json
```

### 4) Leakage stress test (isomorphic variants)
```bash
python -m loleak.isomorph \
  --dataset data/examples/example_dataset.jsonl \
  --out data/examples/example_dataset.isomorphic.jsonl \
  --k 3

python -m loleak.run \
  --models qwen2.5:7b llama3.1:8b \
  --dataset data/examples/example_dataset.isomorphic.jsonl \
  --outdir runs

python -m loleak.eval \
  --dataset data/examples/example_dataset.isomorphic.jsonl \
  --rundir runs \
  --report results/report_isomorphic.json

python -m loleak.gap \
  --original results/report.json \
  --isomorphic results/report_isomorphic.json \
  --out results/memorization_gap.json
```

---

## Dataset format (JSONL)
Each line is one **subproblem**.

- `id`: unique
- `source`: e.g., "NACLO", "UKLO", "AUSLO", "IOL"
- `year`: integer (optional but strongly recommended)
- `task_type`: one of:
  - `matching`
  - `mcq`
  - `short_text`
- `prompt`: the full model prompt (we keep it explicit so formatting is stable)
- `answer`: canonical gold answer
- `output_spec`: how we will parse the model output

See `data/examples/example_dataset.jsonl`.

---

## Releasing the dataset safely
Many Olympiad problems are copyrighted. A safe approach for v1:
- Store **structured problem data** needed for evaluation (tables/wordlists/options) and **links** to sources.
- Avoid shipping verbatim PDFs/solutions.
- If you later want to publish a full dataset, get permission or restrict to permissively licensed sources.

---

## Roadmap for your 2-week sprint
See `docs/PLAN.md`.

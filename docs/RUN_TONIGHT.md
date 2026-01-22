# Overnight runs

```bash
python scripts/extract_structured_ollama.py \
  --in data/raw/naclo_filtered.jsonl \
  --out data/structured/naclo_draft.jsonl \
  --mode problems \
  --model qwen2.5:14b \
  --resume

python scripts/extract_structured_ollama.py \
  --in data/raw/uklo_filtered.jsonl \
  --out data/structured/uklo_draft.jsonl \
  --mode problems \
  --model qwen2.5:14b \
  --resume

python scripts/filter_raw.py \
  --in data/raw/naclo_raw.jsonl \
  --out data/raw/naclo_solutions.jsonl \
  --mode solutions

python scripts/filter_raw.py \
  --in data/raw/iol_raw.jsonl \
  --out data/raw/iol_solutions.jsonl \
  --mode solutions

python scripts/filter_raw.py \
  --in data/raw/uklo_raw.jsonl \
  --out data/raw/uklo_solutions.jsonl \
  --mode solutions

python scripts/extract_structured_ollama.py \
  --in data/raw/naclo_solutions.jsonl \
  --out data/structured/naclo_solutions.jsonl \
  --mode solutions \
  --model qwen2.5:14b \
  --resume

python scripts/extract_structured_ollama.py \
  --in data/raw/iol_solutions.jsonl \
  --out data/structured/iol_solutions.jsonl \
  --mode solutions \
  --model qwen2.5:14b \
  --resume

python scripts/extract_structured_ollama.py \
  --in data/raw/uklo_solutions.jsonl \
  --out data/structured/uklo_solutions.jsonl \
  --mode solutions \
  --model qwen2.5:14b \
  --resume
```

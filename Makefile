.PHONY: pull demo iso iso_run iso_eval gap extract_raw filter_raw extract_structured extract_structured_local merge_structured

MODELS ?= qwen2.5:7b llama3.1:8b mistral:7b
DATA ?= data/examples/example_dataset.jsonl
ISO_DATA ?= data/examples/example_dataset.isomorphic.jsonl
RUNS ?= runs

pull:
	bash scripts/pull_models.sh

demo:
	python -m loleak.run --models $(MODELS) --dataset $(DATA) --outdir $(RUNS)
	python -m loleak.eval --dataset $(DATA) --rundir $(RUNS) --report results/report.json

iso:
	python -m loleak.isomorph --dataset $(DATA) --out $(ISO_DATA) --k 3

iso_run:
	python -m loleak.run --models $(MODELS) --dataset $(ISO_DATA) --outdir $(RUNS)

iso_eval:
	python -m loleak.eval --dataset $(ISO_DATA) --rundir $(RUNS) --report results/report_isomorphic.json

gap:
	python -m loleak.gap --original results/report.json --isomorphic results/report_isomorphic.json --out results/memorization_gap.json

extract_raw:
	python scripts/extract_pdf_raw.py --source iol
	python scripts/extract_pdf_raw.py --source naclo
	python scripts/extract_pdf_raw.py --source uklo

filter_raw:
	python scripts/filter_raw.py --in data/raw/iol_raw.jsonl --out data/raw/iol_filtered.jsonl
	python scripts/filter_raw.py --in data/raw/naclo_raw.jsonl --out data/raw/naclo_filtered.jsonl
	python scripts/filter_raw.py --in data/raw/uklo_raw.jsonl --out data/raw/uklo_filtered.jsonl

extract_structured:
	python scripts/extract_structured.py --in data/raw/iol_filtered.jsonl --out data/structured/iol_draft.jsonl --mode problems
	python scripts/extract_structured.py --in data/raw/naclo_filtered.jsonl --out data/structured/naclo_draft.jsonl --mode problems
	python scripts/extract_structured.py --in data/raw/uklo_filtered.jsonl --out data/structured/uklo_draft.jsonl --mode problems

extract_structured_local:
	python scripts/extract_structured_ollama.py --in data/raw/iol_filtered.jsonl --out data/structured/iol_draft.jsonl --mode problems
	python scripts/extract_structured_ollama.py --in data/raw/naclo_filtered.jsonl --out data/structured/naclo_draft.jsonl --mode problems
	python scripts/extract_structured_ollama.py --in data/raw/uklo_filtered.jsonl --out data/structured/uklo_draft.jsonl --mode problems

merge_structured:
	python scripts/merge_structured.py --problems data/structured/iol_draft.jsonl --solutions data/structured/iol_solutions.jsonl --out data/structured/iol_merged.jsonl
	python scripts/merge_structured.py --problems data/structured/naclo_draft.jsonl --solutions data/structured/naclo_solutions.jsonl --out data/structured/naclo_merged.jsonl
	python scripts/merge_structured.py --problems data/structured/uklo_draft.jsonl --solutions data/structured/uklo_solutions.jsonl --out data/structured/uklo_merged.jsonl

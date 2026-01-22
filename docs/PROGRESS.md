# Progress log

## Scope
- Competitions: IOL, NACLO, UKLO
- Years: 2010+
- Task types: matching, mcq, short_text (normalized characters)
- Exclusions: non-Latin scripts, low-quality scans, non-auto-gradable problems

## Completed
- Download scripts: `download_iol.py`, `download_naclo.py`, `download_uklo.py`
- Merge PDFs: `scripts/merge_pdfs.py` (IOL/NACLO)
- Raw extraction: `scripts/extract_pdf_raw.py` -> `data/raw/*_raw.jsonl`
- Filtering: `scripts/filter_raw.py` -> `data/raw/*_filtered.jsonl`
- Local LLM extraction: `scripts/extract_structured_ollama.py` (with resume)
- Merge drafts: `scripts/merge_structured.py`
- Paper updates: dataset + reproducibility sections synced to pipeline

## In progress
- Run Ollama extraction on full datasets (overnight)
- Generate solution drafts and merge with problem drafts

## Next
- Validate final JSONL schema + answer coverage
- Add variantable spans and generate isomorphs
- Run evaluation and compute memorization gap
- Summarize dataset stats and results

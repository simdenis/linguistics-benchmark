# 14-step execution plan (no fluff)

Goal: ship a **reproducible** benchmark + leakage stress test across **NACLO, UKLO, AUSLO (+ IOL optional)** using **only open/local models**.

## Deliverables
1) `data/.../*.jsonl`: auto-gradable subset (matching / MCQ / short answers)
2) `loleak` runner + evaluator + isomorphic variant generator
3) `results/`: baseline leaderboard + memorization-gap plots/tables
4) A short report: methods, dataset, key findings, limitations (esp. licensing + leakage)

---

## Step 0 (today): sanity check the pipeline
1. Install + start Ollama
2. Pull 3 models
3. Run the demo dataset:
   - `python -m loleak.run ...`
   - `python -m loleak.eval ...`
4. Generate isomorphic variants + compute gaps

If this works, you never do manual scoring.

---

## Steps 1–3: build the dataset format + templates
- Decide your **task types** for v1:
  - Matching (JSON mapping)
  - MCQ (one letter)
  - Short answer (normalized exact match)
- Write **one prompt template** per task type and keep it fixed.
- For each example, store `prompt` exactly as sent to models.

Tip: keep prompts short; put the data in the prompt, not the story.

---

## Steps 4–7: acquire problems (fast path)
Fast path = manual curation of only the parts you can auto-grade.

1) Create `data/naclo_v1.jsonl`, `data/uklo_v1.jsonl`, `data/auslo_v1.jsonl`
2) For each competition, start with ~25–50 **subproblems**, not full problems.
3) Prefer:
   - matching tables
   - fill-in translations with a single canonical expected string
   - explicit multiple-choice subparts

Licensing-safe v1:
- Don’t ship PDFs/solution text.
- Store only what's necessary: the word lists/tables/options and the gold label, and add `meta.source_url` pointing to the official page.

---

## Steps 8–10: leakage stress test suite
Implement two variant styles (already supported):
1) **Span replacement** (best): provide `meta.variantable.spans` (substrings) and we replace them with pseudo-tokens.
2) **Shuffling** fallback: reorder enumerated lines while preserving IDs.

For each example, add spans for:
- all mystery-language forms
- all English glosses (or MCQ answer strings)

Generate `k=3` isomorphic variants.

---

## Steps 11–12: run models locally (free)
Pick a stable lineup that runs on M1 Pro:
- qwen2.5:7b
- llama3.1:8b
- mistral:7b
- gemma2:9b
- phi3:mini

Run on:
- original dataset
- isomorphic dataset
Compute memorization gap.

---

## Steps 13–14: write the report
Include:
- Dataset description + task breakdown
- Evaluation (strict, auto-graded)
- Leakage methodology (isomorphic variants + gap)
- Key results (who drops the most on variants)
- Threats to validity (contamination, licensing, prompt sensitivity)


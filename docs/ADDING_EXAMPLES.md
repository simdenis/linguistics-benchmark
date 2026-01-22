# Adding benchmark items

Each line is one JSON object (JSONL). Keep items **small** and **auto-gradable**.

## Matching
- `task_type`: `matching`
- `output_spec`: `{ "type": "json_mapping", "keys": ["1", "2", ...] }`
- `answer`: a JSON object mapping those keys to letters.

Tip: add `meta.variantable.spans` for leakage variants:
```json
{"meta":{"variantable":{"spans":[{"text":"<mystery-token>","kind":"l1"},{"text":"<english-gloss>","kind":"en"}]}}}
```

## MCQ
- `task_type`: `mcq`
- `output_spec`: `{ "type": "mcq_letter", "allowed": ["A","B","C","D"] }`
- `answer`: a single letter.

## Short text
- `task_type`: `short_text`
- `output_spec`: `{ "type": "short_text", "lower": true, "strip_punct": false }`
- `answer`: string, or list of acceptable strings.

# Next steps

1) Check outputs
```bash
wc -l data/structured/*_draft.jsonl data/structured/*_solutions.jsonl
```

2) Merge problems + solutions
```bash
make merge_structured
```

3) Validate merged JSONL (missing answers, output_spec)
```bash
# TODO: add validator script
```

4) Add variantable spans + generate isomorphs
```bash
# TODO: add span annotator + run loleak.isomorph
```

5) Run evaluation (orig + iso) and compute gap
```bash
# TODO: run loleak.run / loleak.eval / loleak.gap
```

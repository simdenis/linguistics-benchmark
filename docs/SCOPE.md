# v1 dataset scope (step 1)

## Competitions
- IOL
- NACLO
- UKLO

## Years
- 2010 and after

## Task types (keep only)
- mcq
- matching
- short_text (normalized characters)

## Exclude / ignore
- Non-auto-gradable free response or multi-step reasoning
- Image-only or low-quality scans that do not OCR cleanly
- Problems in non-Latin scripts or unusual writing systems
- Biology/medical content (e.g., mRNA) if it breaks the language focus
- Anything that cannot be cleanly reduced to matching/MCQ/short_text

## Curation notes
- Prefer subparts with explicit tables, word lists, or option sets.
- Keep prompts short; include only the structured data needed to solve.
- Add `meta.source_url` and `meta.page` for every kept item.

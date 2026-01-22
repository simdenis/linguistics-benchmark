# Reject log template

Use one row per PDF/page (or per subproblem) that you want to exclude.

```
source,year,file,page,reason,notes
IOL,2012,iol-2012-indiv-prob.en.pdf,7,non_latin_script,requires Cyrillic mapping
NACLO,2015,naclo-2015-round1-problems.pdf,3,image_only_scan,unreadable OCR
UKLO,2011,uklo-2011-round1-problems.pdf,4,non_language_topic,mRNA biology focus
```

## Reasons (recommended)
- non_latin_script
- image_only_scan
- low_quality_ocr
- non_autogradable
- missing_options
- multi_step_reasoning
- non_language_topic
- other

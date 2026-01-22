# LOLeakBench paper (LaTeX)

This folder is a starter LaTeX draft for the LOLeakBench paper.

## Build

```bash
cd lo-leakage-paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

(or use `latexmk -pdf main.tex` if you have latexmk)

## Structure

- `main.tex`: main entry point
- `sections/`: one file per section
- `refs.bib`: bibliography

Fill TODOs as you collect data and run experiments.

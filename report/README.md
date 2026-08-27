# Project report (LaTeX)

Writeup for the Scenic–Basilisk asteroid-landing case study.
The compiled PDF is `report.pdf` (main body plus references is within the 6–10 page limit; the appendix is extra).

## Contents

| File | Role |
|------|------|
| `report.tex` | Main paper |
| `references.bib` | Citations |
| `report.pdf` | Compiled PDF |
| `figures/` | Plots from evaluation CSVs |
| `make_figures.py` | Regenerates `figures/` |

## Compile

From this directory (TeX Live / MiKTeX, or [Tectonic](https://tectonic-typesetting.github.io/)):

```bash
pdflatex report.tex
bibtex report
pdflatex report.tex
pdflatex report.tex
```

Or:

```bash
tectonic -X compile report.tex
```

## Regenerate figures

Use the `asteroid-rl-demo` virtualenv (`matplotlib` and `pandas`):

```bash
../asteroid-rl-demo/.venv/Scripts/python.exe make_figures.py
```

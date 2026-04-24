# Zurich Edu Data

Analysis of ETH Zurich and University of Zurich (UZH) academic staff
composition, with a focus on foreign (Ausländer) share over time.

## Layout

```
data/
  raw/         Source CSVs and the original ETH .docx
  processed/   Cleaned / derived tables (safe to regenerate from scripts)
scripts/       Python scripts (run from the repo root: `python3 scripts/<name>.py`)
output/
  figures/     PNG plots
  tables/      LaTeX sources and compiled PDFs
PROJECT_MEMORY.md
```

## Scripts → outputs

| Script | Inputs (`data/raw/`) | Outputs |
|---|---|---|
| `scripts/fetch_eth_uzh_professors.py` | FSO PxWeb API | `data/raw/eth_uzh_staff_by_*.csv`, `data/raw/eth_uzh_foreign_staff_by_field_*.csv` |
| `scripts/eth_prof_auslaender_summary.py` | `ETH_Prof_Counts_2006_2025.csv`, `ETH_Auslander_Prof_Counts_2006_2025.csv` | `data/processed/eth_prof_auslaender_summary.{csv,txt,html}` |
| `scripts/build_latex_tables.py` | `ETH_Prof_Counts_2006_2025.csv`, `ETH_Auslander_Prof_Counts_2006_2025.csv`, `UZH_Dozierende_2010-2024.csv` | `data/processed/uzh_dozierende_clean.csv`, `output/tables/{eth,uzh}_professors_table.tex` |
| `scripts/eth_uzh_prof_composition_plot.py` | `data/processed/eth_prof_auslaender_summary.csv`, `UZH_Dozierende_2010-2024.csv` | `output/figures/eth_uzh_prof_composition.png` |
| `scripts/prof_anteil_uebersicht.py` | `eth_uzh_staff_by_nationality_de.csv`, `eth_uzh_staff_by_rank_de.csv` | `output/figures/auslaenderanteil_plot.png`, `output/figures/personalstruktur_plot.png` |
| `scripts/uzh_econ_auslaender.py` | `eth_uzh_staff_by_nationality_de.csv` | `output/figures/uzh_econ_auslaenderanteil_plot.png` |

Compile LaTeX tables:

```
cd output/tables && pdflatex eth_professors_table.tex && pdflatex uzh_professors_table.tex
```

## Notes

- The UZH raw file uses a walked-block layout (faculty header → rank rows); `build_latex_tables.py` cleans it into long format (`data/processed/uzh_dozierende_clean.csv`). For 2022+, an appended "flat" Professuren-per-faculty row style overrides earlier figures — see `clean_uzh()` for the look-ahead logic.
- `data/raw/eth_uzh_staff_by_nationality.csv` is byte-identical to `..._en.csv`; same for `..._rank.csv` / `..._rank_en.csv`. Kept for now pending a decision on which to retain.

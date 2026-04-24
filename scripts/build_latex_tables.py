"""Build LaTeX tables:
  - ETH: hierarchical Faculty/Department/Rank × year (split 2006-2015 and 2016-2025)
  - UZH: hierarchical Faculty/Rank × year (2010-2024), built from a cleaned
    long-format table because the raw CSV interleaves faculty headers and ranks.

Also writes uzh_dozierende_clean.csv for inspection.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
UZH_CSV = RAW / "UZH_Dozierende_2010-2024.csv"
ETH_TOTAL = RAW / "ETH_Prof_Counts_2006_2025.csv"
ETH_FOREIGN = RAW / "ETH_Auslander_Prof_Counts_2006_2025.csv"
UZH_CLEAN = PROCESSED / "uzh_dozierende_clean.csv"
UZH_TEX = TABLES / "uzh_professors_table.tex"
ETH_TEX = TABLES / "eth_professors_table.tex"

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def latex_escape(s: str) -> str:
    return (str(s).replace("\\", r"\textbackslash{}")
            .replace("&", r"\&").replace("%", r"\%")
            .replace("_", r"\_").replace("#", r"\#")
            .replace("{", r"\{").replace("}", r"\}"))


def strip_footnote(name: str) -> str:
    """Strip trailing footnote digits like 'Professuren 1 2 6' -> 'Professuren'."""
    return re.sub(r"\s+\d+(?:\s+\d+)*$", "", str(name)).strip()


# --------------------------------------------------------------------------
# Clean UZH
# --------------------------------------------------------------------------
RAW_RANKS = {
    "Professuren",
    "Titularprofessuren",
    "Privatdozierende",
    "Lehrbeauftragte",
    "Externe Lehrpersonen",
}

# Merge Lehrbeauftragte/Externe Lehrpersonen — the label was swapped ~2019.
RANK_CANON = {
    "Professuren": "Professuren",
    "Titularprofessuren": "Titularprofessuren",
    "Privatdozierende": "Privatdozierende",
    "Lehrbeauftragte": "Lehrbeauftragte / Externe Lehrpersonen",
    "Externe Lehrpersonen": "Lehrbeauftragte / Externe Lehrpersonen",
}

FACULTY_CANON = {
    "Theologische Fakultät": "Theologische Fakultät",
    "Theologische und Religionswiss. Fakultät": "Theologische Fakultät",
    "Rechtswissenschaftliche Fakultät": "Rechtswissenschaftliche Fakultät",
    "Wirtschaftswissenschaftliche Fakultät": "Wirtschaftswissenschaftliche Fakultät",
    "Medizinische Fakultät": "Medizinische Fakultät",
    "Vetsuisse-Fakultät": "Vetsuisse Fakultät",
    "Vetsuisse Fakultät": "Vetsuisse Fakultät",
    "Philosophische Fakultät": "Philosophische Fakultät",
    "Mathematisch-naturwiss. Fakultät": "Mathematisch-naturwissenschaftliche Fakultät",
    "Mathematisch-naturwissenschaftliche Fakultät": "Mathematisch-naturwissenschaftliche Fakultät",
    "Mathematisch naturwissenschaftliche Fakultät": "Mathematisch-naturwissenschaftliche Fakultät",
    "Zentrale Dienste der Universität": "Zentrale Dienste der Universität",
    "Schwerpunkt Forschung und Lehre": "Schwerpunkt Forschung und Lehre",
    "Total": "Gesamt Universität",
}
SKIP_KATEGORIE = {"Lehrpersonen"}  # pseudo header; ignore


FACULTY_ORDER = [
    "Theologische Fakultät",
    "Rechtswissenschaftliche Fakultät",
    "Wirtschaftswissenschaftliche Fakultät",
    "Medizinische Fakultät",
    "Vetsuisse Fakultät",
    "Philosophische Fakultät",
    "Mathematisch-naturwissenschaftliche Fakultät",
    "Schwerpunkt Forschung und Lehre",
    "Zentrale Dienste der Universität",
    "Gesamt Universität",
]

RANK_ORDER = [
    "Professuren",
    "Titularprofessuren",
    "Privatdozierende",
    "Lehrbeauftragte / Externe Lehrpersonen",
]


def clean_uzh(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw = raw[raw["Semester"] == "HS " + raw["Report_Jahr"].astype(str)].copy()
    raw["Kategorie_clean"] = raw["Kategorie"].astype(str).map(strip_footnote)
    raw = raw.reset_index(drop=True)

    records: list[dict] = []
    current_faculty: str | None = None

    for i, row in raw.iterrows():
        kat = row["Kategorie_clean"]
        if kat in SKIP_KATEGORIE or kat.startswith("(") or kat == "":
            continue
        year = int(row["Report_Jahr"])
        if kat in RAW_RANKS:
            if current_faculty is None:
                continue
            records.append({
                "Year": year,
                "Faculty": current_faculty,
                "Rank": RANK_CANON[kat],
                "Total": pd.to_numeric(row["Total"], errors="coerce"),
                "Frauen_%": pd.to_numeric(row["Frauen_%"], errors="coerce"),
                "Auslaendische_%": pd.to_numeric(row["Auslaendische_%"], errors="coerce"),
            })
        else:
            # Faculty header row
            canon = FACULTY_CANON.get(kat)
            current_faculty = canon
            # Supplementary "flat" Professuren rows (appended for 2022+):
            # faculty-name row with empty Frauen_% and not followed by rank rows.
            next_kat = (raw.at[i + 1, "Kategorie_clean"]
                        if i + 1 < len(raw) else "")
            is_flat = pd.isna(row["Frauen_%"]) and (next_kat not in RAW_RANKS)
            if is_flat and canon is not None:
                records.append({
                    "Year": year,
                    "Faculty": canon,
                    "Rank": "Professuren",
                    "Total": pd.to_numeric(row["Total"], errors="coerce"),
                    "Frauen_%": float("nan"),
                    "Auslaendische_%": pd.to_numeric(
                        row["Auslaendische_%"], errors="coerce"),
                })

    df = pd.DataFrame.from_records(records)
    # Supplementary flat rows come later in the file and carry revised figures
    # for 2022+, so keep the LAST record per (year, faculty, rank).
    df = df.drop_duplicates(subset=["Year", "Faculty", "Rank"], keep="last")
    return df


uzh_long = clean_uzh(UZH_CSV)
uzh_long.to_csv(UZH_CLEAN, index=False)

# --------------------------------------------------------------------------
# Load ETH
# --------------------------------------------------------------------------
ETH_YEARS = list(range(2006, 2026))
ETH_RANKS = {"Vollprofessor/innen": "Full Professor",
             "Assistenzprofessor/innen": "Assistant Professor"}
SKIP_ETH_FAC = {"Gesamtsumme", "Ausnahme", "SL-Stäbe und Abteilungen",
                "Ausserdep. L&F-Einheiten und Übrige"}


def load_eth(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    year_cols = [str(y) for y in ETH_YEARS]
    d[year_cols] = d[year_cols].apply(pd.to_numeric, errors="coerce")
    d = d[d["Funktion"].isin(ETH_RANKS)]
    long = d.melt(id_vars=["Fachbereich", "Departement", "Funktion"],
                  value_vars=year_cols, var_name="Year", value_name="Value")
    long["Year"] = long["Year"].astype(int)
    return long


totals = load_eth(ETH_TOTAL).rename(columns={"Value": "Total"})
foreign = load_eth(ETH_FOREIGN).rename(columns={"Value": "Foreign"})
eth = totals.merge(foreign, on=["Fachbereich", "Departement", "Funktion", "Year"],
                   how="left")
eth = eth[~eth["Fachbereich"].isin(SKIP_ETH_FAC)]
eth["Foreign_pct"] = eth["Foreign"] / eth["Total"] * 100


# --------------------------------------------------------------------------
# LaTeX render helpers
# --------------------------------------------------------------------------
def fmt_total(v: float) -> str:
    return f"{v:.1f}" if pd.notna(v) else "--"


def fmt_pct(v: float) -> str:
    return f"{int(round(v))}" if pd.notna(v) else "--"


def year_header(years: list[int]) -> tuple[str, str, str]:
    top = (" & " + " & ".join(
        rf"\multicolumn{{2}}{{c}}{{\textbf{{{y}}}}}" for y in years) + r" \\")
    cmids = " ".join(rf"\cmidrule(lr){{{2+2*i}-{3+2*i}}}"
                     for i in range(len(years)))
    sub = (" & " + " & ".join(["T & \\%"] * len(years)) + r" \\")
    return top, cmids, sub


# --------------------------------------------------------------------------
# ETH longtable builder (one call per year range)
# --------------------------------------------------------------------------
def build_eth_longtable(years: list[int], caption: str, label: str) -> str:
    n_year_cols = 2 * len(years)
    col_spec = "@{}l " + " ".join(["rr"] * len(years)) + "@{}"
    top, cmids, sub = year_header(years)

    body: list[str] = []
    faculties = [f for f in eth["Fachbereich"].drop_duplicates()]
    for fac in faculties:
        fac_rows = eth[eth["Fachbereich"] == fac]
        # Faculty-level totals: sum of Full + Assistant across all departments
        fac_tot = fac_rows.groupby("Year")["Total"].sum(min_count=1)
        fac_foreign = fac_rows.groupby("Year")["Foreign"].sum(min_count=1)
        fac_pct = fac_foreign / fac_tot * 100
        fac_cells: list[str] = []
        for y in years:
            fac_cells.append(fmt_total(fac_tot.get(y, float("nan"))))
            fac_cells.append(fmt_pct(fac_pct.get(y, float("nan"))))
        body.append(
            rf"\textbf{{{latex_escape(fac)}}} & "
            + " & ".join(rf"\textbf{{{c}}}" for c in fac_cells) + r" \\"
        )
        for dept in fac_rows["Departement"].drop_duplicates():
            dept_rows = fac_rows[fac_rows["Departement"] == dept]
            body.append(
                rf"\quad \textit{{{latex_escape(dept)}}} & "
                + " & ".join([""] * n_year_cols) + r" \\"
            )
            for rank_de, rank_en in ETH_RANKS.items():
                rr = dept_rows[dept_rows["Funktion"] == rank_de]
                if rr.empty:
                    continue
                by_y = rr.set_index("Year")
                cells = []
                for y in years:
                    if y in by_y.index:
                        cells.append(fmt_total(by_y.loc[y, "Total"]))
                        cells.append(fmt_pct(by_y.loc[y, "Foreign_pct"]))
                    else:
                        cells.extend(["--", "--"])
                body.append(
                    rf"\quad\quad {latex_escape(rank_en)} & "
                    + " & ".join(cells) + r" \\"
                )
        body.append(r"\addlinespace")

    body_str = "\n    ".join(body)

    return rf"""\begin{{longtable}}{{{col_spec}}}
  \caption{{{caption}}} \label{{{label}}} \\
  \toprule
  {top}
  {cmids}
  \textbf{{Faculty / Department / Rank}} {sub}
  \midrule
  \endfirsthead

  \toprule
  {top}
  {cmids}
  \textbf{{Faculty / Department / Rank}} {sub}
  \midrule
  \endhead

  \midrule
  \multicolumn{{{1 + n_year_cols}}}{{r}}{{\textit{{continued on next page}}}} \\
  \endfoot

  \bottomrule
  \endlastfoot

    {body_str}
\end{{longtable}}
"""


# --------------------------------------------------------------------------
# UZH longtable (faculty × rank), rendered per year range
# --------------------------------------------------------------------------
def build_uzh_longtable(years: list[int], caption: str, label: str) -> str:
    n_year_cols = 2 * len(years)
    col_spec = "@{}l " + " ".join(["rr"] * len(years)) + "@{}"
    top, cmids, sub = year_header(years)

    body: list[str] = []
    faculties_present = [f for f in FACULTY_ORDER
                         if f in uzh_long["Faculty"].unique()]
    for fac in faculties_present:
        rr = uzh_long[(uzh_long["Faculty"] == fac)
                      & (uzh_long["Rank"] == "Professuren")]
        if rr.empty:
            continue
        by_y = rr.set_index("Year")
        cells: list[str] = []
        for y in years:
            if y in by_y.index:
                cells.append(fmt_total(by_y.loc[y, "Total"]))
                cells.append(fmt_pct(by_y.loc[y, "Auslaendische_%"]))
            else:
                cells.extend(["--", "--"])
        body.append(
            rf"{latex_escape(fac)} & " + " & ".join(cells) + r" \\"
        )

    body_str = "\n    ".join(body)

    return rf"""\begin{{longtable}}{{{col_spec}}}
  \caption{{{caption}}}
  \label{{{label}}} \\
  \toprule
  {top}
  {cmids}
  \textbf{{Faculty}} {sub}
  \midrule
  \endfirsthead

  \toprule
  {top}
  {cmids}
  \textbf{{Faculty}} {sub}
  \midrule
  \endhead

  \midrule
  \multicolumn{{{1 + n_year_cols}}}{{r}}{{\textit{{continued on next page}}}} \\
  \endfoot

  \bottomrule
  \endlastfoot

    {body_str}
\end{{longtable}}
"""


# --------------------------------------------------------------------------
# Compose documents
# --------------------------------------------------------------------------
PREAMBLE_ETH = r"""\documentclass{article}
\usepackage[landscape, margin=0.4in]{geometry}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{caption}

\begin{document}

\small
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
"""

eth_part1 = build_eth_longtable(
    list(range(2006, 2016)),
    "ETH Zurich Professors by Faculty, Department and Rank, 2006--2015. "
    "T = Total FTE; \\% = Foreign share (\\%).",
    "tab:eth_professors_part1",
)
eth_part2 = build_eth_longtable(
    list(range(2016, 2026)),
    "ETH Zurich Professors by Faculty, Department and Rank, 2016--2025. "
    "T = Total FTE; \\% = Foreign share (\\%).",
    "tab:eth_professors_part2",
)

ETH_TEX.write_text(
    PREAMBLE_ETH + "\n" + eth_part1 + "\n\\clearpage\n" + eth_part2 + "\n\\end{document}\n"
)

PREAMBLE_UZH = r"""\documentclass{article}
\usepackage[landscape, margin=0.4in]{geometry}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{caption}

\begin{document}

\small
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
"""

uzh_cap = ("UZH Professuren by Faculty, {range}. "
           "T = Total; \\% = Foreign share (\\%).")
uzh_part1 = build_uzh_longtable(
    list(range(2010, 2018)),
    uzh_cap.format(range="2010--2017"),
    "tab:uzh_professors_part1",
)
uzh_part2 = build_uzh_longtable(
    list(range(2018, 2025)),
    uzh_cap.format(range="2018--2024"),
    "tab:uzh_professors_part2",
)

UZH_TEX.write_text(
    PREAMBLE_UZH + "\n" + uzh_part1 + "\n\\vspace{1.5em}\n" + uzh_part2
    + "\n\\end{document}\n"
)

print(f"Wrote: {UZH_CLEAN.name}, {UZH_TEX.name}, {ETH_TEX.name}")
print(f"UZH cleaned rows: {len(uzh_long)}  "
      f"(faculties: {uzh_long['Faculty'].nunique()}, "
      f"ranks: {uzh_long['Rank'].nunique()})")
print("Faculties present:", sorted(uzh_long['Faculty'].unique()))

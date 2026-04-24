"""ETH Full + Assistant professor totals vs. foreign share, 2006-2025.

Produces a fixed-width text table grouped by faculty, plus CSV/HTML exports.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
TOTAL_CSV = RAW / "ETH_Prof_Counts_2006_2025.csv"
FOREIGN_CSV = RAW / "ETH_Auslander_Prof_Counts_2006_2025.csv"
OUT_TXT = PROCESSED / "eth_prof_auslaender_summary.txt"
OUT_CSV = PROCESSED / "eth_prof_auslaender_summary.csv"
OUT_HTML = PROCESSED / "eth_prof_auslaender_summary.html"

YEARS = [str(y) for y in range(2006, 2026)]
RANKS = {
    "Vollprofessor/innen": "Full Prof",
    "Assistenzprofessor/innen": "Assistant Prof",
}
SKIP_FACULTIES = {
    "Gesamtsumme", "Ausnahme", "SL-Stäbe und Abteilungen",
    "Ausserdep. L&F-Einheiten und Übrige",
}

LABEL_W = 42
YEAR_W = 22  # "   Total      Ausl. %"


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df[YEARS] = df[YEARS].apply(pd.to_numeric, errors="coerce")
    return df[df["Funktion"].isin(RANKS)].copy()


total_df = load(TOTAL_CSV)
foreign_df = load(FOREIGN_CSV)


def lookup(df: pd.DataFrame, faculty: str, dept: str | None, rank: str) -> pd.Series:
    mask = (df["Fachbereich"] == faculty) & (df["Funktion"] == rank)
    if dept is not None:
        mask &= df["Departement"] == dept
    sub = df.loc[mask, YEARS]
    if sub.empty:
        return pd.Series({y: float("nan") for y in YEARS})
    return sub.sum(axis=0, min_count=1)


def sum_rank(df: pd.DataFrame, rank: str) -> pd.Series:
    faculty_mask = ~df["Fachbereich"].isin(SKIP_FACULTIES)
    sub = df.loc[faculty_mask & (df["Funktion"] == rank), YEARS]
    return sub.sum(axis=0, min_count=1)


def fmt_cell(total: float, foreign: float) -> str:
    if pd.isna(total):
        return " " * YEAR_W
    f = foreign if pd.notna(foreign) else 0.0
    pct = (f / total * 100) if total else 0.0
    return f"{total:10.1f} {pct:9.1f}%"


def header_lines() -> list[str]:
    year_row = " " * LABEL_W + "|" + "|".join(f"{y:^{YEAR_W}}" for y in YEARS)
    sub_row = " " * LABEL_W + "|" + "|".join(
        f"{'Total':>10} {'Ausl. %':>10}" for _ in YEARS
    )
    return [year_row, sub_row]


def data_row(label: str, total: pd.Series, foreign: pd.Series) -> str:
    cells = "|".join(fmt_cell(total[y], foreign[y]) for y in YEARS)
    return f"{label:<{LABEL_W}}|{cells}"


def section_rule(char: str = "─") -> str:
    return char * (LABEL_W + 1 + (YEAR_W + 1) * len(YEARS) - 1)


lines: list[str] = []
title = "ETH ZURICH - PROFESSOR OVERVIEW (Total Count & Foreign %)"
bar = "=" * len(section_rule("="))
lines.append(title)
lines.append(bar)
lines.append("")
lines.extend(header_lines())
lines.append(section_rule())
lines.append("")
lines.append("ETH OVERALL")
lines.append(section_rule())
for rank_de, rank_en in RANKS.items():
    t = sum_rank(total_df, rank_de)
    f = sum_rank(foreign_df, rank_de)
    lines.append(data_row(
        {"Vollprofessor/innen": "Full Professors",
         "Assistenzprofessor/innen": "Assistant Professors"}[rank_de],
        t, f,
    ))
lines.append("")

faculties = [fac for fac in total_df["Fachbereich"].drop_duplicates()
             if fac not in SKIP_FACULTIES]
for faculty in faculties:
    lines.append(section_rule())
    lines.append("")
    lines.append(faculty.upper())
    lines.append(section_rule())
    depts = (total_df.loc[total_df["Fachbereich"] == faculty, "Departement"]
             .drop_duplicates().tolist())
    for dept in depts:
        for rank_de, rank_en in RANKS.items():
            t = lookup(total_df, faculty, dept, rank_de)
            f = lookup(foreign_df, faculty, dept, rank_de)
            if t.isna().all():
                continue
            lines.append(data_row(f"  {dept} - {rank_en}", t, f))
    lines.append("")

lines.append(bar)

text = "\n".join(lines)
OUT_TXT.write_text(text)


# -- also write a tidy CSV for machine consumption --
records = []
for rank_de, rank_en in RANKS.items():
    t = sum_rank(total_df, rank_de)
    f = sum_rank(foreign_df, rank_de)
    for y in YEARS:
        records.append({
            "Faculty": "ETH OVERALL", "Department": "", "Rank": rank_en,
            "Year": int(y), "Total": round(t[y], 1) if pd.notna(t[y]) else None,
            "Foreign": round(f[y], 1) if pd.notna(f[y]) else None,
            "Foreign %": round(f[y] / t[y] * 100, 1)
            if pd.notna(t[y]) and t[y] else None,
        })

for faculty in faculties:
    depts = (total_df.loc[total_df["Fachbereich"] == faculty, "Departement"]
             .drop_duplicates().tolist())
    for dept in depts:
        for rank_de, rank_en in RANKS.items():
            t = lookup(total_df, faculty, dept, rank_de)
            f = lookup(foreign_df, faculty, dept, rank_de)
            if t.isna().all():
                continue
            for y in YEARS:
                records.append({
                    "Faculty": faculty, "Department": dept, "Rank": rank_en,
                    "Year": int(y),
                    "Total": round(t[y], 1) if pd.notna(t[y]) else None,
                    "Foreign": round(f[y], 1) if pd.notna(f[y]) else None,
                    "Foreign %": round(f[y] / t[y] * 100, 1)
                    if pd.notna(t[y]) and t[y] else None,
                })

tidy = pd.DataFrame(records)
tidy.to_csv(OUT_CSV, index=False)

html_body = f"<pre>{text}</pre>"
OUT_HTML.write_text(html_body)

print(text)
print(f"\nWrote: {OUT_TXT.name}, {OUT_CSV.name}, {OUT_HTML.name}")

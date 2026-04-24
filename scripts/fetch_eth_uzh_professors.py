"""
FSO PxWeb API — ETH & UZH Foreign Professor Data Collector
===========================================================
Data source: Swiss Federal Statistical Office (FSO) STAT-TAB
Series:      px-x-1504040100 — Personnel of cantonal universities (UH)

Two cubes used:
  _102  →  Year × Field × Rank × University          (person counts)
  _103  →  Year × Field × Nationality × University   (person counts)

Institutions:
  70 = UZH   |   90 = ETHZ

Rank codes (Personalkategorie):
  1 = Professor/-innen (all professors, aggregated)
  2 = Übrige Dozierende (other lecturers)
  3 = Assistierende und wissenschaftliche Mitarbeitende
  4 = Direktion, administrativ-technisches Personal

Nationality codes (Staatsangehörigkeit):
  1 = Schweiz (Swiss)
  2 = Ausland (Foreign)

Note on rank granularity:
  The FSO data aggregates all professors into one category (code 1).
  Full / Associate / Assistant distinctions are NOT available in this
  public API cube. For that breakdown you would need to request
  microdata from FSO directly, or scrape ETH/UZH individual annual reports.

Years available: 1980 – 2024 (cube _102), 1980 – 2024 (cube _103)
Fetching all available years (1980–2024) for maximum coverage.
Note: FSO revised methodology in 2012, so pre-2012 data may not be directly comparable.
"""

import requests
import pandas as pd
import os
from io import StringIO

BASE_URL = "https://www.pxweb.bfs.admin.ch/api/v1/de"

CUBE_RANK        = "px-x-1504040100_102"   # rank × field × university
CUBE_NATIONALITY = "px-x-1504040100_103"   # nationality × field × university

UNIVERSITIES = {"70": "UZH", "90": "ETHZ"}


def query_cube(cube_id: str, query: dict) -> pd.DataFrame:
    """POST a query to a FSO PxWeb cube and return a DataFrame."""
    url = f"{BASE_URL}/{cube_id}/{cube_id}.px"
    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=query,
        timeout=30
    )
    response.raise_for_status()
    # FSO returns CSV with latin-1 encoding
    csv_text = response.content.decode("latin-1")
    df = pd.read_csv(StringIO(csv_text))
    return df


# ── 1. Pull nationality data (Swiss vs Foreign) ───────────────────────────────

print("Fetching nationality data (cube _103)...")

query_nat = {
    "query": [
        {"code": "Jahr",
         "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Fachbereich",
         "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Staatsangehörigkeit (Kategorie)",
         "selection": {"filter": "item", "values": ["1", "2"]}},  # Swiss + Foreign
        {"code": "Hochschule",
         "selection": {"filter": "item", "values": ["70", "90"]}},  # UZH + ETHZ
    ],
    "response": {"format": "csv"}
}

df_nat_raw = query_cube(CUBE_NATIONALITY, query_nat)
# Keep a German copy before renaming
df_nat_de = df_nat_raw.copy()
df_nat_de = df_nat_de.melt(
    id_vars=df_nat_de.columns[:3].tolist(),
    value_vars=df_nat_de.columns[3:].tolist(),
    var_name="Hochschule",
    value_name="Anzahl"
)
df_nat_de.iloc[:, 0] = df_nat_de.iloc[:, 0].astype(int)

# English version
df_nat = df_nat_raw.copy()
df_nat.columns = ["Year", "Field", "Nationality", "UZH", "ETHZ"]
df_nat = df_nat.melt(
    id_vars=["Year", "Field", "Nationality"],
    value_vars=["UZH", "ETHZ"],
    var_name="University",
    value_name="Count"
)
df_nat["Year"] = df_nat["Year"].astype(int)

print(f"  → {len(df_nat):,} rows")
print(df_nat.head(6).to_string(index=False))


# ── 2. Pull rank data (professors vs other staff) ─────────────────────────────

print("\nFetching rank/category data (cube _102)...")

query_rank = {
    "query": [
        {"code": "Jahr",
         "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Fachbereich",
         "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Personalkategorie",
         "selection": {"filter": "item", "values": ["1", "2", "3"]}},  # Prof, Lecturer, Assistant
        {"code": "Hochschule",
         "selection": {"filter": "item", "values": ["70", "90"]}},
    ],
    "response": {"format": "csv"}
}

df_rank_raw = query_cube(CUBE_RANK, query_rank)
# Keep a German copy before renaming
df_rank_de = df_rank_raw.copy()
df_rank_de = df_rank_de.melt(
    id_vars=df_rank_de.columns[:3].tolist(),
    value_vars=df_rank_de.columns[3:].tolist(),
    var_name="Hochschule",
    value_name="Anzahl"
)
df_rank_de.iloc[:, 0] = df_rank_de.iloc[:, 0].astype(int)

# English version
df_rank = df_rank_raw.copy()
df_rank.columns = ["Year", "Field", "Rank", "UZH", "ETHZ"]
df_rank = df_rank.melt(
    id_vars=["Year", "Field", "Rank"],
    value_vars=["UZH", "ETHZ"],
    var_name="University",
    value_name="Count"
)
df_rank["Year"] = df_rank["Year"].astype(int)

# Translate rank labels to English
rank_map = {
    "Professor/-innen":                               "Professors",
    "Übrige Dozierende":                              "Other Lecturers",
    "Assistierende und wissenschaftliche Mitarbeitende": "Assistants & Research Staff",
}
df_rank["Rank"] = df_rank["Rank"].map(rank_map).fillna(df_rank["Rank"])

print(f"  → {len(df_rank):,} rows")
print(df_rank.head(6).to_string(index=False))


# ── 3. Summary: foreign staff by field (faculty), all years ──────────────

print("\n── Foreign staff, by Field & University (all years) ──")

df_prof_foreign = (
    df_nat[df_nat["Nationality"] == "Ausland"]
    .copy()
)

# Total staff (Swiss + Foreign) to compute foreign share
df_total = (
    df_nat
    .groupby(["Year", "Field", "University"])["Count"]
    .sum()
    .reset_index()
    .rename(columns={"Count": "Total"})
)

df_summary = df_prof_foreign.merge(df_total, on=["Year", "Field", "University"])
df_summary["Foreign_Share_%"] = (df_summary["Count"] / df_summary["Total"] * 100).round(1)
df_summary = df_summary.rename(columns={"Count": "Foreign_Count"})

print(df_summary[df_summary["Year"] == 2024].to_string(index=False))


# ── 4. Time series: total foreign share by university ─────────────────────────

print("\n── Foreign staff share over time (all categories, UZH vs ETHZ) ──")

ts = (
    df_nat
    .groupby(["Year", "University", "Nationality"])["Count"]
    .sum()
    .reset_index()
)
ts_wide = ts.pivot_table(
    index=["Year", "University"],
    columns="Nationality",
    values="Count"
).reset_index()
ts_wide.columns.name = None
ts_wide = ts_wide.rename(columns={"Schweiz": "Swiss", "Ausland": "Foreign"})
ts_wide["Total"] = ts_wide["Swiss"] + ts_wide["Foreign"]
ts_wide["Foreign_%"] = (ts_wide["Foreign"] / ts_wide["Total"] * 100).round(1)

print(ts_wide[ts_wide["Year"].isin([1980, 1990, 2000, 2005, 2010, 2015, 2020, 2024])].to_string(index=False))


# ── 5. German summary (foreign staff by field, all years) ───────────────────

jahr_col = df_nat_de.columns[0]
fach_col = df_nat_de.columns[1]
nat_col  = df_nat_de.columns[2]

df_prof_foreign_de = df_nat_de[df_nat_de[nat_col] == "Ausland"].copy()

df_total_de = (
    df_nat_de
    .groupby([jahr_col, fach_col, "Hochschule"])["Anzahl"]
    .sum()
    .reset_index()
    .rename(columns={"Anzahl": "Total"})
)

df_summary_de = df_prof_foreign_de.merge(df_total_de, on=[jahr_col, fach_col, "Hochschule"])
df_summary_de["Auslaenderanteil_%"] = (df_summary_de["Anzahl"] / df_summary_de["Total"] * 100).round(1)
df_summary_de = df_summary_de.rename(columns={"Anzahl": "Ausland_Anzahl"})


# ── 6. Save to CSV ────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# English
df_nat.to_csv(os.path.join(RAW_DIR, "eth_uzh_staff_by_nationality_en.csv"), index=False)
df_rank.to_csv(os.path.join(RAW_DIR, "eth_uzh_staff_by_rank_en.csv"), index=False)
df_summary.to_csv(os.path.join(RAW_DIR, "eth_uzh_foreign_staff_by_field_all_years_en.csv"), index=False)

# German (original labels)
df_nat_de.to_csv(os.path.join(RAW_DIR, "eth_uzh_staff_by_nationality_de.csv"), index=False)
df_rank_de.to_csv(os.path.join(RAW_DIR, "eth_uzh_staff_by_rank_de.csv"), index=False)
df_summary_de.to_csv(os.path.join(RAW_DIR, "eth_uzh_foreign_staff_by_field_all_years_de.csv"), index=False)

print("\n✅ Saved:")
print("   eth_uzh_staff_by_nationality_en.csv              (English, all years)")
print("   eth_uzh_staff_by_rank_en.csv                     (English, all years)")
print("   eth_uzh_foreign_staff_by_field_all_years_en.csv  (English, foreign share summary)")
print("   eth_uzh_staff_by_nationality_de.csv              (Deutsch, alle Jahre)")
print("   eth_uzh_staff_by_rank_de.csv                     (Deutsch, alle Jahre)")
print("   eth_uzh_foreign_staff_by_field_all_years_de.csv  (Deutsch, Ausländeranteil)")
print("\nNote: For Full/Associate/Assistant breakdown, the public FSO cube")
print("aggregates all professors together. Request FSO microdata for finer granularity.")
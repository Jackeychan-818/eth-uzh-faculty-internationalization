"""
Multi-page PDF report: Professor Trends — ETH Zurich & University of Zurich.

Output: output/reports/Professor_Trends_Report_ETH_UZH.pdf

ETH section (from data/processed/eth_prof_auslaender_summary.csv):
  - Page 1: Overall stacked bars (Full/Asst × Swiss/Foreign) + Foreign % line.
  - Pages 2+: one page per faculty, line chart of Foreign % by rank.

UZH section (from data/raw/UZH_Dozierende_2009-2024.csv):
  - Page 1: Overall stacked bars (Swiss/Foreign Professuren) + Foreign % line.
    Professoren totals: 2009 from Kategorie=="Total" (user-supplied 2009 row is
    the Professuren sum); 2010–2024 from Kategorie.startswith("Professuren")
    picking the university-wide grand-total row per year (max Total).
  - Pages 2–8: one page per faculty, Foreign % line chart.
    2009 values come directly from the per-faculty row added that year;
    2010–2024 values come from Kategorie == "Professuren" rows under each
    Faktät block in the walked layout (same logic as scripts/build_latex_tables.py).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT_DIR = ROOT / "output" / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_PDF = OUT_DIR / "Professor_Trends_Report_ETH_UZH.pdf"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 120,
})

SWISS_COLOR = "#1f77b4"
FOREIGN_COLOR = "#d62728"
SWISS_LIGHT = "#7fb3d5"
FOREIGN_LIGHT = "#f1948a"
LINE_COLOR = "#2c3e50"


# ─────────────────────────── ETH ────────────────────────────────────────────

def load_eth() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "eth_prof_auslaender_summary.csv")


def eth_overall_page(df: pd.DataFrame) -> plt.Figure:
    """Page 1: stacked bars (Full/Asst × Swiss/Foreign) + Foreign % line."""
    over = df[df["Faculty"] == "ETH OVERALL"].copy()
    piv = over.pivot(index="Year", columns="Rank", values=["Total", "Foreign"])
    years = piv.index.values

    full_total = piv[("Total", "Full Prof")].values
    full_for = piv[("Foreign", "Full Prof")].values
    full_swiss = full_total - full_for
    asst_total = piv[("Total", "Assistant Prof")].values
    asst_for = piv[("Foreign", "Assistant Prof")].values
    asst_swiss = asst_total - asst_for

    grand_total = full_total + asst_total
    grand_for = full_for + asst_for
    foreign_pct = grand_for / grand_total * 100

    fig, ax1 = plt.subplots(figsize=(11.5, 7))

    ax1.bar(years, full_swiss, label="Full Prof — Swiss", color=SWISS_COLOR, width=0.75)
    ax1.bar(years, full_for, bottom=full_swiss, label="Full Prof — Foreign",
            color=FOREIGN_COLOR, width=0.75)
    ax1.bar(years, asst_swiss, bottom=full_swiss + full_for,
            label="Assistant Prof — Swiss", color=SWISS_LIGHT, width=0.75)
    ax1.bar(years, asst_for, bottom=full_swiss + full_for + asst_swiss,
            label="Assistant Prof — Foreign", color=FOREIGN_LIGHT, width=0.75)

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Number of professors")
    ax1.set_xticks(years)
    ax1.set_xticklabels(years, rotation=45)
    ax1.grid(True, axis="y", alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(years, foreign_pct, color=LINE_COLOR, linewidth=2.2,
             marker="o", markersize=5, label="Foreign %")
    ax2.set_ylabel("Foreign share (%)")
    ax2.set_ylim(0, 100)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", ncol=2, framealpha=0.9)

    ax1.set_title("ETH Zurich — Overall Professor Composition Trends (2006–2025)")
    fig.tight_layout()
    return fig


def eth_faculty_page(df: pd.DataFrame, faculty: str) -> plt.Figure:
    """One page per ETH faculty: Foreign % line, one series per rank."""
    sub = df[df["Faculty"] == faculty].copy()
    agg = (sub.groupby(["Rank", "Year"])
           .agg({"Total": "sum", "Foreign": "sum"})
           .reset_index())
    agg["Foreign %"] = agg["Foreign"] / agg["Total"] * 100

    fig, ax = plt.subplots(figsize=(11.5, 7))
    rank_styles = {
        "Full Prof": {"color": SWISS_COLOR, "marker": "o"},
        "Assistant Prof": {"color": FOREIGN_COLOR, "marker": "s"},
    }
    for rank, style in rank_styles.items():
        s = agg[agg["Rank"] == rank].sort_values("Year")
        if s.empty:
            continue
        ax.plot(s["Year"], s["Foreign %"], linewidth=2.2, markersize=6,
                label=rank, **style)

    ax.set_xlabel("Year")
    ax.set_ylabel("Foreign share (%)")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", framealpha=0.9)
    ax.set_title(f"{faculty} — Professor Foreign Percentage Trends (2006–2025)")

    years_all = sorted(agg["Year"].unique())
    ax.set_xticks(years_all)
    ax.set_xticklabels(years_all, rotation=45)
    fig.tight_layout()
    return fig


# ─────────────────────────── UZH ────────────────────────────────────────────

UZH_FACULTIES = [
    "Theologische Fakultät",
    "Rechtswissenschaftliche Fakultät",
    "Wirtschaftswissenschaftliche Fakultät",
    "Medizinische Fakultät",
    "Vetsuisse-Fakultät",
    "Philosophische Fakultät",
    "Mathematisch-naturwissenschaftliche Fakultät",
]

# Raw CSV uses mixed punctuation across years ("Vetsuisse-Fakultät" vs
# "Vetsuisse Fakultät"). Match on a normalised key.
def _norm(s: str) -> str:
    return s.replace("-", " ").lower().strip()


def load_uzh_overall() -> pd.DataFrame:
    """University-wide Professuren count + Foreign % per year (2009–2024)."""
    uzh = pd.read_csv(RAW / "UZH_Dozierende_2009-2024.csv")

    # 2010–2024: rows whose Kategorie starts with "Professuren"; university-wide
    # row is the one with the largest Total in that year.
    profs = uzh[uzh["Kategorie"].str.startswith("Professuren", na=False)].copy()
    uniwide = profs.loc[profs.groupby("Report_Jahr")["Total"].idxmax()].copy()
    uniwide = uniwide[["Report_Jahr", "Total", "Auslaendische_%"]]

    # 2009: per the user-supplied rows, the Kategorie == "Total" entry for 2009
    # is the Professuren sum (520). Other years' "Total" rows are all-staff and
    # not directly comparable, so only the 2009 one is picked up here.
    tot2009 = uzh[(uzh["Kategorie"] == "Total") & (uzh["Report_Jahr"] == 2009)]
    tot2009 = tot2009[["Report_Jahr", "Total", "Auslaendische_%"]]

    out = pd.concat([tot2009, uniwide], ignore_index=True)
    out = out.sort_values("Report_Jahr").reset_index(drop=True)
    out["Foreign"] = (out["Total"] * out["Auslaendische_%"] / 100).round(1)
    out["Swiss"] = (out["Total"] - out["Foreign"]).round(1)
    return out


def load_uzh_by_faculty() -> pd.DataFrame:
    """Per-faculty Professuren foreign % by year (2009–2024), long format."""
    uzh = pd.read_csv(RAW / "UZH_Dozierende_2009-2024.csv")
    records = []

    # 2009: Faculty rows appear directly (walked layout not used that year).
    fac_keys = {_norm(f): f for f in UZH_FACULTIES}
    mask_2009 = (uzh["Report_Jahr"] == 2009) & uzh["Kategorie"].map(
        lambda k: _norm(str(k)) in fac_keys
    )
    for _, row in uzh[mask_2009].iterrows():
        canon = fac_keys[_norm(row["Kategorie"])]
        records.append({
            "Year": 2009,
            "Faculty": canon,
            "Foreign %": row["Auslaendische_%"],
        })

    # 2010–2024: walked layout — faculty-name row followed by rank rows.
    # We want Kategorie == "Professuren" (or starts with "Professuren")
    # scoped to the current faculty block. Reuse the look-ahead logic:
    # reset faculty when a faculty-name row is seen; for "Professuren" rows
    # inside the block, emit a record.
    current_faculty = None
    for _, row in uzh.iterrows():
        if row["Report_Jahr"] == 2009:
            continue
        kat = str(row["Kategorie"]).strip()
        norm_kat = _norm(kat)
        if norm_kat in fac_keys:
            # Could be a walked-faculty header OR a flat supplementary row.
            current_faculty = fac_keys[norm_kat]
            # Flat supplementary row: Frauen_% is NaN and Auslaendische_% is
            # a valid percentage — treat it as Professuren for that faculty.
            if pd.isna(row["Frauen_%"]) and pd.notna(row["Auslaendische_%"]):
                records.append({
                    "Year": int(row["Report_Jahr"]),
                    "Faculty": current_faculty,
                    "Foreign %": row["Auslaendische_%"],
                })
            continue
        if current_faculty is not None and kat.startswith("Professuren"):
            if pd.notna(row["Auslaendische_%"]):
                records.append({
                    "Year": int(row["Report_Jahr"]),
                    "Faculty": current_faculty,
                    "Foreign %": row["Auslaendische_%"],
                })

    df = pd.DataFrame(records)
    # Supplementary flat rows should override earlier walked entries when both
    # exist for the same (year, faculty).
    df = df.drop_duplicates(subset=["Year", "Faculty"], keep="last")
    return df.sort_values(["Faculty", "Year"]).reset_index(drop=True)


def uzh_overall_page(df: pd.DataFrame) -> plt.Figure:
    years = df["Report_Jahr"].values
    swiss = df["Swiss"].values
    foreign = df["Foreign"].values
    pct = df["Auslaendische_%"].values

    fig, ax1 = plt.subplots(figsize=(11.5, 7))
    ax1.bar(years, swiss, label="Swiss", color=SWISS_COLOR, width=0.75)
    ax1.bar(years, foreign, bottom=swiss, label="Foreign",
            color=FOREIGN_COLOR, width=0.75)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Number of professors (Professuren)")
    ax1.set_xticks(years)
    ax1.set_xticklabels(years, rotation=45)
    ax1.grid(True, axis="y", alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(years, pct, color=LINE_COLOR, linewidth=2.2, marker="o",
             markersize=5, label="Foreign %")
    ax2.set_ylabel("Foreign share (%)")
    ax2.set_ylim(0, 100)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", framealpha=0.9)

    ax1.set_title("UZH — Overall Professor Composition Trends (2009–2024)")
    fig.tight_layout()
    return fig


def uzh_faculty_page(df: pd.DataFrame, faculty: str) -> plt.Figure:
    sub = df[df["Faculty"] == faculty].sort_values("Year")
    fig, ax = plt.subplots(figsize=(11.5, 7))
    ax.plot(sub["Year"], sub["Foreign %"], color=FOREIGN_COLOR,
            linewidth=2.2, marker="o", markersize=6, label="Foreign %")
    ax.set_xlabel("Year")
    ax.set_ylabel("Foreign share (%)")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", framealpha=0.9)
    ax.set_title(f"{faculty} — Professor Foreign Percentage Trends (2009–2024)")
    years = sorted(sub["Year"].unique())
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=45)
    fig.tight_layout()
    return fig


# ─────────────────────────── Driver ─────────────────────────────────────────

def add_page_number(fig: plt.Figure, page_num: int, total: int) -> None:
    fig.text(0.98, 0.015, f"Page {page_num} / {total}",
             ha="right", va="bottom", fontsize=9, color="#555")


def main() -> None:
    eth = load_eth()
    eth_faculties = [f for f in eth["Faculty"].unique() if f != "ETH OVERALL"]

    uzh_overall = load_uzh_overall()
    uzh_fac = load_uzh_by_faculty()

    pages = []
    pages.append(("eth_overall", lambda: eth_overall_page(eth)))
    for f in eth_faculties:
        pages.append((f"eth_{f}", lambda f=f: eth_faculty_page(eth, f)))
    pages.append(("uzh_overall", lambda: uzh_overall_page(uzh_overall)))
    for f in UZH_FACULTIES:
        pages.append((f"uzh_{f}", lambda f=f: uzh_faculty_page(uzh_fac, f)))

    total = len(pages)
    with PdfPages(OUT_PDF) as pdf:
        for i, (tag, maker) in enumerate(pages, start=1):
            fig = maker()
            add_page_number(fig, i, total)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    print(f"Wrote {OUT_PDF.relative_to(ROOT)} — {total} pages")


if __name__ == "__main__":
    main()

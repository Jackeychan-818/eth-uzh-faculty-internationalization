"""
Multi-page PDF report: Professor Trends — ETH Zurich & University of Zurich.

Output: output/reports/Professor_Trends_Report_ETH_UZH.pdf

ETH section (from data/processed/eth_prof_auslaender_summary.csv):
  - Page 1: Overall stacked bars (Full/Asst × Swiss/Foreign) + Foreign % line.
  - Pages 2+: one page per faculty, line chart of Foreign % by rank.

UZH section (from data/processed/uzh_dozierende_clean.csv, produced by
scripts/build_latex_tables.py):
  - Page 1: Overall stacked bars (Swiss/Foreign Professuren) + Foreign % line,
    sourced from Faculty == "Gesamt Universität", Rank == "Professuren".
  - Pages 2–8: one page per faculty, Foreign % line chart, sourced from
    Rank == "Professuren" filtered to that faculty.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT_DIR = ROOT / "output" / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_PDF = OUT_DIR / "Professor_Trends_Report_ETH_UZH.pdf"
OUT_PDF_DETAILED = OUT_DIR / "Professor_Trends_Report_ETH_UZH_detailed.pdf"

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

# Color scheme:
#   blue  = Full Professor / Professuren
#   red   = Assistant Professor
#   lighter shade of each = the foreign portion of that rank
FULL_COLOR = "#1f77b4"          # dark blue  — Full Prof, Swiss
FULL_LIGHT = "#7fb3d5"          # light blue — Full Prof, Foreign
ASST_COLOR = "#d62728"          # dark red   — Assistant Prof, Swiss
ASST_LIGHT = "#f1948a"          # light red  — Assistant Prof, Foreign
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

    fig, ax1 = plt.subplots(figsize=(9, 7.5))

    ax1.bar(years, full_swiss, label="Full Prof — Swiss",
            color=FULL_COLOR, width=0.75)
    ax1.bar(years, full_for, bottom=full_swiss, label="Full Prof — Foreign",
            color=FULL_LIGHT, width=0.75)
    ax1.bar(years, asst_swiss, bottom=full_swiss + full_for,
            label="Assistant Prof — Swiss", color=ASST_COLOR, width=0.75)
    ax1.bar(years, asst_for, bottom=full_swiss + full_for + asst_swiss,
            label="Assistant Prof — Foreign", color=ASST_LIGHT, width=0.75)

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


def _eth_faculty_axes(df: pd.DataFrame, faculty: str, ax: plt.Axes) -> None:
    sub = df[df["Faculty"] == faculty].copy()
    agg = (sub.groupby(["Rank", "Year"])
           .agg({"Total": "sum", "Foreign": "sum"})
           .reset_index())
    agg["Foreign %"] = agg["Foreign"] / agg["Total"] * 100

    rank_styles = {
        "Full Prof": {"color": FULL_COLOR, "marker": "o"},
        "Assistant Prof": {"color": ASST_COLOR, "marker": "s"},
    }
    for rank, style in rank_styles.items():
        s = agg[agg["Rank"] == rank].sort_values("Year")
        if s.empty:
            continue
        ax.plot(s["Year"], s["Foreign %"], linewidth=1.6, markersize=4,
                label=rank, **style)

    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.set_title(faculty, fontsize=10)
    years_all = sorted(agg["Year"].unique())
    ax.set_xticks(years_all[::3])
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)


def eth_faculty_page(df: pd.DataFrame, faculty: str) -> plt.Figure:
    """Single ETH faculty on its own page (line chart, both ranks)."""
    fig, ax = plt.subplots(figsize=(11.5, 7))
    _eth_faculty_axes(df, faculty, ax)
    ax.set_title(f"{faculty} — Professor Foreign Percentage Trends (2006–2025)",
                 fontsize=14)
    ax.set_xlabel("Year")
    ax.set_ylabel("Foreign share (%)")
    sub = df[df["Faculty"] == faculty]
    years_all = sorted(sub["Year"].unique())
    ax.set_xticks(years_all)
    ax.tick_params(axis="x", rotation=45, labelsize=10)
    ax.tick_params(axis="y", labelsize=10)
    ax.legend(loc="best", framealpha=0.9)
    fig.tight_layout()
    return fig


def eth_faculty_grid_page(df: pd.DataFrame, faculties: list[str]) -> plt.Figure:
    """All ETH faculties on one page: row 0 has 3 plots, row 1 has plots in
    cols 0 and 2 with the shared legend filling the middle cell."""
    fig = plt.figure(figsize=(11, 8.5))
    gs = fig.add_gridspec(2, 3, hspace=0.55, wspace=0.3)
    positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2)]
    axes = []
    for faculty, (r, c) in zip(faculties, positions):
        ax = fig.add_subplot(gs[r, c])
        _eth_faculty_axes(df, faculty, ax)
        axes.append(ax)
        if c == 0:
            ax.set_ylabel("Foreign %", fontsize=9)
    # Legend axis in the centre cell of row 1.
    legend_ax = fig.add_subplot(gs[1, 1])
    legend_ax.axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    legend_ax.legend(handles, labels, loc="center", fontsize=11,
                     framealpha=0.9, title="Rank", title_fontsize=11)
    fig.suptitle("ETH Zurich — Foreign Professor Share by Faculty (2006–2025)",
                 fontsize=14, fontweight="bold", y=0.98)
    return fig


# ─────────────────────────── UZH ────────────────────────────────────────────

UZH_FACULTIES = [
    "Theologische Fakultät",
    "Rechtswissenschaftliche Fakultät",
    "Wirtschaftswissenschaftliche Fakultät",
    "Medizinische Fakultät",
    "Vetsuisse Fakultät",
    "Philosophische Fakultät",
    "Mathematisch-naturwissenschaftliche Fakultät",
]
UZH_OVERALL_FACULTY = "Gesamt Universität"


def _load_uzh_clean() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "uzh_dozierende_clean.csv")


def load_uzh_overall() -> pd.DataFrame:
    """University-wide Professuren count + Foreign % per year (2009–2024)."""
    df = _load_uzh_clean()
    out = df[(df["Faculty"] == UZH_OVERALL_FACULTY)
             & (df["Rank"] == "Professuren")].copy()
    out = (out[["Year", "Total", "Auslaendische_%"]]
           .sort_values("Year").reset_index(drop=True))
    out["Foreign"] = (out["Total"] * out["Auslaendische_%"] / 100).round(1)
    out["Swiss"] = (out["Total"] - out["Foreign"]).round(1)
    return out


def load_uzh_by_faculty() -> pd.DataFrame:
    """Per-faculty Professuren foreign % by year (2009–2024), long format."""
    df = _load_uzh_clean()
    sub = df[(df["Rank"] == "Professuren")
             & (df["Faculty"].isin(UZH_FACULTIES))].copy()
    sub = sub.rename(columns={"Auslaendische_%": "Foreign %"})
    return (sub[["Year", "Faculty", "Foreign %"]]
            .sort_values(["Faculty", "Year"]).reset_index(drop=True))


def uzh_overall_page(df: pd.DataFrame) -> plt.Figure:
    years = df["Year"].values
    swiss = df["Swiss"].values
    foreign = df["Foreign"].values
    pct = df["Auslaendische_%"].values

    fig, ax1 = plt.subplots(figsize=(9, 7.5))
    ax1.bar(years, swiss, label="Professuren — Swiss",
            color=FULL_COLOR, width=0.75)
    ax1.bar(years, foreign, bottom=swiss, label="Professuren — Foreign",
            color=FULL_LIGHT, width=0.75)
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


def _uzh_faculty_axes(df: pd.DataFrame, faculty: str, ax: plt.Axes) -> None:
    sub = df[df["Faculty"] == faculty].sort_values("Year")
    # Professuren foreign-share line — light blue (foreign shade of "Full" rank).
    ax.plot(sub["Year"], sub["Foreign %"], color=FULL_LIGHT,
            linewidth=1.8, marker="o", markersize=4,
            markeredgecolor=FULL_COLOR)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.set_title(faculty, fontsize=9)
    years = sorted(sub["Year"].unique())
    ax.set_xticks(years[::3])
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)


def uzh_faculty_page(df: pd.DataFrame, faculty: str) -> plt.Figure:
    """Single UZH faculty on its own page."""
    fig, ax = plt.subplots(figsize=(11.5, 7))
    _uzh_faculty_axes(df, faculty, ax)
    ax.set_title(f"{faculty} — Professor Foreign Percentage Trends (2009–2024)",
                 fontsize=14)
    ax.set_xlabel("Year")
    ax.set_ylabel("Foreign share (%)")
    sub = df[df["Faculty"] == faculty]
    years = sorted(sub["Year"].unique())
    ax.set_xticks(years)
    ax.tick_params(axis="x", rotation=45, labelsize=10)
    ax.tick_params(axis="y", labelsize=10)
    fig.tight_layout()
    return fig


def uzh_faculty_grid_page(df: pd.DataFrame, faculties: list[str]) -> plt.Figure:
    """All UZH faculties on one page in a 2-2-3 layout via a 3x3 grid."""
    fig = plt.figure(figsize=(11, 9))
    gs = fig.add_gridspec(3, 3, hspace=0.65, wspace=0.3)
    # Row 0: faculties 0,1 in cols 0,1 (col 2 hidden)
    # Row 1: faculties 2,3 in cols 0,1 (col 2 hidden)
    # Row 2: faculties 4,5,6 across cols 0,1,2
    positions = [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1), (2, 2)]
    for faculty, (r, c) in zip(faculties, positions):
        ax = fig.add_subplot(gs[r, c])
        _uzh_faculty_axes(df, faculty, ax)
        if c == 0:
            ax.set_ylabel("Foreign %", fontsize=9)
    fig.suptitle("UZH — Foreign Professor Share by Faculty (2009–2024)",
                 fontsize=14, fontweight="bold", y=0.98)
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

    compact_pages = [
        ("eth_overall", lambda: eth_overall_page(eth)),
        ("eth_faculty_grid", lambda: eth_faculty_grid_page(eth, eth_faculties)),
        ("uzh_overall", lambda: uzh_overall_page(uzh_overall)),
        ("uzh_faculty_grid", lambda: uzh_faculty_grid_page(uzh_fac, UZH_FACULTIES)),
    ]

    detailed_pages = [("eth_overall", lambda: eth_overall_page(eth))]
    for f in eth_faculties:
        detailed_pages.append((f"eth_{f}", lambda f=f: eth_faculty_page(eth, f)))
    detailed_pages.append(("uzh_overall", lambda: uzh_overall_page(uzh_overall)))
    for f in UZH_FACULTIES:
        detailed_pages.append((f"uzh_{f}", lambda f=f: uzh_faculty_page(uzh_fac, f)))

    for out_path, pages in [(OUT_PDF, compact_pages),
                            (OUT_PDF_DETAILED, detailed_pages)]:
        total = len(pages)
        with PdfPages(out_path) as pdf:
            for i, (_tag, maker) in enumerate(pages, start=1):
                fig = maker()
                add_page_number(fig, i, total)
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
        print(f"Wrote {out_path.relative_to(ROOT)} — {total} pages")


if __name__ == "__main__":
    main()

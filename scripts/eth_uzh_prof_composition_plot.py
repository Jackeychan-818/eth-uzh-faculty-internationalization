"""Stacked bar charts: ETH (2006-2025) and UZH (2010-2024) professor composition.

- ETH: 4 segments (Full/Asst × Swiss/Foreign) from eth_prof_auslaender_summary.csv
- UZH: 2 segments (Swiss/Foreign Professuren) from UZH_Dozierende_2010-2024.csv
- Black line overlay on secondary axis shows foreign share %.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ETH_CSV = ROOT / "data" / "processed" / "eth_prof_auslaender_summary.csv"
UZH_CSV = ROOT / "data" / "raw" / "UZH_Dozierende_2010-2024.csv"
OUT_PNG = ROOT / "output" / "figures" / "eth_uzh_prof_composition.png"

COLORS = {
    "full_swiss": "#6BA3D4",
    "full_foreign": "#1F4E78",
    "asst_swiss": "#F4B084",
    "asst_foreign": "#C5504B",
    "uzh_swiss": "#6BA3D4",
    "uzh_foreign": "#1F4E78",
}

# ---------- ETH ----------
eth = pd.read_csv(ETH_CSV)
eth = eth[(eth["Faculty"] == "ETH OVERALL") & (eth["Department"].isna())]

full = eth[eth["Rank"] == "Full Prof"].set_index("Year").sort_index()
asst = eth[eth["Rank"] == "Assistant Prof"].set_index("Year").sort_index()

eth_years = full.index.to_numpy()
full_total = full["Total"].to_numpy(dtype=float)
full_foreign = full["Foreign"].fillna(0).to_numpy(dtype=float)
full_swiss = full_total - full_foreign
asst_total = asst["Total"].to_numpy(dtype=float)
asst_foreign = asst["Foreign"].fillna(0).to_numpy(dtype=float)
asst_swiss = asst_total - asst_foreign

eth_grand_total = full_total + asst_total
eth_grand_foreign = full_foreign + asst_foreign
eth_foreign_pct = np.where(
    eth_grand_total > 0, eth_grand_foreign / eth_grand_total * 100, np.nan
)

# ---------- UZH ----------
uzh_raw = pd.read_csv(UZH_CSV)
uzh_raw = uzh_raw[uzh_raw["Semester"] == "HS " + uzh_raw["Report_Jahr"].astype(str)]
# UZH labels the grand-total prof row inconsistently across years
# (e.g. "Professuren", "Professuren 3 4 5 8", "Professuren 1 2 3 4 5 7").
# Match any row starting with "Professuren" and keep the university-wide
# grand total (= max Total per year).
profs = uzh_raw[uzh_raw["Kategorie"].str.startswith("Professuren", na=False)].copy()
profs["Total"] = pd.to_numeric(profs["Total"], errors="coerce")
profs["Auslaendische_%"] = pd.to_numeric(profs["Auslaendische_%"], errors="coerce")
profs = profs.dropna(subset=["Total"])
uzh = profs.loc[profs.groupby("Report_Jahr")["Total"].idxmax()].sort_values(
    "Report_Jahr"
).reset_index(drop=True)

uzh_years = uzh["Report_Jahr"].to_numpy()
uzh_total = uzh["Total"].to_numpy(dtype=float)
uzh_foreign_pct = uzh["Auslaendische_%"].to_numpy(dtype=float)
uzh_foreign = uzh_total * uzh_foreign_pct / 100
uzh_swiss = uzh_total - uzh_foreign

# ---------- Plot ----------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 11))

# ETH
bar_kw = {"width": 0.72, "edgecolor": "white", "linewidth": 0.5}
ax1.bar(eth_years, full_swiss, label="Full Prof (Swiss)",
        color=COLORS["full_swiss"], **bar_kw)
ax1.bar(eth_years, full_foreign, bottom=full_swiss,
        label="Full Prof (Foreign)", color=COLORS["full_foreign"], **bar_kw)
ax1.bar(eth_years, asst_swiss, bottom=full_swiss + full_foreign,
        label="Assistant Prof (Swiss)", color=COLORS["asst_swiss"], **bar_kw)
ax1.bar(eth_years, asst_foreign,
        bottom=full_swiss + full_foreign + asst_swiss,
        label="Assistant Prof (Foreign)", color=COLORS["asst_foreign"], **bar_kw)

ax1.set_title("ETH Zurich - Professor Composition by Rank (2006-2025)",
              fontsize=13, fontweight="bold")
ax1.set_xlabel("Year")
ax1.set_ylabel("Number of Professors (FTE)")
ax1.set_xticks(eth_years)
ax1.tick_params(axis="x", rotation=45)
ax1.grid(axis="y", alpha=0.3)
ax1.set_axisbelow(True)

ax1r = ax1.twinx()
ax1r.plot(eth_years, eth_foreign_pct, color="black", marker="o",
          linewidth=2, markersize=5, label="Foreign %")
ax1r.set_ylabel("Foreign %")
ax1r.set_ylim(0, 100)

h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax1r.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, ncol=2)

# UZH
ax2.bar(uzh_years, uzh_swiss, label="Professor (Swiss)",
        color=COLORS["uzh_swiss"], **bar_kw)
ax2.bar(uzh_years, uzh_foreign, bottom=uzh_swiss,
        label="Professor (Foreign)", color=COLORS["uzh_foreign"], **bar_kw)

ax2.set_title("UZH - Professor Composition (2010-2024)",
              fontsize=13, fontweight="bold")
ax2.set_xlabel("Year")
ax2.set_ylabel("Number of Professors")
ax2.set_xticks(uzh_years)
ax2.tick_params(axis="x", rotation=45)
ax2.grid(axis="y", alpha=0.3)
ax2.set_axisbelow(True)

ax2r = ax2.twinx()
ax2r.plot(uzh_years, uzh_foreign_pct, color="black", marker="o",
          linewidth=2, markersize=5, label="Foreign %")
ax2r.set_ylabel("Foreign %")
ax2r.set_ylim(0, 100)

h1, l1 = ax2.get_legend_handles_labels()
h2, l2 = ax2r.get_legend_handles_labels()
ax2.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)

fig.tight_layout()
fig.savefig(OUT_PNG, dpi=200, bbox_inches="tight")
print(f"Wrote: {OUT_PNG.name}")
print(f"ETH years: {eth_years[0]}-{eth_years[-1]}, "
      f"UZH years: {uzh_years[0]}-{uzh_years[-1]}")
print(f"ETH 2025 foreign %: {eth_foreign_pct[-1]:.1f}  |  "
      f"UZH 2024 foreign %: {uzh_foreign_pct[-1]:.1f}")

"""
Ausländeranteil in den Wirtschaftswissenschaften — Universität Zürich
=====================================================================
Zeigt die Anzahl und den Anteil ausländischer Mitarbeitender im
Fachbereich Wirtschaftswissenschaften der UZH, Jahr für Jahr.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
FIG_DIR = os.path.join(ROOT, "output", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# ── 1. Daten einlesen & filtern ─────────────────────────────────────────────

df = pd.read_csv(os.path.join(RAW_DIR, "eth_uzh_staff_by_nationality_de.csv"))

# Nur UZH, nur Wirtschaftswissenschaften
mask = (df["Hochschule"] == "UZH") & (df["Fachbereich"] == "2 Wirtschaftswissenschaften")
df_econ = df[mask].copy()

# Pivot: Schweiz / Ausland nebeneinander
wide = df_econ.pivot_table(
    index="Jahr",
    columns="Staatsangehörigkeit (Kategorie)",
    values="Anzahl"
).reset_index()
wide.columns.name = None
wide["Gesamt"] = wide["Schweiz"] + wide["Ausland"]
wide["Ausländeranteil_%"] = (wide["Ausland"] / wide["Gesamt"] * 100).round(1)

# Tabelle ausgeben
print("=" * 70)
print("UZH Wirtschaftswissenschaften — Ausländeranteil")
print("=" * 70)
print(wide.to_string(index=False))
print()


# ── 2. Plot ─────────────────────────────────────────────────────────────────

fig, ax1 = plt.subplots(figsize=(12, 6))

# Balken: Anzahl Schweiz + Ausland gestapelt
ax1.bar(wide["Jahr"], wide["Schweiz"], label="Schweiz", color="#1f77b4", alpha=0.7)
ax1.bar(wide["Jahr"], wide["Ausland"], bottom=wide["Schweiz"],
        label="Ausland", color="#d62728", alpha=0.7)
ax1.set_xlabel("Jahr", fontsize=12)
ax1.set_ylabel("Anzahl Personen", fontsize=12)
ax1.set_xlim(wide["Jahr"].min() - 1, wide["Jahr"].max() + 1)

# Linie: Ausländeranteil auf zweiter y-Achse (geglättet mit Spline)
ax2 = ax1.twinx()
x = wide["Jahr"].values
y = wide["Ausländeranteil_%"].values
x_smooth = np.linspace(x.min(), x.max(), 300)
spl = make_interp_spline(x, y, k=3)
y_smooth = spl(x_smooth)
ax2.plot(x_smooth, y_smooth, color="black", linewidth=1.5, label="Ausländeranteil (%)")
ax2.scatter(x, y, color="black", s=12, zorder=5)
ax2.set_ylabel("Ausländeranteil (%)", fontsize=12)
ax2.set_ylim(0, None)

# Legende kombinieren
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=11)

ax1.set_title("UZH Wirtschaftswissenschaften — Ausländeranteil des Personals",
              fontsize=14, fontweight="bold")
ax1.grid(True, alpha=0.2)

plt.tight_layout()
out_plot = os.path.join(FIG_DIR, "uzh_econ_auslaenderanteil_plot.png")
plt.savefig(out_plot, dpi=150)
print(f"✅ Grafik gespeichert: {os.path.basename(out_plot)}")
plt.show()

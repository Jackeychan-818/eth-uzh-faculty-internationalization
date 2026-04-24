"""
Ausländeranteil des Personals: ETH Zürich vs Universität Zürich
================================================================
Liest die deutsche Nationalitätstabelle ein und zeigt den Anteil
ausländischer Mitarbeitender am gesamten Personal — Jahr für Jahr,
als Liniendiagramm (ETHZ vs UZH).

Hinweis: Die öffentliche FSO-API liefert Nationalität und Personalkategorie
in getrennten Datenwürfeln. Eine Kreuzung (z.B. «nur ausländische
Professoren») ist mit den öffentlichen Daten nicht möglich. Die Grafik
zeigt daher den Ausländeranteil über alle Personalkategorien hinweg.
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
FIG_DIR = os.path.join(ROOT, "output", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# ── 1. Daten einlesen ───────────────────────────────────────────────────────

df = pd.read_csv(os.path.join(RAW_DIR, "eth_uzh_staff_by_nationality_de.csv"))

# Pro Jahr & Hochschule & Nationalität summieren (über alle Fachbereiche)
agg = (
    df.groupby(["Jahr", "Hochschule", "Staatsangehörigkeit (Kategorie)"])["Anzahl"]
    .sum()
    .reset_index()
)

# Pivot: Schweiz / Ausland nebeneinander
wide = agg.pivot_table(
    index=["Jahr", "Hochschule"],
    columns="Staatsangehörigkeit (Kategorie)",
    values="Anzahl"
).reset_index()
wide.columns.name = None
wide["Gesamt"] = wide["Schweiz"] + wide["Ausland"]
wide["Ausländeranteil_%"] = (wide["Ausland"] / wide["Gesamt"] * 100).round(1)


# ── 2. Plot ─────────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(12, 6))

for hs, label, color in [("ETHZ", "ETH Zürich", "#1f77b4"),
                          ("UZH",  "Universität Zürich", "#d62728")]:
    sub = wide[wide["Hochschule"] == hs].sort_values("Jahr")
    ax.plot(sub["Jahr"], sub["Ausländeranteil_%"],
            marker="o", markersize=4, linewidth=2,
            color=color, label=label)

ax.set_xlabel("Jahr", fontsize=12)
ax.set_ylabel("Ausländeranteil (%)", fontsize=12)
ax.set_title("Ausländeranteil des Personals — ETH Zürich vs Universität Zürich",
             fontsize=14, fontweight="bold")
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
ax.set_xlim(wide["Jahr"].min() - 1, wide["Jahr"].max() + 1)
ax.set_ylim(0, None)

plt.tight_layout()
out_plot = os.path.join(FIG_DIR, "auslaenderanteil_plot.png")
plt.savefig(out_plot, dpi=150)
print(f"✅ Grafik gespeichert: {os.path.basename(out_plot)}")
plt.show()


# ── 3. Personalstruktur: Anteil jeder Kategorie über die Jahre ──────────────

df_rank = pd.read_csv(os.path.join(RAW_DIR, "eth_uzh_staff_by_rank_de.csv"))

# Gesamtpersonal pro Jahr & Hochschule
totals = (
    df_rank.groupby(["Jahr", "Hochschule"])["Anzahl"]
    .sum()
    .reset_index()
    .rename(columns={"Anzahl": "Gesamt"})
)

df_rank = df_rank.merge(totals, on=["Jahr", "Hochschule"])
df_rank["Anteil_%"] = (df_rank["Anzahl"] / df_rank["Gesamt"] * 100).round(1)

colors = {
    "Professor/-innen": "#1f77b4",
    "Übrige Dozierende": "#ff7f0e",
    "Assistierende und wissenschaftliche Mitarbeitende": "#2ca02c",
}

kategorien = list(colors.keys())

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

for ax, (hs, title) in zip(axes, [("ETHZ", "ETH Zürich"), ("UZH", "Universität Zürich")]):
    sub = df_rank[df_rank["Hochschule"] == hs]
    # Pivot so each category is a column
    piv = sub.pivot_table(index="Jahr", columns="Personalkategorie",
                          values="Anzahl", aggfunc="sum").reindex(columns=kategorien)
    jahre = piv.index
    bottom = None
    for kat in kategorien:
        vals = piv[kat].values
        ax.bar(jahre, vals, bottom=bottom if bottom is not None else 0,
               label=kat, color=colors[kat], width=0.8)
        bottom = vals if bottom is None else bottom + vals
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Jahr", fontsize=12)
    ax.set_xlim(df_rank["Jahr"].min() - 1.5, df_rank["Jahr"].max() + 1.5)

axes[0].set_ylabel("Anzahl Personen", fontsize=12)
axes[0].legend(fontsize=9, loc="upper left")

fig.suptitle("Personalstruktur nach Kategorie — Anzahl Personen",
             fontsize=15, fontweight="bold", y=1.02)
plt.tight_layout()
out_plot2 = os.path.join(FIG_DIR, "personalstruktur_plot.png")
plt.savefig(out_plot2, dpi=150, bbox_inches="tight")
print(f"✅ Grafik gespeichert: {os.path.basename(out_plot2)}")
plt.show()

"""Generate top-10 major funder bar chart for ICSSI 2026 abstract."""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from pathlib import Path

# Read the funders summary from the preprint results
csv_path = Path.home() / "proj/osm/osm-preprint-2026/results/funders_summary_2024_2025.csv"
df = pd.read_csv(csv_path)

# Apply major funder thresholds (same as preprint: Weibull 3% survival + OpenAlex works)
ARTICLE_THRESHOLD = 2586
WORKS_THRESHOLD = 100_000

major = df[
    (df["total_articles"] >= ARTICLE_THRESHOLD)
    & (df["aggregated_works_count"] >= WORKS_THRESHOLD)
].copy()

# Sort by open data percentage descending, take top 10
major.sort_values("open_data_pct", ascending=False, inplace=True)
top10 = major.head(10).copy()

# Reverse so highest is at top of chart
top10 = top10.iloc[::-1]
n = len(top10)

labels = [
    f"{row['funder_name']} ({row['country']})" if row["country"] else row["funder_name"]
    for _, row in top10.iterrows()
]
observed = top10["open_data_pct"].values
totals = top10["total_articles"].values

# Color: total articles on log scale using YlOrRd
norm = mcolors.LogNorm(vmin=totals.min(), vmax=totals.max())
cmap = plt.cm.YlOrRd
colors = [cmap(norm(t)) for t in totals]
colors_light = [(*c[:3], 0.35) for c in colors]

fig, ax = plt.subplots(figsize=(10, 0.45 * n + 2.0))

has_correction = "corrected_pct" in top10.columns and top10["corrected_pct"].notna().any()

if has_correction:
    corrected = top10["corrected_pct"].values
    ci_lo = top10["ci_lo_pct"].values
    ci_hi = top10["ci_hi_pct"].values

    # Background bar: corrected estimate (lighter)
    ax.barh(range(n), corrected, color=colors_light, edgecolor="grey", linewidth=0.3)
    # Foreground bar: observed (full opacity)
    ax.barh(range(n), observed, color=colors, edgecolor="grey", linewidth=0.3)
    # Error whiskers
    ax.errorbar(
        corrected, range(n),
        xerr=[corrected - ci_lo, ci_hi - corrected],
        fmt="none", ecolor="black", elinewidth=0.8, capsize=2, capthick=0.8,
    )
    max_val = ci_hi.max()

    for i, (obs_v, corr_v, hi_v) in enumerate(zip(observed, corrected, ci_hi)):
        ax.text(
            hi_v + 0.5, i,
            f"{obs_v:.1f}%\n(est. {corr_v:.1f}%)",
            va="center", fontsize=6.5, linespacing=0.9,
        )

    legend_elements = [
        Patch(facecolor=cmap(0.5), edgecolor="grey", label="Observed"),
        Patch(facecolor=(*cmap(0.5)[:3], 0.35), edgecolor="grey", label="Estimated (corrected)"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=8, framealpha=0.9)
else:
    ax.barh(range(n), observed, color=colors, edgecolor="grey", linewidth=0.3)
    max_val = observed.max()
    for i, val in enumerate(observed):
        ax.text(val + 0.3, i, f"{val:.1f}%", va="center", fontsize=8)

ax.set_yticks(range(n))
ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("% Articles with Open Data Statement", fontsize=11)
ax.set_title("Open Data Rates Among Major Funders", fontsize=13, fontweight="bold")

# Colorbar
import matplotlib.ticker as ticker
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, pad=0.02, aspect=30, shrink=0.8)
cbar.set_label("Total Funded Articles", fontsize=10)
import numpy as np
tick_vals = [3000, 5000, 10000, 20000, 30000]
tick_vals = [v for v in tick_vals if totals.min() * 0.9 <= v <= totals.max() * 1.1]
cbar.set_ticks(tick_vals)
cbar.set_ticklabels([f"{v:,}" for v in tick_vals])

# Baseline line
baseline_pct = 16.6
ax.axvline(baseline_pct, color="grey", linestyle="--", linewidth=1, alpha=0.7)
ax.text(baseline_pct + 0.3, -0.5, f"Funded baseline: {baseline_pct:.1f}%",
        fontsize=8, color="grey", va="top")

ax.set_xlim(0, max_val * 1.22)
plt.tight_layout()

out = Path("funders_top10.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {out} with {n} funders")

# Print the funders for reference
top10_display = major.head(10)[["funder_name", "country", "total_articles", "open_data_pct"]]
print(top10_display.to_string(index=False))

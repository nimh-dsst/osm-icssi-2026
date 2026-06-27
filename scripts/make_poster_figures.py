#!/usr/bin/env python3
"""Generate poster-tuned open-data figures for the ICSSI 2026 poster.

Reads the precomputed funder/journal summary CSVs vendored in this repo's
``results/`` and emits wide, large-label PNGs straight into
``latex-poster/figures/``.

Design (poster-tuned, distinct from the print-sized preprint charts):
  - Horizontal dual bars per entity:
      * light bar  = corrected_pct (estimated, accounts for XML undercount)
      * solid bar  = open_data_pct (observed; census-exact, no interval)
      * whiskers   = 95% imputation interval on the corrected estimate
  - Single forest-green accent (matches the poster), no colorbar -- legible at
    poster distance.
  - Large Roboto fonts (bundled TTFs) to match the poster typography.
  - Funders: MAJOR funders only -- those with >= MIN_WORKS total works indexed
    in OpenAlex AND above a Weibull-derived funded-article size threshold --
    so peer agencies (NIH, NSF, UKRI, ...) are compared head-to-head. This
    mirrors the preprint's Figure 1 filter (--min-works-figure 100000,
    --figure-survival 0.03) and excludes smaller / regional funders (e.g. the
    National Science Foundation of Sri Lanka) from the headline ranking.
    Displayed ranked by observed open-data rate.
  - Journals: top-N journals by observed open-data rate (the leaders),
    among journals with a minimum article count.

Run:  uv run --no-project python scripts/make_poster_figures.py
  or:  ~/proj/osm/venv/bin/python scripts/make_poster_figures.py
"""
from __future__ import annotations

import os
from pathlib import Path

# Use a writable matplotlib cache (the default ~/.matplotlib may be read-only
# under sandboxing).
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "mpl"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
REPO = Path(__file__).resolve().parent.parent
FONTS_DIR = REPO / "scripts" / "fonts"
FIG_DIR = REPO / "latex-poster" / "figures"
DATA_DIR = Path(os.environ.get("OSM_RESULTS_DIR", REPO / "results"))
FUNDERS_CSV = DATA_DIR / "funders_summary_2024_2025.csv"
JOURNALS_CSV = DATA_DIR / "journals_summary_2024_2025.csv"

# --------------------------------------------------------------------------- #
# Style
# --------------------------------------------------------------------------- #
GREEN = "#38761d"          # poster title / accent green
GREEN_LIGHT = "#a8d08d"    # estimated (corrected) bar
INK = "#222222"            # text / axes
GREY = "#9aa0a6"           # baseline line / muted

N_JOURNALS = 18
FUNDER_BASELINE = 16.6     # funded-article open-data baseline (%)
JOURNAL_BASELINE = 8.7     # overall open-data baseline (%)
MIN_JOURNAL_ARTICLES = 150

# "Major funder" filter for the headline funders figure (mirrors the preprint
# Figure 1: --min-works-figure 100000 --figure-survival 0.03). A funder must
# have at least MIN_WORKS total works indexed in OpenAlex (overall size) AND
# be above the Weibull FIG_SURVIVAL article-count threshold.
MIN_WORKS = 100_000
FIG_SURVIVAL = 0.03
FIT_MIN_ARTICLES = 100     # min articles for the Weibull fit (matches preprint)
FALLBACK_ART_THRESHOLD = 2586  # preprint's Weibull-3% threshold for this dataset


def _major_funder_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Restrict to major funders, matching the preprint's Figure 1 logic."""
    counts = df["total_articles"].to_numpy()
    counts = counts[counts >= FIT_MIN_ARTICLES]
    try:
        from scipy.stats import weibull_min
        shape, loc, scale = weibull_min.fit(np.log(counts))
        art_thr = int(np.exp(weibull_min.isf(FIG_SURVIVAL, shape, loc=loc, scale=scale)))
    except Exception:
        art_thr = FALLBACK_ART_THRESHOLD
    sub = df[(df["aggregated_works_count"] >= MIN_WORKS)
             & (df["total_articles"] >= art_thr)]
    return sub.copy(), art_thr


def _register_roboto() -> str:
    """Register the bundled Roboto TTFs; return the family name to use."""
    if not FONTS_DIR.exists():
        return "DejaVu Sans"
    for ttf in FONTS_DIR.glob("Roboto-*.ttf"):
        font_manager.fontManager.addfont(str(ttf))
    try:
        font_manager.findfont("Roboto", fallback_to_default=False)
        return "Roboto"
    except Exception:
        return "DejaVu Sans"


def _apply_rc(family: str) -> None:
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 22,
            "text.color": INK,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "axes.linewidth": 1.2,
            "svg.fonttype": "none",
        }
    )


# Compact display names for long funder titles.
FUNDER_SHORT = {
    "Agence Nationale de la Recherche": "Agence Nationale de la Recherche",
    "Bundesministerium fur Bildung und Forschung": "Fed. Min. of Education & Research",
    "Natural Sciences and Engineering Research Council of Canada": "Natural Sci. & Eng. Research Council",
    "European Regional Development Fund": "European Regional Development Fund",
    "Canadian Institutes of Health Research": "Canadian Inst. of Health Research",
    "National Natural Science Foundation of China": "Natl. Natural Science Foundation",
    "National Institutes of Health": "National Institutes of Health (NIH)",
    "UK Research and Innovation": "UK Research and Innovation",
    "National Key Research and Development Program": "China Natl. Key R&D Program",
    "Deutsche Forschungsgemeinschaft": "Deutsche Forschungsgemeinschaft",
    "European Commission": "European Commission",
    "National Science Foundation": "Natl. Science Foundation (NSF)",
    "Japan Society for the Promotion of Science": "Japan Soc. for Promotion of Science",
    "National Research Foundation of Korea": "Natl. Research Foundation of Korea",
    "Wellcome Trust": "Wellcome Trust",
    "National Institute for Health Research": "UK Natl. Inst. for Health Research",
    "Swiss National Science Foundation": "Swiss Natl. Science Foundation",
    "National Council for Scientific and Technological Development (CNPq)": "CNPq",
    "National Science Foundation of Sri Lanka": "Natl. Science Foundation",
    "National Research Foundation": "National Research Foundation",
    "Fundamental Research Funds for the Central Universities": "China Fundamental Research Funds",
    "Coordenacao de Aperfeicoamento de Pessoal de Nivel Superior": "CAPES",
    "Swedish Research Council": "Swedish Research Council",
    "China Postdoctoral Science Foundation": "China Postdoctoral Sci. Foundation",
}


def _shorten_journal(name: str, limit: int = 38) -> str:
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def _draw(
    df: pd.DataFrame,
    labels: list[str],
    baseline: float,
    xlabel: str,
    out_path: Path,
    figsize: tuple[float, float],
    xpad: float = 1.30,
) -> None:
    """Render a poster dual-bar chart (highest value at the top)."""
    # Reverse so the highest-rate row sits at the top of the chart.
    df = df.iloc[::-1].reset_index(drop=True)
    labels = labels[::-1]
    n = len(df)
    observed = df["open_data_pct"].to_numpy()
    corrected = df["corrected_pct"].to_numpy()
    ci_lo = df["ci_lo_pct"].to_numpy()
    ci_hi = df["ci_hi_pct"].to_numpy()

    fig, ax = plt.subplots(figsize=figsize)
    y = range(n)
    bar_h = 0.74

    # Estimated (corrected) bar behind, observed in front.
    ax.barh(y, corrected, height=bar_h, color=GREEN_LIGHT, edgecolor=GREEN,
            linewidth=1.0, zorder=2)
    ax.barh(y, observed, height=bar_h, color=GREEN, edgecolor=GREEN,
            linewidth=1.0, zorder=3)
    # Imputation-interval whiskers on the corrected estimate. Clamp arms ≥0
    # (ci_*_pct are full precision while corrected is shown coarser, so rounding
    # can make an arm marginally negative). Rows with no imputation interval have
    # NaN ci_lo/ci_hi (no correction applied → no imputation uncertainty); their
    # whiskers are skipped by matplotlib.
    ax.errorbar(corrected, list(y),
                xerr=[np.clip(corrected - ci_lo, 0, None),
                      np.clip(ci_hi - corrected, 0, None)],
                fmt="none", ecolor=INK, elinewidth=1.6, capsize=5, capthick=1.6,
                zorder=4)

    # Value annotation past the longest extent of each row. ci_hi is NaN where
    # no imputation interval applies; ignore NaN when sizing.
    max_ci = float(np.nanmax(np.concatenate([ci_hi, corrected, observed])))
    pad = max_ci * 0.012
    for i in range(n):
        end = float(np.nanmax([observed[i], corrected[i], ci_hi[i]]))
        ax.text(end + pad, i, f"{observed[i]:.0f}% (est. {corrected[i]:.0f}%)",
                va="center", ha="left", fontsize=19, color=INK, zorder=5)

    # Baseline.
    ax.axvline(baseline, color=GREY, linestyle="--", linewidth=2.0, zorder=1)
    ax.text(baseline, n - 0.35, f"  baseline {baseline:.1f}%", color=GREY,
            fontsize=19, va="bottom", ha="left", style="italic")

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=23)
    ax.set_ylim(-0.7, n - 0.1)
    ax.set_xlim(0, max_ci * xpad)
    ax.set_xlabel(xlabel, fontsize=26, labelpad=10)
    ax.tick_params(axis="x", labelsize=21, length=6)
    ax.tick_params(axis="y", length=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color="#e3e3e3", linewidth=1.0)

    legend = [
        Patch(facecolor=GREEN, edgecolor=GREEN, label="Observed (PDF + XML)"),
        Patch(facecolor=GREEN_LIGHT, edgecolor=GREEN, label="Corrected for XML undercount"),
    ]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 1.0),
              ncol=2, fontsize=22, frameon=False, handlelength=1.4,
              columnspacing=2.2)

    fig.tight_layout(pad=0.6)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out_path}  ({n} rows)")


def make_funders() -> None:
    df = pd.read_csv(FUNDERS_CSV)
    top, art_thr = _major_funder_filter(df)
    top = top.sort_values("open_data_pct", ascending=False).reset_index(drop=True)
    print(f"  major funders: {len(top)} "
          f"(works>={MIN_WORKS:,} and articles>={art_thr})")
    country_fix = {"LK": "Sri Lanka", "USA": "USA", "UK": "UK", "EU": "EU"}
    labels = [
        f"{FUNDER_SHORT.get(r.funder_name, r.funder_name)}"
        + (f" · {country_fix.get(r.country, r.country)}"
           if isinstance(r.country, str) and r.country else "")
        for r in top.itertuples()
    ]
    _draw(top, labels, FUNDER_BASELINE,
          "% of funded articles with an open-data statement",
          FIG_DIR / "funders_open_data_2024_2025.png",
          figsize=(15.0, 13.8))


def make_journals() -> None:
    df = pd.read_csv(JOURNALS_CSV)
    df = df[df["total_articles"] >= MIN_JOURNAL_ARTICLES]
    top = df.sort_values("open_data_pct", ascending=False).head(N_JOURNALS).copy()
    top = top.reset_index(drop=True)
    labels = [_shorten_journal(j) for j in top["journal"]]
    _draw(top, labels, JOURNAL_BASELINE,
          "% of articles with an open-data statement",
          FIG_DIR / "journals_open_data_2024_2025.png",
          figsize=(15.0, 16.5), xpad=1.16)


def main() -> None:
    family = _register_roboto()
    _apply_rc(family)
    print(f"font family: {family}")
    make_funders()
    make_journals()


if __name__ == "__main__":
    main()

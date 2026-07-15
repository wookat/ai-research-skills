---
name: data-visualization
description: >
  Create publication-quality figures with matplotlib/seaborn (Python) or ggplot2 (R).
  Covers multi-panel layouts, colorblind-safe palettes, and journal export settings.
tags:
  - visualization
  - matplotlib
  - seaborn
  - ggplot2
  - publication-figures
  - color-palettes
version: "1.0.0"
authors:
  - name: "awesome-rosetta-skills contributors"
    github: "@awesome-rosetta-skills"
license: "MIT"
platforms:
  - claude-code
  - codex
  - gemini-cli
  - cursor
dependencies:
  python:
    - matplotlib>=3.7.0
    - seaborn>=0.12.0
    - numpy>=1.24.0
    - pandas>=2.0.0
    - scipy>=1.10.0
    - palettable>=3.3.3
last_updated: "2026-03-17"
---

# Data Visualization

Produce figures that meet journal submission standards: correct DPI, font sizes,
line widths, colorblind-friendly palettes, and vector/raster export formats.

---

## Journal Figure Standards

| Journal Family | Single Column | Double Column | DPI | Preferred Format |
|---|---|---|---|---|
| Nature / Science | 89 mm | 183 mm | 300 | TIFF / EPS |
| Cell Press | 85 mm | 170 mm | 300 | PDF / TIFF |
| PLOS ONE | 83 mm | 171 mm | 300 | TIFF / EPS |
| ACS Journals | 84 mm | 176 mm | 600 | TIFF |
| General use | 3.5 in | 7 in | 300 | PDF / SVG |

---

## Setup

```bash
pip install matplotlib seaborn numpy pandas scipy palettable
# For LaTeX rendering in labels (optional but recommended)
# Requires a local LaTeX installation (e.g. TeX Live or MiKTeX)
```

---

## Publication Style Foundation

```python
"""
pub_style.py
Reusable publication-quality matplotlib configuration.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Optional, Tuple, List, Union


# ─────────────────────────────────────────────
# Color Palettes (colorblind-friendly)
# ─────────────────────────────────────────────

# Okabe-Ito (8 colors, safe for all common color-vision deficiencies)
OKABE_ITO = [
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermilion
    "#CC79A7",  # reddish purple
    "#000000",  # black
]

# Wong palette (alternative 8-color colorblind-safe set)
WONG = [
    "#000000",
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]

# Discrete palettes from palettable (ColorBrewer)
def get_colorbrewer(name: str = "Set2", n: int = 8) -> List[str]:
    """Return hex colors from a ColorBrewer palette."""
    try:
        import palettable
        palette = getattr(palettable.colorbrewer.qualitative, f"{name}_{n}")
        return palette.hex_colors
    except Exception:
        return OKABE_ITO[:n]


# ─────────────────────────────────────────────
# Core Style Setup
# ─────────────────────────────────────────────

def setup_publication_style(
    font_size: int = 8,
    font_family: str = "sans-serif",
    use_latex: bool = False,
    style: str = "whitegrid",
    context: str = "paper",
    color_palette: Optional[List[str]] = None,
    line_width: float = 0.75,
    tick_major_size: float = 3.0,
    axes_spines_right: bool = False,
    axes_spines_top: bool = False,
) -> None:
    """
    Configure matplotlib/seaborn for publication-quality output.

    Parameters
    ----------
    font_size : int
        Base font size in pt. Typical range: 6–10 pt for journals.
    font_family : str
        Font family ('sans-serif', 'serif').
    use_latex : bool
        Render text with LaTeX (requires a local LaTeX install).
    style : str
        Seaborn style: 'whitegrid', 'ticks', 'white', 'dark'.
    context : str
        Seaborn context: 'paper', 'notebook', 'talk', 'poster'.
    color_palette : list, optional
        List of hex colors. Defaults to Okabe-Ito.
    line_width : float
        Default line width for axes and lines.
    tick_major_size : float
        Major tick length in pt.
    axes_spines_right : bool
        Whether to show right spine.
    axes_spines_top : bool
        Whether to show top spine.
    """
    if color_palette is None:
        color_palette = OKABE_ITO

    sns.set_theme(style=style, context=context, palette=color_palette,
                  font=font_family, font_scale=1.0)

    rc_params = {
        # Font
        "font.size":          font_size,
        "axes.titlesize":     font_size,
        "axes.labelsize":     font_size,
        "xtick.labelsize":    font_size - 1,
        "ytick.labelsize":    font_size - 1,
        "legend.fontsize":    font_size - 1,
        "legend.title_fontsize": font_size,
        # Lines
        "lines.linewidth":    line_width * 1.5,
        "axes.linewidth":     line_width,
        "patch.linewidth":    line_width,
        # Ticks
        "xtick.major.size":   tick_major_size,
        "ytick.major.size":   tick_major_size,
        "xtick.minor.size":   tick_major_size * 0.6,
        "ytick.minor.size":   tick_major_size * 0.6,
        "xtick.major.width":  line_width,
        "ytick.major.width":  line_width,
        # Spines
        "axes.spines.right":  axes_spines_right,
        "axes.spines.top":    axes_spines_top,
        # Saving
        "savefig.dpi":        300,
        "savefig.bbox":       "tight",
        "savefig.pad_inches": 0.02,
        # Legend
        "legend.frameon":     False,
        "legend.handlelength": 1.5,
        # LaTeX
        "text.usetex":        use_latex,
    }
    mpl.rcParams.update(rc_params)


def mm_to_inches(mm: float) -> float:
    """Convert millimetres to inches for figure sizing."""
    return mm / 25.4


def save_figure(
    fig: plt.Figure,
    path: str,
    formats: Optional[List[str]] = None,
    dpi: int = 300,
) -> None:
    """
    Save figure to one or more formats.

    Parameters
    ----------
    fig : matplotlib Figure
    path : str
        Base path without extension (e.g. 'figures/fig1').
    formats : list, optional
        Defaults to ['pdf', 'tiff']. Options: 'pdf', 'svg', 'tiff', 'png', 'eps'.
    dpi : int
        Resolution for raster formats.
    """
    if formats is None:
        formats = ["pdf", "tiff"]
    for fmt in formats:
        full_path = f"{path}.{fmt}"
        fig.savefig(full_path, dpi=dpi, format=fmt)
        print(f"Saved: {full_path}")
```

---

## Figure 1 — Scatter Plot with Regression Line

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pub_style import setup_publication_style, mm_to_inches, save_figure, OKABE_ITO

setup_publication_style(font_size=8)

rng = np.random.default_rng(42)
n = 80
x = rng.normal(5, 1.5, n)
y = 2.3 * x + rng.normal(0, 2, n)
group = rng.choice(["A", "B"], size=n)
df = pd.DataFrame({"x": x, "y": y, "group": group})

fig, ax = plt.subplots(figsize=(mm_to_inches(89), mm_to_inches(70)))

colors = {"A": OKABE_ITO[0], "B": OKABE_ITO[1]}
for grp, gdf in df.groupby("group"):
    ax.scatter(gdf["x"], gdf["y"], color=colors[grp], s=18, alpha=0.75,
               linewidths=0.3, edgecolors="white", label=grp, zorder=3)

    # Per-group regression line
    slope, intercept, r, p, se = stats.linregress(gdf["x"], gdf["y"])
    x_line = np.linspace(gdf["x"].min(), gdf["x"].max(), 100)
    ax.plot(x_line, slope * x_line + intercept, color=colors[grp],
            linewidth=1.2, linestyle="--")
    ax.annotate(f"r={r:.2f}", xy=(x_line[-1], slope * x_line[-1] + intercept),
                fontsize=6, color=colors[grp], ha="left")

ax.set_xlabel("Predictor variable (units)")
ax.set_ylabel("Outcome variable (units)")
ax.legend(title="Group", loc="upper left", markerscale=1.2)
ax.set_title("Figure 1: Group-stratified regression")

fig.tight_layout()
save_figure(fig, "figure1_scatter", formats=["pdf", "tiff"])
plt.show()
```

---

## Figure 2 — Violin + Strip Plot (Multi-Group Comparison)

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pub_style import setup_publication_style, mm_to_inches, save_figure, OKABE_ITO

setup_publication_style(font_size=8)

rng = np.random.default_rng(7)
data = pd.DataFrame({
    "value": np.concatenate([
        rng.normal(5, 1.2, 40),
        rng.normal(6.5, 1.5, 40),
        rng.normal(4.2, 0.9, 40),
        rng.normal(7.0, 2.0, 40),
    ]),
    "condition": ["Control"] * 40 + ["Drug A"] * 40 + ["Drug B"] * 40 + ["Combo"] * 40,
})

fig, ax = plt.subplots(figsize=(mm_to_inches(120), mm_to_inches(80)))

palette = {c: OKABE_ITO[i] for i, c in enumerate(data["condition"].unique())}

# Violin (distribution)
sns.violinplot(
    data=data, x="condition", y="value",
    palette=palette, inner=None, linewidth=0.8,
    cut=0, ax=ax,
)

# Strip (individual data points)
sns.stripplot(
    data=data, x="condition", y="value",
    color="black", size=2.5, alpha=0.5, jitter=True,
    ax=ax, zorder=3,
)

# Median markers
for i, (cond, grp) in enumerate(data.groupby("condition")):
    ax.plot(i, grp["value"].median(), marker="D", color="white",
            markeredgecolor="black", markeredgewidth=0.8, markersize=5, zorder=4)

ax.set_xlabel("Treatment condition")
ax.set_ylabel("Response (arbitrary units)")
ax.set_title("Figure 2: Distribution of responses by condition")

# Significance bracket example
ax.annotate("", xy=(1, 9.5), xytext=(3, 9.5),
            arrowprops=dict(arrowstyle="-", color="black", lw=0.8))
ax.text(2, 9.7, "***", ha="center", va="bottom", fontsize=9)

fig.tight_layout()
save_figure(fig, "figure2_violin", formats=["pdf", "tiff"])
plt.show()
```

---

## Figure 3 — Multi-Panel Figure with GridSpec

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy.cluster import hierarchy
from scipy.spatial.distance import pdist
from pub_style import setup_publication_style, mm_to_inches, save_figure, OKABE_ITO

setup_publication_style(font_size=8)

rng = np.random.default_rng(123)

# ── Data ──────────────────────────────────────────────────────────────────
n_genes, n_samples = 30, 20
expr_matrix = rng.normal(0, 1, (n_genes, n_samples))
# Add a biologically meaningful signal
expr_matrix[:10, :10] += 2.5

labels_col = ["Ctrl"] * 10 + ["Treat"] * 10
time_x = np.linspace(0, 4 * np.pi, 100)
curve_a = np.sin(time_x) + rng.normal(0, 0.15, 100)
curve_b = np.cos(time_x) + rng.normal(0, 0.15, 100)

# ── Layout: 2 rows × 3 cols ───────────────────────────────────────────────
fig = plt.figure(figsize=(mm_to_inches(183), mm_to_inches(120)))
gs = gridspec.GridSpec(
    2, 3,
    figure=fig,
    hspace=0.45,
    wspace=0.38,
    width_ratios=[1.5, 1, 1],
)

# Panel A — heatmap with clustering
ax_a = fig.add_subplot(gs[:, 0])   # spans both rows
linkage = hierarchy.linkage(pdist(expr_matrix), method="ward")
order = hierarchy.leaves_list(linkage)
cmap = sns.diverging_palette(220, 20, as_cmap=True)
im = ax_a.imshow(
    expr_matrix[order, :], aspect="auto", cmap=cmap,
    vmin=-3, vmax=3, interpolation="nearest",
)
ax_a.set_xlabel("Sample")
ax_a.set_ylabel("Gene (clustered)")
ax_a.set_title("A", loc="left", fontweight="bold")
cbar = fig.colorbar(im, ax=ax_a, fraction=0.046, pad=0.04)
cbar.set_label("Z-score", fontsize=7)
cbar.ax.tick_params(labelsize=6)

# Panel B — line plot
ax_b = fig.add_subplot(gs[0, 1])
ax_b.plot(time_x, curve_a, color=OKABE_ITO[0], linewidth=1.0, label="Condition A")
ax_b.plot(time_x, curve_b, color=OKABE_ITO[1], linewidth=1.0, linestyle="--", label="Condition B")
ax_b.fill_between(time_x, curve_a - 0.3, curve_a + 0.3, color=OKABE_ITO[0], alpha=0.15)
ax_b.set_xlabel("Time (s)")
ax_b.set_ylabel("Signal")
ax_b.legend(loc="upper right", fontsize=6)
ax_b.set_title("B", loc="left", fontweight="bold")

# Panel C — bar chart with error bars
ax_c = fig.add_subplot(gs[0, 2])
means = rng.uniform(3, 8, 4)
sems  = rng.uniform(0.3, 1.0, 4)
bars = ax_c.bar(
    range(4), means, yerr=sems,
    color=OKABE_ITO[:4],
    capsize=3, linewidth=0.7, edgecolor="black", width=0.6,
    error_kw={"linewidth": 0.8},
)
ax_c.set_xticks(range(4))
ax_c.set_xticklabels(["Ctrl", "A", "B", "C"], fontsize=7)
ax_c.set_ylabel("Mean ± SEM")
ax_c.set_title("C", loc="left", fontweight="bold")

# Panel D — scatter
ax_d = fig.add_subplot(gs[1, 1])
x4 = rng.normal(0, 1, 60)
y4 = 0.7 * x4 + rng.normal(0, 0.8, 60)
ax_d.scatter(x4, y4, color=OKABE_ITO[2], s=15, alpha=0.7, linewidths=0)
ax_d.set_xlabel("Variable X")
ax_d.set_ylabel("Variable Y")
ax_d.set_title("D", loc="left", fontweight="bold")

# Panel E — histogram
ax_e = fig.add_subplot(gs[1, 2])
data_e = rng.normal(5, 1.5, 200)
ax_e.hist(data_e, bins=20, color=OKABE_ITO[3], edgecolor="white", linewidth=0.4)
ax_e.axvline(data_e.mean(), color="black", linestyle="--", linewidth=0.9, label="Mean")
ax_e.set_xlabel("Value")
ax_e.set_ylabel("Count")
ax_e.legend(fontsize=6)
ax_e.set_title("E", loc="left", fontweight="bold")

save_figure(fig, "figure3_multipanel", formats=["pdf", "tiff"])
plt.show()
```

---

## R / ggplot2 Publication Figure

```r
# publication_figure.R
# Requires: ggplot2, cowplot, ggbeeswarm, RColorBrewer

library(ggplot2)
library(cowplot)
library(dplyr)

# Colorblind-safe palette (Okabe-Ito)
okabe_ito <- c(
  "#E69F00", "#56B4E9", "#009E73",
  "#F0E442", "#0072B2", "#D55E00", "#CC79A7"
)

# ── Theme ─────────────────────────────────────────────────────────────────
pub_theme <- theme_cowplot(font_size = 8) +
  theme(
    axis.line        = element_line(linewidth = 0.4),
    axis.ticks       = element_line(linewidth = 0.4),
    axis.ticks.length = unit(2, "pt"),
    legend.key.size  = unit(8, "pt"),
    plot.title       = element_text(face = "bold", size = 8),
    strip.text       = element_text(size = 7),
  )

# ── Simulate data ─────────────────────────────────────────────────────────
set.seed(42)
df <- data.frame(
  group    = rep(c("Control", "Drug A", "Drug B"), each = 50),
  response = c(rnorm(50, 5, 1.2), rnorm(50, 7, 1.5), rnorm(50, 4, 0.9)),
  time     = rep(1:50, 3)
)

# ── Panel 1: Violin + jitter ──────────────────────────────────────────────
p1 <- ggplot(df, aes(x = group, y = response, fill = group)) +
  geom_violin(trim = FALSE, alpha = 0.7, linewidth = 0.4) +
  geom_jitter(width = 0.15, size = 0.8, alpha = 0.5, color = "black") +
  stat_summary(fun = median, geom = "crossbar",
               width = 0.4, linewidth = 0.6, color = "white") +
  scale_fill_manual(values = okabe_ito[1:3]) +
  labs(x = NULL, y = "Response (a.u.)", title = "A") +
  pub_theme +
  theme(legend.position = "none")

# ── Panel 2: Line plot with ribbon ───────────────────────────────────────
df_time <- df %>%
  group_by(group, time) %>%
  summarise(mean = mean(response), se = sd(response) / sqrt(n()), .groups = "drop")

p2 <- ggplot(df_time, aes(x = time, y = mean, color = group, fill = group)) +
  geom_ribbon(aes(ymin = mean - se, ymax = mean + se), alpha = 0.15, linewidth = 0) +
  geom_line(linewidth = 0.6) +
  scale_color_manual(values = okabe_ito[1:3]) +
  scale_fill_manual(values  = okabe_ito[1:3]) +
  labs(x = "Time (arbitrary)", y = "Mean ± SE", title = "B",
       color = "Group", fill = "Group") +
  pub_theme +
  theme(legend.position = c(0.7, 0.85))

# ── Combine panels ────────────────────────────────────────────────────────
combined <- plot_grid(p1, p2, ncol = 2, align = "hv", axis = "tblr")

# ── Save ──────────────────────────────────────────────────────────────────
ggsave("figure_ggplot2.pdf",  combined, width = 183, height = 90, units = "mm", dpi = 300)
ggsave("figure_ggplot2.tiff", combined, width = 183, height = 90, units = "mm", dpi = 300,
       compression = "lzw")
```

---

## Common Export Formats

| Format | Best For | Notes |
|---|---|---|
| PDF | Vector; LaTeX inclusion | Infinitely scalable, small file |
| SVG | Web, Inkscape editing | Editable in vector tools |
| TIFF | Journal submission | Use LZW compression to reduce size |
| EPS | Legacy journal systems | Avoid transparency |
| PNG | Web / presentations | 300 DPI minimum for print |

---

## Quick Palette Reference

```python
from pub_style import OKABE_ITO, get_colorbrewer

# Colorblind-safe qualitative (≤8 groups)
colors = OKABE_ITO

# Sequential (e.g. heatmaps)
import matplotlib.pyplot as plt
plt.cm.viridis   # perceptually uniform, colorblind-safe
plt.cm.cividis   # optimised for deuteranopia / protanopia

# Diverging (e.g. correlation matrices, fold-change)
plt.cm.RdBu_r    # red–white–blue reversed
plt.cm.bwr       # blue–white–red

# From ColorBrewer
cb_colors = get_colorbrewer("Set2", n=8)   # qualitative
cb_seq    = get_colorbrewer("Blues", n=9)  # sequential (via palettable)
```

---

## Accessibility Checklist

- [ ] All colors distinguishable in grayscale (for B/W printing)
- [ ] No red-green combinations as sole encoding (affects ~8% of males)
- [ ] Font size ≥ 6 pt in final printed figure
- [ ] Sufficient contrast ratio (WCAG AA: ≥4.5:1 for text)
- [ ] Data are shown (not just summaries) wherever possible
- [ ] Error bars labelled in caption (SD, SEM, 95% CI)

---
name: meta-analysis
description: >
  Use this Skill to pool effect sizes across studies: fixed/random-effects models,
  heterogeneity tests (I², Cochran Q), forest plot, funnel plot, Egger test,
  and subgroup analysis using pymare or manual computation.
tags:
  - universal
  - meta-analysis
  - effect-sizes
  - heterogeneity
  - forest-plot
version: "1.0.0"
authors:
  - name: awesome-rosetta-skills contributors
    github: "@xjtulyc"
license: "MIT"
platforms:
  - claude-code
  - codex
  - gemini-cli
  - cursor
dependencies:
  python:
    - pymare>=0.8
    - numpy>=1.23
    - scipy>=1.9
    - matplotlib>=3.6
    - pandas>=1.5
last_updated: "2026-03-17"
status: stable
---

# Meta-Analysis: Pooling Effect Sizes Across Studies

> **TL;DR** — Pool effect sizes from multiple studies using fixed-effects or
> random-effects models, quantify heterogeneity (I², Cochran Q, τ²), produce
> publication-quality forest plots and funnel plots, test for publication bias
> (Egger, trim-and-fill), and run subgroup / moderator analyses.

---

## When to Use This Skill

Use this Skill when you have:

- A completed systematic review with ≥ 2 quantitative studies on the same outcome
- A set of effect sizes (Cohen's d, Hedges' g, OR, RR, correlation r) and their
  standard errors or sample sizes
- A need to communicate pooled estimates with forest or funnel plots
- Questions about heterogeneity between studies or subgroup differences

| Task | Use case |
|---|---|
| Fixed-effects pooling | Studies estimate the same true effect; low heterogeneity |
| Random-effects pooling | True effects vary across studies; I² > 25% |
| Heterogeneity decomposition | Understand sources of between-study variance |
| Forest plot | Visualize study-level and pooled estimates |
| Funnel plot + Egger test | Detect small-study effects / publication bias |
| Subgroup analysis | Test whether effect differs by moderator variable |

---

## Background & Key Concepts

### Effect Size Types

| Measure | Formula | Use case |
|---|---|---|
| Cohen's d | (M₁ − M₂) / SD_pooled | Two-group continuous outcome |
| Hedges' g | d × correction factor J(df) | Small samples (n < 20 per group) |
| Odds Ratio (OR) | (a/b) / (c/d) in 2×2 table | Binary outcome, case-control |
| Risk Ratio (RR) | (a/(a+b)) / (c/(c+d)) | Binary outcome, cohort/RCT |
| Correlation r | Pearson r | Association between two continuous vars |

All are converted to a common scale (log-OR or Fisher's z) for pooling, then
back-transformed for presentation.

### Fixed vs Random Effects

**Fixed-effects** (inverse-variance weighting): assumes one true underlying effect
shared by all studies. Precision-weighted average. Appropriate when studies are
highly homogeneous.

**Random-effects** (DerSimonian-Laird or REML): assumes true effects vary across
studies drawn from a distribution N(μ, τ²). Accounts for between-study variance τ².
Gives wider, more honest confidence intervals when heterogeneity exists.

### Heterogeneity Statistics

- **Cochran Q**: Sum of squared deviations from pooled estimate, weighted by study
  precision. Chi-squared distributed with k−1 df. H₀: all studies share one true effect.
- **I²**: Percentage of total variability due to between-study heterogeneity.
  I² = (Q − df)/Q × 100. Thresholds: 0–25% low, 25–50% moderate, > 50% high.
- **τ²**: Between-study variance. Estimated by DerSimonian-Laird method-of-moments
  or REML.

---

## Environment Setup

```bash
conda create -n meta python=3.11 -y
conda activate meta
pip install numpy scipy pandas matplotlib pymare

# Verify
python -c "import numpy, scipy, pandas, matplotlib; print('Core packages OK')"
python -c "import pymare; print(f'pymare {pymare.__version__}')"
```

---

## Core Workflow

### Step 1 — Compute Effect Sizes and Standard Errors

```python
import numpy as np
import pandas as pd
from scipy import stats


def cohens_d_from_means(
    m1: float, sd1: float, n1: int,
    m2: float, sd2: float, n2: int,
) -> tuple[float, float]:
    """
    Compute Cohen's d and its standard error from group summary statistics.

    Args:
        m1, sd1, n1: Mean, SD, and n for group 1 (intervention).
        m2, sd2, n2: Mean, SD, and n for group 2 (control).

    Returns:
        Tuple of (cohen_d, se_d).
    """
    sd_pooled = np.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))
    d = (m1 - m2) / sd_pooled
    se = np.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2 - 2)))
    return float(d), float(se)


def hedges_g_correction(df: int) -> float:
    """Hedges' g correction factor J(df) using the gamma-function exact formula."""
    from math import gamma
    return gamma(df / 2) / (np.sqrt(df / 2) * gamma((df - 1) / 2))


def log_odds_ratio(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    """
    Compute log(OR) and its SE from a 2×2 contingency table.

    Table layout:
        Outcome+  Outcome-
    Exposed:   a         b
    Unexposed: c         d

    Returns:
        Tuple of (log_or, se_log_or).
    """
    # Add 0.5 continuity correction for zero cells
    a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    log_or = np.log((a * d) / (b * c))
    se = np.sqrt(1/a + 1/b + 1/c + 1/d)
    return float(log_or), float(se)


def r_to_z(r: float, n: int) -> tuple[float, float]:
    """
    Fisher's r-to-z transformation for pooling correlations.

    Returns:
        Tuple of (z, se_z).
    """
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    return float(z), float(se)


def z_to_r(z: float) -> float:
    """Back-transform Fisher's z to correlation r."""
    return float(np.tanh(z))


# ── Build a sample dataset ────────────────────────────────────────────────────
def make_sample_dataset() -> pd.DataFrame:
    """
    Create a synthetic meta-analysis dataset (k=10 studies).

    Columns: study_id, author, year, n1, n2, m1, sd1, m2, sd2, d, se_d.
    """
    np.random.seed(42)
    k = 10
    rows = []
    true_d = 0.50  # true underlying effect
    tau = 0.20     # between-study SD

    for i in range(k):
        n1 = np.random.randint(30, 150)
        n2 = np.random.randint(30, 150)
        study_d = np.random.normal(true_d, tau)
        d, se = cohens_d_from_means(
            m1=study_d, sd1=1.0, n1=n1,
            m2=0.0,     sd2=1.0, n2=n2,
        )
        rows.append({
            "study_id": i + 1,
            "author": f"Author{i+1} et al.",
            "year": 2015 + i,
            "n1": n1, "n2": n2,
            "d": d, "se_d": se,
            "vi": se**2,
            "subgroup": "GroupA" if i < 5 else "GroupB",
        })
    return pd.DataFrame(rows)
```

### Step 2 — Fixed-Effects and Random-Effects Pooling

```python
import numpy as np
import pandas as pd
from scipy import stats
from typing import Literal


def fixed_effects_pool(es: np.ndarray, vi: np.ndarray) -> dict:
    """
    Inverse-variance weighted fixed-effects pooling.

    Args:
        es: Array of effect sizes (e.g., Cohen's d or log-OR).
        vi: Array of within-study variances (se²).

    Returns:
        Dictionary with keys: pooled_es, se, ci_low, ci_high, z, pvalue,
        Q, df, I2, pQ.
    """
    w = 1.0 / vi
    theta_fe = np.sum(w * es) / np.sum(w)
    se_fe = np.sqrt(1.0 / np.sum(w))
    z = theta_fe / se_fe
    pval = 2 * stats.norm.sf(abs(z))
    ci_low = theta_fe - 1.96 * se_fe
    ci_high = theta_fe + 1.96 * se_fe

    # Cochran Q and I²
    Q = np.sum(w * (es - theta_fe) ** 2)
    df = len(es) - 1
    I2 = max(0.0, (Q - df) / Q * 100)
    pQ = 1 - stats.chi2.cdf(Q, df)

    return {
        "pooled_es": float(theta_fe),
        "se": float(se_fe),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "z": float(z),
        "pvalue": float(pval),
        "Q": float(Q),
        "df": int(df),
        "I2": float(I2),
        "pQ": float(pQ),
        "model": "Fixed-Effects",
    }


def dersimonian_laird(es: np.ndarray, vi: np.ndarray) -> dict:
    """
    DerSimonian-Laird random-effects meta-analysis.

    Estimates between-study variance τ² by method-of-moments,
    then applies inverse-variance weighting with vi + τ².

    Args:
        es: Array of effect sizes.
        vi: Array of within-study variances.

    Returns:
        Dictionary with pooled estimate, SE, CI, z, p, Q, I², τ².
    """
    w = 1.0 / vi
    theta_fe = np.sum(w * es) / np.sum(w)
    Q = np.sum(w * (es - theta_fe) ** 2)
    df = len(es) - 1
    I2 = max(0.0, (Q - df) / Q * 100)
    pQ = 1 - stats.chi2.cdf(Q, df)

    # DL τ² estimate
    c = np.sum(w) - np.sum(w**2) / np.sum(w)
    tau2 = max(0.0, (Q - df) / c)

    # Random-effects weights
    w_re = 1.0 / (vi + tau2)
    theta_re = np.sum(w_re * es) / np.sum(w_re)
    se_re = np.sqrt(1.0 / np.sum(w_re))
    z = theta_re / se_re
    pval = 2 * stats.norm.sf(abs(z))
    ci_low = theta_re - 1.96 * se_re
    ci_high = theta_re + 1.96 * se_re

    return {
        "pooled_es": float(theta_re),
        "se": float(se_re),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "z": float(z),
        "pvalue": float(pval),
        "Q": float(Q),
        "df": int(df),
        "I2": float(I2),
        "pQ": float(pQ),
        "tau2": float(tau2),
        "tau": float(np.sqrt(tau2)),
        "model": "Random-Effects (DL)",
    }


def subgroup_analysis(df: pd.DataFrame, group_col: str,
                       es_col: str = "d", vi_col: str = "vi") -> pd.DataFrame:
    """
    Run DerSimonian-Laird pooling within each subgroup.

    Args:
        df:        DataFrame with effect sizes and grouping variable.
        group_col: Column name defining subgroups.
        es_col:    Column with effect size values.
        vi_col:    Column with within-study variances.

    Returns:
        DataFrame with one row per subgroup: group, k, pooled_es, se, ci_low,
        ci_high, I2, tau2.
    """
    rows = []
    for grp, gdf in df.groupby(group_col):
        res = dersimonian_laird(gdf[es_col].values, gdf[vi_col].values)
        rows.append({
            "subgroup": grp,
            "k": len(gdf),
            "pooled_es": res["pooled_es"],
            "se": res["se"],
            "ci_low": res["ci_low"],
            "ci_high": res["ci_high"],
            "I2": res["I2"],
            "tau2": res["tau2"],
        })
    return pd.DataFrame(rows)
```

### Step 3 — Forest Plot, Funnel Plot, and Egger Test

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from scipy import stats


def forest_plot(
    df: pd.DataFrame,
    pooled: dict,
    es_col: str = "d",
    vi_col: str = "vi",
    label_col: str = "author",
    x_label: str = "Effect Size (Cohen's d)",
    output_path: str = "forest_plot.png",
) -> None:
    """
    Draw a publication-quality forest plot.

    Args:
        df:          DataFrame of individual study estimates.
        pooled:      Output dict from fixed_effects_pool or dersimonian_laird.
        es_col:      Column name for effect sizes.
        vi_col:      Column name for within-study variances.
        label_col:   Column name for study labels on y-axis.
        x_label:     X-axis label.
        output_path: File path to save the figure.
    """
    k = len(df)
    fig, ax = plt.subplots(figsize=(10, max(5, k * 0.45 + 2)))

    y_positions = np.arange(k, 0, -1)
    se = np.sqrt(df[vi_col].values)
    ci_low  = df[es_col].values - 1.96 * se
    ci_high = df[es_col].values + 1.96 * se

    # Relative weights as marker size
    w = 1.0 / df[vi_col].values
    w_norm = w / w.max()
    marker_sizes = 30 + 100 * w_norm

    for i, (y, es_val, cil, cih, ms) in enumerate(
        zip(y_positions, df[es_col].values, ci_low, ci_high, marker_sizes)
    ):
        ax.plot([cil, cih], [y, y], color="#4C72B0", lw=1.2)
        ax.scatter(es_val, y, s=ms, color="#4C72B0", zorder=5)

    # Pooled diamond
    p = pooled["pooled_es"]
    p_lo = pooled["ci_low"]
    p_hi = pooled["ci_high"]
    diamond_y = 0.0
    diamond = plt.Polygon(
        [[p_lo, diamond_y], [p, diamond_y + 0.3],
         [p_hi, diamond_y], [p, diamond_y - 0.3]],
        closed=True, fc="#E63946", ec="#C1121F", zorder=6,
    )
    ax.add_patch(diamond)

    ax.axvline(0, color="grey", lw=0.8, linestyle="--")
    ax.set_yticks(list(y_positions) + [0])
    ax.set_yticklabels(list(df[label_col]) + [f"Pooled ({pooled['model']})"])
    ax.set_xlabel(x_label)

    info = (f"Pooled = {p:.3f} (95% CI: [{p_lo:.3f}, {p_hi:.3f}])\n"
            f"I² = {pooled['I2']:.1f}%,  Q = {pooled['Q']:.2f} (p = {pooled['pQ']:.3f})")
    ax.set_title(f"Forest Plot\n{info}", fontsize=10)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Forest plot saved to {output_path}")


def funnel_plot(
    df: pd.DataFrame,
    pooled: dict,
    es_col: str = "d",
    vi_col: str = "vi",
    output_path: str = "funnel_plot.png",
) -> None:
    """
    Draw a funnel plot and annotate with Egger's test result.

    Args:
        df:          Study-level estimates DataFrame.
        pooled:      Pooled result dictionary.
        es_col:      Effect size column.
        vi_col:      Variance column.
        output_path: Output file path.
    """
    se = np.sqrt(df[vi_col].values)
    es = df[es_col].values
    theta = pooled["pooled_es"]

    egger = egger_test(es, se)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(es, se, color="#4C72B0", edgecolors="white", s=60, zorder=5)
    ax.invert_yaxis()

    # Pseudo 95% CI funnel lines
    se_range = np.linspace(0, se.max() * 1.05, 100)
    ax.plot(theta + 1.96 * se_range, se_range, "r--", lw=1, label="95% pseudo-CI")
    ax.plot(theta - 1.96 * se_range, se_range, "r--", lw=1)
    ax.axvline(theta, color="grey", lw=0.8, linestyle="-")

    title = (f"Funnel Plot\nEgger's test: intercept = {egger['intercept']:.3f}, "
             f"p = {egger['pvalue']:.3f}")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Effect Size")
    ax.set_ylabel("Standard Error")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Funnel plot saved to {output_path}")


def egger_test(es: np.ndarray, se: np.ndarray) -> dict:
    """
    Egger's test for funnel plot asymmetry.

    Regresses standardized effect (es/se) on precision (1/se).
    A significant non-zero intercept suggests small-study effects.

    Args:
        es: Array of effect sizes.
        se: Array of standard errors.

    Returns:
        Dictionary: intercept, slope, t_stat, pvalue, interpretation.
    """
    precision = 1.0 / se
    std_effect = es / se

    slope, intercept, r, pval, se_slope = stats.linregress(precision, std_effect)
    # Egger uses the intercept t-test; scipy linregress reports overall regression p-value
    n = len(es)
    t_intercept = intercept / (se_slope * np.sqrt(np.sum(precision**2) / n))
    p_intercept = 2 * stats.t.sf(abs(t_intercept), df=n - 2)

    interpretation = (
        "Significant asymmetry (possible publication bias)" if p_intercept < 0.05
        else "No significant asymmetry detected"
    )
    return {
        "intercept": float(intercept),
        "slope": float(slope),
        "t_stat": float(t_intercept),
        "pvalue": float(p_intercept),
        "interpretation": interpretation,
    }
```

---

## Advanced Usage

### PET-PEESE Publication Bias Correction

PET-PEESE is a regression-based correction:

- **PET** (Precision-Effect Test): regress effect on SE. If intercept ≈ 0, no effect.
- **PEESE** (Precision-Effect Estimate with Standard Error): if PET intercept ≠ 0,
  use variance (SE²) as predictor to estimate bias-corrected effect.

```python
def pet_peese(es: np.ndarray, se: np.ndarray) -> dict:
    """
    PET-PEESE publication bias correction.

    Args:
        es: Array of effect sizes.
        se: Array of standard errors.

    Returns:
        Dictionary with PET intercept (bias-adjusted null-test) and PEESE estimate.
    """
    vi = se ** 2

    # PET: es_i = beta0 + beta1 * se_i + error
    slope_pet, int_pet, _, p_pet, _ = stats.linregress(se, es)

    # PEESE: es_i = beta0 + beta1 * vi_i + error
    slope_peese, int_peese, _, p_peese, _ = stats.linregress(vi, es)

    if p_pet < 0.10:
        corrected = int_peese
        method = "PEESE"
    else:
        corrected = int_pet
        method = "PET"

    return {
        "pet_intercept": float(int_pet),
        "pet_pvalue": float(p_pet),
        "peese_intercept": float(int_peese),
        "peese_pvalue": float(p_peese),
        "corrected_estimate": float(corrected),
        "method_used": method,
    }
```

### Trim-and-Fill

The trim-and-fill method imputes missing studies on the asymmetric side of the
funnel and re-estimates the pooled effect. Use `pymare` for this:

```python
from pymare import Dataset
from pymare.estimators import DerSimonianLaird, TrimAndFill

def trim_and_fill_pymare(es: list, se: list, study_ids: list) -> dict:
    """
    Apply trim-and-fill using pymare.

    Args:
        es:         List of effect sizes.
        se:         List of standard errors.
        study_ids:  List of study identifier strings.

    Returns:
        Dictionary with original and adjusted pooled estimates.
    """
    dataset = Dataset(
        y=es,
        v=[s**2 for s in se],
        n=study_ids,  # used as labels only
    )
    # Original DL estimate
    dl = DerSimonianLaird()
    dl.fit(dataset)
    original = dl.summary_

    # Trim-and-fill adjusted
    taf = TrimAndFill()
    taf.fit(dataset)
    adjusted = taf.summary_

    return {"original": original, "adjusted": adjusted}
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `tau2` is negative | Q < df (less variation than expected) | Truncate τ² at 0 (as implemented above) |
| Forest plot labels overlap | Too many studies | Reduce `figsize` height per study or use abbreviations |
| I² = 100% | One study has extreme effect or tiny SE | Check data entry; consider influence diagnostics |
| Egger p-value inflated | Small k (fewer than 10 studies) | Use Begg's rank correlation test instead |
| pymare import error | Package not installed correctly | `pip install pymare --upgrade` |
| Wide pooled CI | High τ² (genuine heterogeneity) | Report τ² and prediction interval; investigate moderators |

---

## External Resources

- Borenstein et al. (2009) *Introduction to Meta-Analysis* (Wiley)
- Cochrane Handbook Chapter 10: <https://training.cochrane.org/handbook/current/chapter-10>
- pymare documentation: <https://pymare.readthedocs.io>
- PRISMA-MA reporting: <https://www.prisma-statement.org>
- metafor R package (reference implementation): <https://www.metafor-project.org>
- PET-PEESE paper: Stanley & Doucouliagos (2014), *Journal of Economic Surveys*

---

## Examples

### Example 1 — End-to-End Manual Pooling with NumPy

```python
# Generate data and run both models
df = make_sample_dataset()

fe_result = fixed_effects_pool(df["d"].values, df["vi"].values)
re_result = dersimonian_laird(df["d"].values, df["vi"].values)

print("=== Fixed-Effects ===")
print(f"  Pooled d = {fe_result['pooled_es']:.3f} "
      f"[{fe_result['ci_low']:.3f}, {fe_result['ci_high']:.3f}]")
print(f"  I² = {fe_result['I2']:.1f}%,  Q = {fe_result['Q']:.2f} (p = {fe_result['pQ']:.3f})")

print("\n=== Random-Effects (DerSimonian-Laird) ===")
print(f"  Pooled d = {re_result['pooled_es']:.3f} "
      f"[{re_result['ci_low']:.3f}, {re_result['ci_high']:.3f}]")
print(f"  τ² = {re_result['tau2']:.4f},  τ = {re_result['tau']:.4f}")
print(f"  I² = {re_result['I2']:.1f}%")
```

### Example 2 — Forest Plot Generation

```python
df = make_sample_dataset()
re_result = dersimonian_laird(df["d"].values, df["vi"].values)

forest_plot(
    df=df,
    pooled=re_result,
    es_col="d",
    vi_col="vi",
    label_col="author",
    x_label="Cohen's d (intervention vs. control)",
    output_path="forest_plot.png",
)
```

### Example 3 — Funnel Plot and Egger Test

```python
df = make_sample_dataset()
re_result = dersimonian_laird(df["d"].values, df["vi"].values)

funnel_plot(df, re_result, output_path="funnel_plot.png")

egger = egger_test(df["d"].values, np.sqrt(df["vi"].values))
print(f"Egger intercept = {egger['intercept']:.3f}, p = {egger['pvalue']:.3f}")
print(egger["interpretation"])

pet_result = pet_peese(df["d"].values, np.sqrt(df["vi"].values))
print(f"\nPET-PEESE corrected estimate = {pet_result['corrected_estimate']:.3f} "
      f"(method: {pet_result['method_used']})")
```

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-03-17 | Initial release — FE/RE pooling, forest/funnel plots, Egger, PET-PEESE |

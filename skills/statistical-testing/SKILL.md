---
name: statistical-testing
description: >
  Select and run the correct hypothesis test based on data properties.
  Covers parametric/non-parametric tests, effect sizes, and multiple comparison correction.
tags:
  - statistics
  - hypothesis-testing
  - scipy
  - effect-size
  - multiple-comparisons
  - power-analysis
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
    - scipy>=1.10.0
    - numpy>=1.24.0
    - pandas>=2.0.0
    - statsmodels>=0.14.0
    - pingouin>=0.5.3
last_updated: "2026-03-17"
---

# Statistical Testing

**本整合包适配（ML/时序实验小样本规则）：**

- **n=3 种子不要报 p 值**——检验功效不足，任何"显著"都不可信；报均值±标准差
  （`mean ± std`，不要写"方差"除非真的报的是 variance）或极差。
- **≥5 种子**才考虑显著性检验；同种子/同数据集天然配对，用配对检验
  （小样本首选 Wilcoxon signed-rank；分布近似正态可用 paired t-test）。
- **时序预测特有注意**：不同预测长度（96/192/336/720）与不同数据集的误差不可
  合并成一个总体做检验（分布不同质）；按（数据集, horizon）分层比较。滚动
  评测窗口之间高度自相关，不满足独立样本假设，不要把窗口当独立观测灌进 t 检验。
- **多重比较**：数据集 × horizon × baseline × 指标的全组合检验必须做
  Holm 或 Benjamini-Hochberg FDR 校正，否则只对预先指定的主对比做检验。
- **实验级比较台账（comparison ledger）**：校正必须覆盖*整个实验中做过的全部检验*，
  不是每次调用 `correct_pvalues` 时手头恰好有的那几个 p 值。在
  `research_run/<slug>/stage4_experiments/comparison_ledger.md` 维护一张累计表
  （比较对象 / 数据集 / horizon / 指标 / 原始 p 值 / 所属比较族），投稿前对每个
  比较族整体重跑一次校正；表里没登记的检验不得写进论文。
- **两组独立比较默认 Welch**：不要用"先 Levene 检验再选 equal_var"的两步法
  （膨胀错误率）；`run_comparison` 已默认 `equal_var=False`。

Choose and execute the right statistical test for your data. This skill covers
normality checks, parametric and non-parametric tests, effect size computation,
and multiple comparison correction.

---

## Decision Tree

| Scenario | Groups | Normal? | Recommended Test |
|---|---|---|---|
| Compare means | 2 independent | Yes | Independent t-test |
| Compare means | 2 independent | No | Mann-Whitney U |
| Compare means | 2 paired | Yes | Paired t-test |
| Compare means | 2 paired | No | Wilcoxon signed-rank |
| Compare means | ≥3 independent | Yes | One-way ANOVA |
| Compare means | ≥3 independent | No | Kruskal-Wallis |
| Compare means | ≥3 repeated | Yes | Repeated-measures ANOVA |
| Compare means | ≥3 repeated | No | Friedman test |
| Association | 2 categorical | Expected ≥5 | Chi-square |
| Association | 2 categorical | Expected <5 | Fisher exact |
| Correlation | 2 continuous | Both normal | Pearson r |
| Correlation | 2 continuous | Non-normal | Spearman ρ |

---

## Setup

```bash
pip install scipy numpy pandas statsmodels pingouin
```

---

## Core Implementation

```python
"""
statistical_testing.py
Complete statistical testing toolkit with automatic test selection.
"""

import warnings
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats import multitest
from statsmodels.stats.power import TTestIndPower, FTestAnovaPower
from typing import Union, Optional, Tuple, List, Dict, Any


# ─────────────────────────────────────────────
# 1. Normality Tests
# ─────────────────────────────────────────────

def test_normality(
    data: np.ndarray,
    alpha: float = 0.05,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run Shapiro-Wilk, Kolmogorov-Smirnov, and D'Agostino-Pearson normality tests.

    Parameters
    ----------
    data : array-like
        1-D numeric data.
    alpha : float
        Significance level.
    verbose : bool
        Print a summary.

    Returns
    -------
    dict with keys: shapiro, ks, dagostino, is_normal
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)

    results: Dict[str, Any] = {}

    # Shapiro-Wilk (best for n < 5000)
    if n < 5000:
        stat_sw, p_sw = stats.shapiro(data)
        results["shapiro"] = {"statistic": stat_sw, "p_value": p_sw, "normal": p_sw > alpha}
    else:
        results["shapiro"] = {"statistic": None, "p_value": None, "normal": None,
                              "note": "n>=5000; skipped Shapiro-Wilk"}

    # Lilliefors-corrected KS (parameters estimated from the same sample — a plain
    # stats.kstest with fitted mu/sigma is anti-conservative and must NOT be used)
    if n >= 4:
        try:
            from statsmodels.stats.diagnostic import lilliefors
            stat_ks, p_ks = lilliefors(data, dist="norm")
            results["ks"] = {"statistic": stat_ks, "p_value": p_ks, "normal": p_ks > alpha,
                             "note": "Lilliefors-corrected KS"}
        except ImportError:
            results["ks"] = {"statistic": None, "p_value": None, "normal": None,
                             "note": "statsmodels missing; skipped KS (do not substitute "
                                     "a plain kstest with fitted parameters)"}
    else:
        results["ks"] = {"statistic": None, "p_value": None, "normal": None,
                         "note": "n<4; skipped KS"}

    # D'Agostino-Pearson (needs n >= 20)
    if n >= 20:
        stat_da, p_da = stats.normaltest(data)
        results["dagostino"] = {"statistic": stat_da, "p_value": p_da, "normal": p_da > alpha}
    else:
        results["dagostino"] = {"statistic": None, "p_value": None, "normal": None,
                                "note": "n<20; skipped D'Agostino"}

    # Consensus: normal if at least 2 out of 3 available tests agree
    votes = [v["normal"] for v in results.values() if isinstance(v, dict) and v["normal"] is not None]
    results["is_normal"] = sum(votes) >= (len(votes) / 2)
    results["n"] = n

    if verbose:
        print(f"Normality tests (n={n}, alpha={alpha})")
        for test_name, res in results.items():
            if isinstance(res, dict) and "p_value" in res and res["p_value"] is not None:
                verdict = "NORMAL" if res["normal"] else "NON-NORMAL"
                print(f"  {test_name:15s}: stat={res['statistic']:.4f}, p={res['p_value']:.4f}  [{verdict}]")
        print(f"  Consensus: {'NORMAL' if results['is_normal'] else 'NON-NORMAL'}\n")

    return results


# ─────────────────────────────────────────────
# 2. Effect Sizes
# ─────────────────────────────────────────────

def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """Cohen's d for two independent groups."""
    g1, g2 = np.asarray(group1), np.asarray(group2)
    n1, n2 = len(g1), len(g2)
    pooled_sd = np.sqrt(((n1 - 1) * np.var(g1, ddof=1) + (n2 - 1) * np.var(g2, ddof=1)) / (n1 + n2 - 2))
    return (np.mean(g1) - np.mean(g2)) / pooled_sd


def eta_squared(f_statistic: float, df_between: int, df_within: int) -> float:
    """Eta-squared from F-statistic for one-way ANOVA."""
    ss_between = f_statistic * df_between
    ss_total = ss_between + df_within
    return ss_between / ss_total


def cramers_v(contingency_table: np.ndarray) -> float:
    """Cramér's V for association in a contingency table."""
    chi2 = stats.chi2_contingency(contingency_table, correction=False)[0]
    n = contingency_table.sum()
    min_dim = min(contingency_table.shape) - 1
    return np.sqrt(chi2 / (n * min_dim))


def interpret_effect_size(d: float, measure: str = "cohens_d") -> str:
    """Return a qualitative label for an effect size."""
    thresholds = {
        "cohens_d":   [(0.2, "small"), (0.5, "medium"), (0.8, "large")],
        "eta_squared": [(0.01, "small"), (0.06, "medium"), (0.14, "large")],
        "cramers_v":  [(0.1, "small"), (0.3, "medium"), (0.5, "large")],
    }
    d = abs(d)
    for threshold, label in thresholds.get(measure, []):
        if d < threshold:
            return label
    return "large"


# ─────────────────────────────────────────────
# 3. Automatic Test Selection
# ─────────────────────────────────────────────

def run_comparison(
    *groups: np.ndarray,
    paired: bool = False,
    alpha: float = 0.05,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Automatically select and run the appropriate comparison test.

    Parameters
    ----------
    *groups : array-like
        Two or more numeric arrays (one per group).
    paired : bool
        Whether observations are paired / repeated measures.
    alpha : float
        Significance level.
    verbose : bool
        Print result summary.

    Returns
    -------
    dict with keys: test_name, statistic, p_value, effect_size, significant
    """
    groups = [np.asarray(g, dtype=float) for g in groups]
    k = len(groups)

    if k < 2:
        raise ValueError("Need at least 2 groups.")

    min_n = min(len(g) for g in groups)
    if min_n < 5:
        import warnings
        warnings.warn(
            f"smallest group has n={min_n} < 5: p-values are unreliable at this sample "
            "size \u2014 report mean/std (or range) instead of significance claims "
            "(pack policy: no p-values at n=3).", stacklevel=2)

    # Check normality for each group
    all_normal = all(test_normality(g, alpha=alpha, verbose=False)["is_normal"] for g in groups)

    result: Dict[str, Any] = {}

    if k == 2:
        g1, g2 = groups[0], groups[1]
        if paired:
            if all_normal:
                stat, p = stats.ttest_rel(g1, g2)
                result["test_name"] = "Paired t-test"
                d = np.mean(g1 - g2) / np.std(g1 - g2, ddof=1)
                result["effect_size"] = {"cohens_d": round(d, 4)}
            else:
                stat, p = stats.wilcoxon(g1, g2)
                result["test_name"] = "Wilcoxon signed-rank"
                # matched-pairs rank-biserial r = (T+ - T-)/(T+ + T-), computed from
                # the signed ranks directly (robust to scipy's choice of W statistic)
                diff = g1 - g2
                diff = diff[diff != 0]
                ranks = stats.rankdata(np.abs(diff))
                t_plus = float(ranks[diff > 0].sum())
                t_minus = float(ranks[diff < 0].sum())
                rb = (t_plus - t_minus) / (t_plus + t_minus)
                result["effect_size"] = {"rank_biserial": round(rb, 4)}
        else:
            if all_normal:
                # Welch by default — the two-step "Levene pretest then choose
                # equal_var" procedure inflates error rates and is not robust;
                # Welch loses almost nothing when variances happen to be equal.
                stat, p = stats.ttest_ind(g1, g2, equal_var=False)
                result["test_name"] = "Welch's t-test"
                d = cohens_d(g1, g2)
                result["effect_size"] = {"cohens_d": round(d, 4),
                                         "interpretation": interpret_effect_size(d)}
            else:
                stat, p = stats.mannwhitneyu(g1, g2, alternative="two-sided")
                result["test_name"] = "Mann-Whitney U"
                n1, n2 = len(g1), len(g2)
                rb = 1 - (2 * stat) / (n1 * n2)
                result["effect_size"] = {"rank_biserial_r": round(rb, 4)}
    else:
        # k >= 3
        if paired:
            if all_normal:
                # Repeated-measures via pingouin if available, else warn
                try:
                    import pingouin as pg
                    df_long = pd.DataFrame({
                        "value": np.concatenate(groups),
                        "group": np.repeat(np.arange(k), [len(g) for g in groups]),
                        "subject": np.tile(np.arange(len(groups[0])), k),
                    })
                    aov = pg.rm_anova(data=df_long, dv="value", within="group", subject="subject")
                    stat = aov["F"].iloc[0]
                    p = aov["p-unc"].iloc[0]
                    result["test_name"] = "Repeated-measures ANOVA (pingouin)"
                    result["effect_size"] = {"eta_squared": round(aov["np2"].iloc[0], 4)}
                except ImportError:
                    warnings.warn("pingouin not installed; falling back to Friedman test.")
                    stat, p = stats.friedmanchisquare(*groups)
                    result["test_name"] = "Friedman test (fallback)"
                    result["effect_size"] = {}
            else:
                stat, p = stats.friedmanchisquare(*groups)
                result["test_name"] = "Friedman test"
                result["effect_size"] = {}
        else:
            if all_normal:
                stat, p = stats.f_oneway(*groups)
                result["test_name"] = "One-way ANOVA"
                total_n = sum(len(g) for g in groups)
                df_between = k - 1
                df_within = total_n - k
                es = eta_squared(stat, df_between, df_within)
                result["effect_size"] = {"eta_squared": round(es, 4),
                                         "interpretation": interpret_effect_size(es, "eta_squared")}
            else:
                stat, p = stats.kruskal(*groups)
                result["test_name"] = "Kruskal-Wallis H"
                result["effect_size"] = {}

    result["statistic"] = round(float(stat), 4)
    result["p_value"] = round(float(p), 6)
    result["significant"] = p < alpha
    result["alpha"] = alpha

    if verbose:
        print(f"Test: {result['test_name']}")
        print(f"  Statistic = {result['statistic']}, p = {result['p_value']}")
        print(f"  Significant at alpha={alpha}: {result['significant']}")
        if result.get("effect_size"):
            print(f"  Effect size: {result['effect_size']}")
        print()

    return result


# ─────────────────────────────────────────────
# 4. Multiple Comparison Correction
# ─────────────────────────────────────────────

def correct_pvalues(
    p_values: List[float],
    method: str = "fdr_bh",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """
    Apply multiple comparison correction.

    Parameters
    ----------
    p_values : list of float
    method : str
        One of: bonferroni, holm, fdr_bh (Benjamini-Hochberg),
        fdr_by (Benjamini-Yekutieli), sidak
    alpha : float

    Returns
    -------
    DataFrame with original p-values, corrected p-values, and rejection flags.
    """
    reject, p_corrected, _, _ = multitest.multipletests(p_values, alpha=alpha, method=method)
    return pd.DataFrame({
        "p_original": p_values,
        "p_corrected": p_corrected,
        "reject_H0": reject,
        "method": method,
    })


# ─────────────────────────────────────────────
# 5. Power Analysis
# ─────────────────────────────────────────────

def power_analysis_ttest(
    effect_size: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.80,
    n_per_group: Optional[int] = None,
) -> Dict[str, float]:
    """
    Two-sample t-test power analysis — for **a priori** planning only (choose n
    before running the experiment, using an effect size from pilot data or the
    literature). Do NOT compute "achieved/post-hoc power" from the observed effect
    size of the same experiment: it is a monotone transform of the p-value and adds
    no information. Note this solver is for *independent* two-sample designs; a
    paired design has different power characteristics (use
    statsmodels TTestPower on the difference scores instead).
    Provide any three of (effect_size, alpha, power, n_per_group) to solve for the fourth.
    """
    analysis = TTestIndPower()
    if n_per_group is None:
        n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, ratio=1.0)
        return {"required_n_per_group": np.ceil(n), "effect_size": effect_size,
                "alpha": alpha, "power": power}
    else:
        achieved_power = analysis.solve_power(effect_size=effect_size, alpha=alpha,
                                               nobs1=n_per_group, ratio=1.0)
        return {"n_per_group": n_per_group, "effect_size": effect_size,
                "alpha": alpha, "achieved_power": round(achieved_power, 4)}


def chi_square_test_with_effect(
    contingency: np.ndarray,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Chi-square test with Cramér's V effect size."""
    chi2, p, dof, expected = stats.chi2_contingency(contingency)
    v = cramers_v(contingency)
    result = {
        "test_name": "Chi-square" if expected.min() >= 5 else "Fisher exact (recommended)",
        "chi2": round(chi2, 4),
        "p_value": round(p, 6),
        "dof": dof,
        "cramers_v": round(v, 4),
        "significant": p < alpha,
    }
    if expected.min() < 5:
        if contingency.shape == (2, 2):
            _, p_fisher = stats.fisher_exact(contingency)
            result["fisher_p"] = round(p_fisher, 6)
    return result
```

---

## Example 1 — Comparing Three Treatment Groups

```python
import numpy as np
from statistical_testing import run_comparison, correct_pvalues, power_analysis_ttest

rng = np.random.default_rng(42)

# Simulate three treatment groups (non-normal distributions)
control   = rng.exponential(scale=5, size=40)
treatment1 = rng.exponential(scale=7, size=38)
treatment2 = rng.exponential(scale=9, size=42)

# Automatic test selection
result = run_comparison(control, treatment1, treatment2, alpha=0.05)
# → Kruskal-Wallis H (non-normal data detected automatically)

# If significant, run post-hoc pairwise tests with FDR correction
from scipy.stats import mannwhitneyu

pairs = [
    ("control vs t1", mannwhitneyu(control, treatment1, alternative="two-sided").pvalue),
    ("control vs t2", mannwhitneyu(control, treatment2, alternative="two-sided").pvalue),
    ("t1 vs t2",      mannwhitneyu(treatment1, treatment2, alternative="two-sided").pvalue),
]

labels, raw_p = zip(*pairs)
correction_df = correct_pvalues(list(raw_p), method="fdr_bh")
correction_df.index = labels
print(correction_df)
```

---

## Example 2 — Paired Comparison + A-Priori Power Planning

```python
import numpy as np
from statistical_testing import test_normality, run_comparison, power_analysis_ttest

rng = np.random.default_rng(0)

pre  = rng.normal(loc=100, scale=15, size=30)
post = pre + rng.normal(loc=8, scale=10, size=30)   # ~0.5 SD improvement

# Step 1: Check normality of the difference
diff = post - pre
norm_result = test_normality(diff)

# Step 2: Run the appropriate test and report effect size + CI
result = run_comparison(pre, post, paired=True)

# Step 3 (planning the NEXT experiment): a-priori power using an effect size
# from pilot data or the literature — never "achieved power" from this sample.
d_planned = 0.5  # e.g., smallest effect size of interest
needed = power_analysis_ttest(effect_size=d_planned, alpha=0.05, power=0.90)
print(f"N needed for 90% power at d={d_planned}: {int(needed['required_n_per_group'])}")
```

---

## Categorical Data Example

```python
import numpy as np
from statistical_testing import chi_square_test_with_effect, correct_pvalues

# 2x2 contingency: treatment vs outcome
table = np.array([[45, 15],
                  [30, 30]])

result = chi_square_test_with_effect(table)
print(result)
# {'test_name': 'Chi-square', 'chi2': ..., 'p_value': ..., 'cramers_v': ..., 'significant': True}

# 3x3 contingency across three centres
multi_table = np.array([[50, 20, 10],
                        [40, 25, 15],
                        [35, 30, 20]])
result3 = chi_square_test_with_effect(multi_table)
print(result3)
```

---

## Quick Reference: Effect Size Benchmarks

| Measure | Small | Medium | Large |
|---|---|---|---|
| Cohen's d | 0.2 | 0.5 | 0.8 |
| η² (eta-squared) | 0.01 | 0.06 | 0.14 |
| Cramér's V (2×2) | 0.1 | 0.3 | 0.5 |
| Pearson r | 0.1 | 0.3 | 0.5 |

---

## Multiple Comparison Methods

| Method | Controls | Best For |
|---|---|---|
| Bonferroni | Family-wise error rate (FWER) | Few comparisons, strict control |
| Holm | FWER (less conservative) | General use |
| Benjamini-Hochberg (FDR) | False discovery rate | Many comparisons (genomics, etc.) |
| Benjamini-Yekutieli | FDR under dependence | Correlated tests |

---

## Common Pitfalls

- **Assuming normality without testing**: Always run normality checks, especially for n < 30.
- **Ignoring equal-variance assumption**: Run Levene's test before independent t-test.
- **Multiple comparisons inflation**: Any time you run ≥3 tests on the same dataset, apply correction.
- **Over-relying on p < 0.05**: Always report effect sizes alongside p-values.
- **Wrong test for paired data**: Pre/post measurements are paired; use paired tests.

---

## Environment Variables

No API keys required. All computation is local.

```bash
# Optional: set random seed for reproducibility in scripts
export STATS_RANDOM_SEED=42
```

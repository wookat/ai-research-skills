---
name: time-series-analysis
description: >
  Use this Skill for time series analysis: ARIMA/SARIMA identification (ACF/PACF, AIC),
  seasonal decomposition (STL), VAR, GARCH volatility, and forecast evaluation.
tags:
  - mathematics
  - time-series
  - ARIMA
  - VAR
  - GARCH
  - forecasting
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
    - statsmodels>=0.14
    - pmdarima>=2.0
    - arch>=6.0
    - pandas>=1.5
    - matplotlib>=3.6
    - scipy>=1.9
last_updated: "2026-03-17"
status: stable
---

# Time Series Analysis

> **TL;DR** — Full pipeline from stationarity testing and ACF/PACF identification
> through ARIMA/SARIMA fitting, STL decomposition, VAR impulse response, GARCH
> volatility modelling, and rigorous forecast evaluation (MASE, DM test).

---

## When to Use

Use this Skill when you need to:

- Determine the order of an ARIMA model from ADF / KPSS tests and ACF/PACF plots.
- Fit and forecast with ARIMA, SARIMA, or auto-ARIMA (pmdarima).
- Decompose a seasonal series into trend, seasonal, and residual components via STL.
- Model multivariate dynamics with a Vector Autoregression (VAR).
- Estimate conditional volatility clustering with GARCH(1,1).
- Compare forecasts rigorously using Diebold-Mariano (DM) test and CRPS.

| Task | Tool |
|---|---|
| Univariate forecasting | `statsmodels ARIMA / pmdarima auto_arima` |
| Seasonal decomposition | `statsmodels STL` |
| Multivariate forecasting | `statsmodels VAR` |
| Volatility modelling | `arch GARCH` |
| Model selection | AIC, BIC, out-of-sample MASE |

---

## Background & Key Concepts

### Stationarity

A time series is **weakly stationary** if its mean and autocovariance structure do not
change over time. Most classical methods require stationarity:
- Apply first-differencing (`d=1`) to remove stochastic trends.
- Apply seasonal differencing (`D=1` at lag `s`) to remove seasonal unit roots.
- Confirm with **ADF** (null: unit root, want rejection) and **KPSS** (null: stationary,
  want non-rejection).

### ARIMA(p, d, q)

- `p` AR lags identified from PACF cutting off after lag p.
- `d` differencing order from unit-root tests.
- `q` MA lags identified from ACF cutting off after lag q.
- Seasonal extension: `SARIMA(p,d,q)(P,D,Q)[s]`.

### VAR(p)

A system of k variables, each regressed on p lags of all k variables.
Lag order `p` chosen by AIC/BIC. Impulse response functions (IRF) trace the dynamic
effect of a one-unit shock to variable j on all other variables over h horizons.

### GARCH(1,1)

Conditional variance: `h_t = omega + alpha * e_{t-1}^2 + beta * h_{t-1}`.
`alpha + beta < 1` ensures covariance stationarity.
News impact curve: how a return shock of size `e` affects next-period variance.

---

## Environment Setup

```bash
conda create -n ts python=3.11 -y
conda activate ts
pip install statsmodels>=0.14 pmdarima>=2.0 arch>=6.0 \
            pandas>=1.5 matplotlib>=3.6 scipy>=1.9

python -c "import statsmodels, pmdarima, arch; print('OK')"
```

---

## Core Workflow

### Step 1 — Stationarity Tests

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

np.random.seed(42)

# ── Generate a non-stationary series with trend + noise ─────────────────────────
n = 300
t = np.arange(n)
series = 0.05 * t + np.random.randn(n).cumsum() * 0.5  # random walk + drift
ts = pd.Series(series, index=pd.date_range("2010-01-01", periods=n, freq="W"))


def run_stationarity_tests(x: pd.Series, label: str = "series") -> dict:
    """
    Run ADF and KPSS stationarity tests and return a summary dict.

    ADF  H0: unit root present  (reject -> stationary)
    KPSS H0: series is stationary (reject -> non-stationary)
    """
    adf_stat, adf_p, adf_lags, _, adf_cv, _ = adfuller(x, autolag="AIC")
    kpss_stat, kpss_p, kpss_lags, kpss_cv = kpss(x, regression="c", nlags="auto")

    result = {
        "label"    : label,
        "adf_stat" : adf_stat,
        "adf_p"    : adf_p,
        "kpss_stat": kpss_stat,
        "kpss_p"   : kpss_p,
        "adf_cv_5pct"  : adf_cv["5%"],
        "kpss_cv_5pct" : kpss_cv["5%"],
        "likely_stationary": (adf_p < 0.05) and (kpss_p > 0.05),
    }
    print(f"[{label}]  ADF  stat={adf_stat:.3f}  p={adf_p:.4f}  "
          f"(5% cv={adf_cv['5%']:.3f})")
    print(f"[{label}]  KPSS stat={kpss_stat:.3f}  p={kpss_p:.4f}  "
          f"(5% cv={kpss_cv['5%']:.3f})")
    print(f"[{label}]  Likely stationary: {result['likely_stationary']}")
    return result


# Test levels
print("=== Level series ===")
r0 = run_stationarity_tests(ts, "levels")

# Test first difference
ts_diff = ts.diff().dropna()
print("\n=== First difference ===")
r1 = run_stationarity_tests(ts_diff, "first_diff")

# ── ACF / PACF plots ─────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(12, 6))
plot_acf(ts,      lags=30, ax=axes[0, 0], title="ACF  — Levels")
plot_pacf(ts,     lags=30, ax=axes[0, 1], title="PACF — Levels")
plot_acf(ts_diff, lags=30, ax=axes[1, 0], title="ACF  — First Diff")
plot_pacf(ts_diff,lags=30, ax=axes[1, 1], title="PACF — First Diff")
fig.tight_layout()
fig.savefig("acf_pacf.png", dpi=150)
print("\nSaved acf_pacf.png")
```

### Step 2 — ARIMA Identification and Forecast

```python
import warnings
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
import pmdarima as pm

np.random.seed(0)

# ── Synthetic ARIMA(2,1,1) series ────────────────────────────────────────────────
from statsmodels.tsa.arima_process import ArmaProcess
ar_coefs = np.array([1, -0.6, -0.3])    # AR polynomial (includes lag-0 = 1)
ma_coefs = np.array([1,  0.4])           # MA polynomial
arma_process = ArmaProcess(ar_coefs, ma_coefs)
data_stationary = arma_process.generate_sample(nsample=400)
data_nonstationary = np.cumsum(data_stationary)   # integrate once -> I(1)

dates = pd.date_range("2010-01-01", periods=len(data_nonstationary), freq="M")
ys = pd.Series(data_nonstationary, index=dates)

# ── Manual ARIMA(2,1,1) ──────────────────────────────────────────────────────────
train, test = ys[:-24], ys[-24:]

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    manual_model = ARIMA(train, order=(2, 1, 1))
    manual_fit   = manual_model.fit()

print(manual_fit.summary())

# Static 24-step forecast with confidence intervals
forecast = manual_fit.get_forecast(steps=24)
fc_mean = forecast.predicted_mean
fc_ci   = forecast.conf_int(alpha=0.05)

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(train[-48:], label="Train (last 48)")
ax.plot(test,        label="Actual test", color="black")
ax.plot(fc_mean,     label="ARIMA(2,1,1) forecast", color="red")
ax.fill_between(fc_ci.index, fc_ci.iloc[:, 0], fc_ci.iloc[:, 1],
                alpha=0.2, color="red", label="95% CI")
ax.legend()
ax.set_title("ARIMA(2,1,1) Forecast")
fig.tight_layout()
fig.savefig("arima_forecast.png", dpi=150)

# ── Auto ARIMA via pmdarima ───────────────────────────────────────────────────────
print("\nRunning auto_arima...")
auto_model = pm.auto_arima(
    train,
    d=1,                   # force one differencing (already know it's I(1))
    start_p=0, max_p=4,
    start_q=0, max_q=4,
    seasonal=False,
    information_criterion="aic",
    stepwise=True,
    trace=True,
    error_action="ignore",
    suppress_warnings=True,
)
print(f"\nBest auto_arima order: {auto_model.order}")
auto_fc, auto_ci = auto_model.predict(n_periods=24, return_conf_int=True)
auto_fc_series = pd.Series(auto_fc, index=test.index)

# ── Forecast evaluation ───────────────────────────────────────────────────────────
def mase(actual: np.ndarray, forecast: np.ndarray, insample: np.ndarray) -> float:
    """Mean Absolute Scaled Error (scale-free, handles zeros)."""
    naive_mae = np.mean(np.abs(np.diff(insample)))
    mae       = np.mean(np.abs(actual - forecast))
    return mae / naive_mae if naive_mae > 0 else np.inf


def mape(actual: np.ndarray, forecast: np.ndarray) -> float:
    """Mean Absolute Percentage Error."""
    mask = actual != 0
    return np.mean(np.abs((actual[mask] - forecast[mask]) / actual[mask])) * 100


manual_mase = mase(test.values, fc_mean.values, train.values)
auto_mase   = mase(test.values, auto_fc,         train.values)
print(f"\nManual ARIMA(2,1,1) MASE: {manual_mase:.4f}")
print(f"Auto ARIMA {auto_model.order} MASE: {auto_mase:.4f}")
```

### Step 3 — STL Decomposition and VAR

```python
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.vector_ar.var_model import VAR

# ── STL decomposition ─────────────────────────────────────────────────────────────
# Generate monthly series with trend + seasonality
n = 120
t = np.arange(n)
seasonal_component = 3 * np.sin(2 * np.pi * t / 12)
trend_component    = 0.1 * t
noise              = np.random.randn(n) * 0.5
y_seasonal = pd.Series(
    trend_component + seasonal_component + noise,
    index=pd.date_range("2014-01-01", periods=n, freq="ME"),
)

stl = STL(y_seasonal, period=12, robust=True)
stl_result = stl.fit()

fig = stl_result.plot()
fig.set_size_inches(10, 7)
fig.suptitle("STL Decomposition", y=1.01)
fig.tight_layout()
fig.savefig("stl_decomposition.png", dpi=150)
print("Saved stl_decomposition.png")

# Seasonal strength: 1 - Var(remainder) / Var(seasonal + remainder)
rem = stl_result.resid
seas = stl_result.seasonal
seasonal_strength = max(0, 1 - np.var(rem) / np.var(seas + rem))
print(f"Seasonal strength: {seasonal_strength:.4f}")

# ── VAR(p) model ─────────────────────────────────────────────────────────────────
# Bivariate VAR: US Industrial Production and Unemployment Rate (synthetic)
np.random.seed(1)
n_var = 200
# Simulate a simple bivariate AR(1) system
B = np.array([[0.7, -0.2], [0.1, 0.8]])   # coefficient matrix
eps = np.random.multivariate_normal([0, 0], [[1, 0.3], [0.3, 1]], n_var)
Y = np.zeros((n_var, 2))
for t_ in range(1, n_var):
    Y[t_] = B @ Y[t_-1] + eps[t_]

df_var = pd.DataFrame(Y, columns=["y1", "y2"],
                      index=pd.date_range("2005-01", periods=n_var, freq="ME"))

# ── Lag selection ─────────────────────────────────────────────────────────────────
model_var = VAR(df_var)
lag_result = model_var.select_order(maxlags=8)
print("\nVAR lag selection:")
print(lag_result.summary())
best_lag = lag_result.aic

# ── Fit VAR ───────────────────────────────────────────────────────────────────────
var_fit = model_var.fit(best_lag)
print(var_fit.summary())

# ── Granger causality test ────────────────────────────────────────────────────────
gc_test = var_fit.test_causality("y1", "y2", kind="f")
print(f"\nGranger causality y2 -> y1: F={gc_test.test_statistic:.4f}, p={gc_test.pvalue:.4f}")

# ── Impulse response functions ────────────────────────────────────────────────────
irf = var_fit.irf(periods=12)
fig_irf = irf.plot(orth=True)
fig_irf.set_size_inches(8, 5)
fig_irf.tight_layout()
fig_irf.savefig("var_irf.png", dpi=150)
print("Saved var_irf.png")

# ── 12-step ahead forecast ────────────────────────────────────────────────────────
var_fc = var_fit.forecast(df_var.values[-best_lag:], steps=12)
print("\nVAR 12-step forecast (first 3 rows):")
print(pd.DataFrame(var_fc[:3], columns=["y1_hat", "y2_hat"]))
```

---

## Advanced Usage

### GARCH(1,1) Volatility Modelling

```python
from arch import arch_model
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)

# ── Simulate GARCH(1,1) returns ──────────────────────────────────────────────────
n_garch = 1000
omega, alpha, beta = 0.0001, 0.1, 0.85
h = np.zeros(n_garch)
r = np.zeros(n_garch)
h[0] = omega / (1 - alpha - beta)

for t in range(1, n_garch):
    h[t] = omega + alpha * r[t-1]**2 + beta * h[t-1]
    r[t] = np.sqrt(h[t]) * np.random.randn()

returns = pd.Series(r * 100, name="returns")   # scale to percentage returns

# ── Fit GARCH(1,1) ───────────────────────────────────────────────────────────────
garch_model = arch_model(returns, vol="Garch", p=1, q=1, dist="normal", mean="Zero")
garch_fit   = garch_model.fit(disp="off")
print(garch_fit.summary())

params = garch_fit.params
print(f"\nEstimated omega={params['omega']:.6f}  alpha={params['alpha[1]']:.4f}  "
      f"beta={params['beta[1]']:.4f}")
print(f"alpha + beta = {params['alpha[1]'] + params['beta[1]']:.4f}  "
      f"(< 1 -> covariance stationary)")

# ── Conditional volatility plot ──────────────────────────────────────────────────
cond_vol = garch_fit.conditional_volatility
fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
axes[0].plot(returns, color="grey", linewidth=0.5, label="Returns")
axes[0].set_title("Returns")
axes[1].plot(cond_vol, color="darkred", linewidth=0.8, label="Conditional vol")
axes[1].set_title("GARCH(1,1) Conditional Volatility")
for ax in axes:
    ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig("garch_volatility.png", dpi=150)
print("Saved garch_volatility.png")

# ── 10-step ahead volatility forecast ───────────────────────────────────────────
garch_fc = garch_fit.forecast(horizon=10, reindex=False)
vol_fc   = np.sqrt(garch_fc.variance.iloc[-1])
print("\n10-step ahead conditional std deviation forecast:")
print(vol_fc.values.round(4))
```

### Diebold-Mariano Forecast Comparison Test

```python
from scipy.stats import t as t_dist
import numpy as np


def diebold_mariano_test(
    actual: np.ndarray,
    forecast1: np.ndarray,
    forecast2: np.ndarray,
    h: int = 1,
    loss: str = "mse",
) -> dict:
    """
    Diebold-Mariano test for equal predictive accuracy.

    H0: E[d_t] = 0  (equal forecast accuracy)
    H1: model 1 is more accurate (one-sided) or different (two-sided)

    Args:
        actual:    Array of true values.
        forecast1: Array of model 1 predictions.
        forecast2: Array of model 2 predictions.
        h:         Forecast horizon (>1 needs Newey-West HAC).
        loss:      'mse' or 'mae'.

    Returns:
        dict with DM statistic, p-value, and conclusion.
    """
    e1 = actual - forecast1
    e2 = actual - forecast2

    if loss == "mse":
        d = e1**2 - e2**2
    elif loss == "mae":
        d = np.abs(e1) - np.abs(e2)
    else:
        raise ValueError("loss must be 'mse' or 'mae'")

    n = len(d)
    d_bar = np.mean(d)

    # Newey-West HAC variance (needed when h > 1)
    gamma0 = np.var(d, ddof=1)
    gamma_sum = sum(
        (1 - k / (h + 1)) * np.cov(d[k:], d[:-k])[0, 1]
        for k in range(1, h)
    ) if h > 1 else 0.0
    var_d  = (gamma0 + 2 * gamma_sum) / n
    se_d   = np.sqrt(max(var_d, 1e-12))

    dm_stat = d_bar / se_d
    p_value = 2 * t_dist.sf(abs(dm_stat), df=n - 1)  # two-sided

    return {
        "dm_statistic": float(dm_stat),
        "p_value"     : float(p_value),
        "mean_diff"   : float(d_bar),
        "conclusion"  : "Model 1 better" if dm_stat < 0 else "Model 2 better"
                        if p_value < 0.05 else "No significant difference",
    }


# Example usage
np.random.seed(10)
y_true = np.random.randn(100)
fc1    = y_true + np.random.randn(100) * 0.8   # model 1: noisier
fc2    = y_true + np.random.randn(100) * 1.2   # model 2: even noisier

dm = diebold_mariano_test(y_true, fc1, fc2, h=1, loss="mse")
print(f"DM statistic : {dm['dm_statistic']:.4f}")
print(f"p-value      : {dm['p_value']:.4f}")
print(f"Conclusion   : {dm['conclusion']}")
```

---

## Troubleshooting

| Error / Symptom | Cause | Fix |
|---|---|---|
| `MLE Optimization Failed to Converge` | Poor starting values | Set `start_params` manually; try different `method` (e.g., `'powell'`) |
| `ARIMA` ACF of residuals shows autocorrelation | Under-specified model | Increase `p` or `q`; check Ljung-Box test on residuals |
| `KPSS LevelWarning: p-value is outside look-up table` | Extreme test statistic | Series is strongly non-stationary; apply differencing |
| VAR: `LinAlgError: Singular matrix` | Collinear variables | Drop one collinear variable or apply first difference |
| GARCH: `alpha + beta >= 1` | Near-integrated volatility | Use IGARCH or constrain parameters: `constraints={'type':'ineq','fun': lambda p: 0.999 - p[1] - p[2]}` |
| `pmdarima auto_arima` very slow | Stepwise=False searches all combos | Set `stepwise=True`; reduce `max_p`, `max_q` |

---

## External Resources

- statsmodels time series: <https://www.statsmodels.org/stable/tsa.html>
- pmdarima auto_arima: <https://alkaline-ml.com/pmdarima/>
- arch GARCH documentation: <https://arch.readthedocs.io/>
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (free): <https://otexts.com/fpp3/>
- Diebold-Mariano test paper: <https://doi.org/10.1080/07350015.1995.10524599>

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-03-17 | Initial release — ARIMA, SARIMA, STL, VAR, GARCH, DM test |

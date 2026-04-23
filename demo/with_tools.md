# Demo: Claude with mcp-stats-oracle (real AAPL 2020 data, unedited)

252 daily bars of AAPL OHLCV from Yahoo Finance (2020-01-02 to 2020-12-30)
— the COVID crash + recovery provides a textbook regime-shift example.
Output captured from `python demo/run_demo.py` against the live Plumber worker.

---

**Prompt:**
> Read `sample_data/aapl_2020.csv` (AAPL daily closes 2020) and tell me if
> the series is entering a new regime. Show me a line plot. Be specific
> about confidence.

**Tool calls (in order):**

### 1. `describe_data(close)`
```
  n_finite: 252
  mean: 95.199
  sd: 21.725
  min: 56.09  max: 136.69
  interpretation: N=252 (100.0% finite), mean=95.199, sd=21.725, range=[56.092, 136.690].
```

### 2. `catch22_features(close)`
```
  DN_HistogramMode_5:       -0.6871
  DN_HistogramMode_10:      -0.8726
  CO_f1ecac:                57.02
  CO_FirstMin_ac:           146
  CO_HistogramAMI_even_2_5: 1.09
  interpretation: Series shows strong autocorrelation (f1ecac=57.02) suggesting
                  persistence/trending; long positive runs (longstretch=106.00)
                  indicating regime persistence.
```

### 3. `detect_changepoints(close, hazard_rate=100)`
```
  n_changepoints: 6
  changepoints: [37, 86, 108, 128, 147, 232]
  last_changepoint: 232
  interpretation: 6 regime changes detected; most recent at index 232
                  (92.1% of series from end). Series has experienced
                  multiple structural shifts.
```

(Index 37 ≈ late February 2020 — beginning of the COVID selloff.
 Index 86 ≈ early May — start of V-recovery. Index 232 ≈ early December.)

### 4. `mrcd_outlier_detection(close ~ open)`
```
  n: 252
  n_outliers: 17
  cooks_threshold: 0.0159
  interpretation: Flagged 17 of 252 observations as outliers (6.7%,
                  threshold 4/n = 0.0159). Largest Cook's distance 0.091
                  at index 170.
```

### 5. `plot_series(plot_type="line", data=close, title="AAPL close 2020")`
```
                          AAPL close 2020
   140 **************************************************************
       *                                                            *
       *                                                       *    *
v  120 *                                     **     *      *****    *
a      *                                  **** *************        *
l  100 *                               ** *      **    *            *
u      *                          *********                         *
e      *    **********    * *******                                 *
  80.0 *           **********                                       *
       *               *                                            *
  60.0 *                                                            *
       **************************************************************
          0        50.0        100        150        200        250
                                  index
```

The V-shape is unmistakable: a flat-to-down drift into index ~40, the sharp
COVID crash bottoming near index 55, then a steady climb to ~$137 by year-end.

### 6. `money_flow_index(OHLCV, window=14)`
```
  latest: 57.97
  signal: neutral
  interpretation: Current 14-period MFI is 58.0 (neutral). Positive money
                  flow ratio 1.38.
```

### 7. `bayesian_nowcast(historical=close[:-10], signals=...)`
```
  point_estimate: 114.93
  ci_95: [86.68, 143.18]
  uncertainty_reduction: 0.31
  interpretation: Nowcast point estimate 114.930 (95% CI [86.678, 143.181]).
                  Posterior SD 14.414 vs prior SD 20.864 — uncertainty
                  reduced by 30.9% after 2 signals.
```

---

## Claude's synthesis (what it can say after reading all that)

> **Yes — AAPL 2020 was a multi-regime year; the most aggressive shift was
> the COVID crash around trading day 37 (late February) and the recovery
> starting around day 55.** Confidence on "multi-regime": high (~90%).
>
> The changepoint detector flags six structural breaks at days 37, 86, 108,
> 128, 147, and 232. The first two are the textbook pair: the February crash
> and the May-June V-recovery. The remaining four are smaller shifts as the
> rally accelerated through summer and cooled into year-end.
>
> Catch22 shows extreme persistence (f1ecac=57, longstretch=106), consistent
> with a series dominated by trending behavior rather than mean reversion —
> exactly what you expect from a directional year.
>
> MRCD flags 17 outliers (6.7%) in the close-vs-open regression, with the
> largest Cook's distance near day 170 — early September, during the
> post-split rally blow-off that preceded the late-September correction.
>
> MFI closes the year at 58 — neutral, consistent with the late-November
> consolidation after the recovery.
>
> Caveat: `hazard_rate=100` is tuned for noisy daily data. If you want only
> the most severe breaks, set it to 250 and you'll probably keep only the
> COVID crash and the V-recovery.

---

Same model. Same prompt. With tools: a dated, number-backed, real-world
answer. Without tools: see `without_tools.md`.

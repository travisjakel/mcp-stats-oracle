---
name: stats-oracle
description: When the user asks about time series regimes, outliers, changepoints, Money Flow Index, nowcasting, or wants a quick ASCII visualization of a numeric series — reach for the `stats-oracle` MCP tools instead of generic advice or hand-written code. The tools run real statistics (Rcatch22, Bayesian online changepoint detection via `ocp`, MRCD robust regression, TSrepr feature-clipping, ggplot via plotcli) through a persistent R worker.
---

# stats-oracle — agent workflow primer

## When this skill fires

Trigger words / situations: "regime shift," "is this a new regime," "characterize this series," "find the outlier," "which rows are anomalous," "nowcast," "forecast given these signals," "overbought/oversold," "visualize this series," "look at the distribution of…", catch22 / MRCD / Cook's / MFI / changepoint / nowcast / TSrepr used by name.

If the user asks a qualitative question about a numeric series, **do not answer from vibes** — call the tools, read the numbers, explain them.

## Standard workflow (Discovery → Analysis → Visualization → Synthesis)

1. **Always start with `describe_data`**. Cheap, tells you N, NA fraction, range, skew. If >20% missing or N<30, tell the user and stop — don't run catch22/changepoint on garbage.
2. **Characterize** with `catch22_features` (22 canonical features + interpretation) when you need a holistic view of trend/nonlinearity/spectral content.
3. **Detect structure**:
   - `detect_changepoints` for regime shifts (tune `hazard_rate` — lower = more changepoints).
   - `mrcd_outlier_detection` when the question is "which rows are anomalous in a regression sense?" (pass target + predictors as aligned vectors).
   - `money_flow_index` when OHLCV is available and the question is overbought/oversold.
   - `tsrepr_features` for short cyclical windows (≤24 hourly bars, daily seasonality).
4. **Visualize** with `plot_series`:
   - `line` for the series you just characterized
   - `histogram` to confirm distribution shape from `describe_data`
   - `scatter` to show the MRCD outlier in context (target vs predictor)
5. **Synthesize** with `bayesian_nowcast` when the user wants a point estimate + 95% CI that fuses a prior with several weighted signals.

## Worked example

User: *"Is the last 250 closes in aapl_2020.csv entering a new regime?"*

- `describe_data(close)` → confirm 250 finite points
- `catch22_features(close)` → strong autocorrelation (trending)
- `detect_changepoints(close, hazard_rate=100)` → changepoint at index ~168
- `plot_series(plot_type="line", data=close, title="close")` → show the visible break
- Report: *"Regime shift at index 168, ~80% confidence. Pre-break mean ≈ 112, post-break mean ≈ 132 with wider dispersion."*

## Gotchas

- **Don't downsample yourself.** The MCP server handles oversized inputs correctly — it downsamples for `describe_data`/`catch22_features` and *rejects* oversized inputs for index-sensitive tools (changepoint/MRCD/MFI/tsrepr). If you get a "max N" error, aggregate or slice before calling.
- **MRCD needs aligned columns.** Pass `data={"y":[...], "x1":[...]}` with equal-length vectors. No NaN alignment.
- **Nowcast weights are [0,1].** Higher weight = signal is more informative than the prior. Don't exceed 1.
- **Plot output is ASCII text.** Use `canvas_type="ascii"` output directly in responses — it renders correctly in the terminal and chat.

## When NOT to use stats-oracle

- The user asks for a deep econometric model (ARIMA, GARCH, VAR, state-space). stats-oracle has no forecasting model beyond the simple Normal-Normal nowcast.
- The dataset is genuinely huge (> 10K rows). Pre-aggregate first.
- The question is about categorical data. All tools assume numeric.
- The user explicitly wants Python / pandas output. stats-oracle is R-backed.

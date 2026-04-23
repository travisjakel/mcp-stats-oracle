# Changelog

All notable changes to mcp-stats-oracle are documented here. Follows
[Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-04-21

### Added
- `plot_series` tool — ASCII-rendered ggplot (line / histogram / scatter) via
  `plotcli::ggplotcli`. Output is text Claude can read inline, no image I/O.
- Claude Code plugin packaging: `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`, `hooks/hooks.json`, `skills/stats-oracle/`.
- Plugin-aware `hooks/plumber_manager.py` — uses `$CLAUDE_PLUGIN_ROOT` and
  `$CLAUDE_PLUGIN_DATA` when available, falls back to repo-relative paths for
  local development.
- Sample dataset (`sample_data/aapl_2020.csv`, 252 bars of AAPL daily OHLCV
  for 2020 — pulled from Yahoo Finance via `quantmod`; the COVID crash and
  recovery provide a textbook regime-shift example) and a standalone
  `demo/run_demo.py` that exercises all tools.

### Changed
- Downsampling policy is now per-tool. Only `describe_data` and
  `catch22_features` downsample (safe — both are distributional/spectral).
  `detect_changepoints`, `mrcd_outlier_detection`, `money_flow_index`,
  `tsrepr_features`, `bayesian_nowcast` reject oversized inputs rather than
  silently alias their output.
- Three-tier error taxonomy in `r_bridge.py` — `RBridgeConnectionError`,
  `RBridgeProtocolError`, `RBridgeToolError` — replaces the brittle
  `len(data) <= 3` heuristic for detecting R-side errors.
- Plumber server uses `@serializer unboxedJSON` so scalar fields come back
  as numbers instead of single-element arrays.

### Fixed
- `tsrepr` feature names had trailing dots from upstream (`cross.` instead of
  `cross`) — now normalized.
- Warnings in R tool functions no longer leak as partial output.
- MRCD interpretation string handles the edge case where Cook's distance is
  non-finite (previously returned an empty array; now returns a complete
  sentence with a graceful fallback).
- Hat-matrix leverage values are clamped to `< 1 - 1e-8` so perfectly-leveraged
  observations don't propagate `Inf` through Cook's distance.

## [0.1.0] — 2026-04-20

Initial release. Seven tools:

- `describe_data` — summary statistics + interpretation
- `catch22_features` — 22 canonical time-series features (Rcatch22)
- `detect_changepoints` — Bayesian online changepoint detection (ocp)
- `mrcd_outlier_detection` — robust regression + Cook's distance
- `money_flow_index` — volume-weighted momentum oscillator
- `tsrepr_features` — feature-clipping compression (TSrepr)
- `bayesian_nowcast` — sequential Normal-Normal posterior updating

Persistent R Plumber worker architecture, interpretation strings on every
tool response, Pydantic input validation at the Python boundary.

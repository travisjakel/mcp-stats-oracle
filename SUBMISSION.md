# Anthropic Plugin Marketplace Submission

Draft fields for platform.claude.com/plugins/submit. Not part of the plugin itself.

---

## Plugin name
`mcp-stats-oracle`

## One-line description (≤120 chars)
> 8 statistical tools Claude can call directly — catch22, Bayesian changepoint, MRCD outliers, MFI, ggplot, and more.

## Short description (≤300 chars)
> Turn Claude into a competent statistical analyst. Eight R-backed tools — catch22 time-series features, Bayesian online changepoint detection, MRCD robust-regression outlier flagging, Money Flow Index, TSrepr compression, Bayesian nowcasting, ASCII ggplot rendering, and a describe helper. Ships with hooks that auto-manage the R worker so you never start it by hand.

## Long description / README (for marketplace listing)
Paste the repo's README.md verbatim.

## Category
`Data & Analytics` / `Developer Tools`

## Tags / keywords
`mcp`, `r`, `statistics`, `time-series`, `changepoint-detection`, `robust-regression`,
`bayesian`, `ggplot`, `finance`, `quant`

## Repository URL
`https://github.com/travisjakel/mcp-stats-oracle`

## Marketplace URL (if different)
Same — this repo contains `.claude-plugin/marketplace.json`.

## License
MIT

## Version
0.2.0

## Dependencies
- R 4.3+ with: `plumber`, `Rcatch22`, `ocp`, `TSrepr`, `ggplot2`, `plotcli`, `jsonlite`
- Python 3.10+ with: `mcp`, `httpx`, `pydantic`

Run `Rscript setup.R` after install to install the R dependencies.

## Screenshots / demos
1. `demo/with_tools.md` — side-by-side Claude transcript with and without tools
2. Optional follow-up: Loom / YouTube demo (≤2 min) showing Claude Desktop or
   Claude Code using stats-oracle in real time

## Security / privacy review notes
- Local only. Plumber binds to `127.0.0.1:8787`; no network exposure by default.
- No data is sent to third parties. All computation happens on the user's machine.
- No authentication required (intended for single-user local use).
- Hooks only spawn a local R subprocess; they never touch the filesystem beyond
  writing a PID file + log in `$CLAUDE_PLUGIN_DATA`.

## Why Claude users will care
Claude is a strong reasoner but cannot run `Rcatch22::catch22_all`. This
plugin fills the gap for anyone who needs real statistical computation —
quants, data scientists, researchers, anyone working with time series.

## What makes it different from "generate R code and run it"
- **Typed tools**, not ad-hoc R code. Claude gets a schema; users get
  deterministic behavior.
- **Persistent R worker** — 0.1–0.3 s R startup per call becomes 10 ms once
  the Plumber server is warm. Matters for agent loops.
- **Interpretation strings** — every tool returns raw numbers *and* a
  one-sentence natural-language summary. Saves ~200 tokens per call of
  context that would otherwise be 22 raw floats.
- **Explicit downsampling policy** — aliasing is a silent bug in naive MCP
  wrappers; we reject oversized inputs for index-sensitive tools instead.
- **Auto-lifecycle hooks** — the R worker starts/stops with the Claude
  session. Users never manage it.

## What's NOT included (set expectations honestly)
- No ARIMA / GARCH / VAR / state-space forecasting (simple Normal-Normal
  nowcast only)
- No visualization beyond ASCII terminal plots
- No support for > 10,000-row inputs (pre-aggregate first)
- R is required — this is not a pure-Python toolkit

## Submission checklist
- [ ] Repo is public on GitHub
- [ ] `.claude-plugin/plugin.json` valid
- [ ] `.claude-plugin/marketplace.json` valid
- [ ] README installs in 30 seconds (`/plugin marketplace add …`)
- [ ] `setup.R` installs all R deps cleanly
- [ ] Smoke test: `python demo/run_demo.py` passes
- [ ] All R tests pass (`Rscript tests/test_r_scripts.R`)
- [ ] All Python tests pass (`pytest tests/`)
- [ ] LICENSE file present
- [ ] CHANGELOG.md up to date
- [ ] Tag release `v0.2.0` on GitHub
- [ ] Fill submission form at platform.claude.com/plugins/submit

# MCP-Stats-Oracle

**8 statistical analysis tools Claude can call directly** — catch22 time-series
features, Bayesian changepoint detection, MRCD robust-regression outlier
flagging, Money Flow Index, TSrepr compression, Bayesian nowcasting, ASCII
ggplot rendering, and a describe helper. Shipped as a Claude Code plugin with
auto-lifecycle hooks that manage the backing R worker for you.

## Install (Claude Code, 30 seconds)

```
/plugin marketplace add travisjakel/mcp-stats-oracle
/plugin install mcp-stats-oracle@mcp-stats-oracle
```

Requires R 4.3+ with `plumber`, `Rcatch22`, `ocp`, `TSrepr`, `ggplot2`, `plotcli`
(one-liner: `Rscript setup.R` after cloning). Python 3.10+ with `mcp`, `httpx`,
`pydantic`.

Then ask Claude something like:

> Read `sample_data/aapl_2020.csv` and tell me if the close series entered a
> new regime. Show me a line plot.

Claude will call `describe_data`, `detect_changepoints`, and `plot_series`
autonomously — the hooks will have already started the R worker for you.

---

## What this is

A reference implementation showing how to bridge a production R statistics
stack into an LLM agent loop — with interpretation strings for context
compression, a persistent worker for sub-second tool latency, and explicit
policy for when downsampling is (and isn't) safe.

> **Not** a drop-in tool for general LLM users. It requires a local R
> installation with specific packages. Most valuable as a pattern to copy or
> as stats firepower for people already living in R.

## Why it exists

Claude is a strong reasoner but cannot run `Rcatch22::catch22_all`. For
questions like *"is this price series entering a new volatility regime?"*,
the agent should not guess — it should call the appropriate statistical tool,
read the numbers, and explain them.

This project packages six production methods (MRCD robust regression,
Bayesian online changepoint detection, catch22 features, Money Flow Index,
TSrepr feature-clipping, Bayesian nowcasting) and a `describe_data` discovery
tool behind an MCP interface.

## Architecture

```
Claude Desktop / Claude Code
        │  (MCP / stdio)
        ▼
 server.py                (FastMCP + Pydantic validation)
        │  (HTTP POST, 127.0.0.1 only)
        ▼
 r_scripts/plumber_server.R   (persistent R worker, port 8787)
        │
        ├─ describe_tool.R        (Discovery)
        ├─ catch22_tool.R         (Analysis)
        ├─ changepoint_tool.R     (Analysis)
        ├─ mrcd_tool.R            (Analysis)
        ├─ mfi_tool.R             (Analysis)
        ├─ tsrepr_tool.R          (Analysis)
        └─ nowcast_tool.R         (Synthesis)
```

## Design decisions worth stealing

- **Persistent R worker.** R startup is 0.1–0.3s per call. Subprocess-per-call
  makes agent loops feel sluggish; an HTTP worker feels instant.
- **Interpretation strings.** Every tool returns both raw numeric output *and*
  a one-sentence natural-language summary, so the agent doesn't burn context
  on 22 raw floats per call.
- **Per-tool downsampling policy** (see below). Aliasing was an easy silent
  bug; we made the policy explicit.
- **Three-tier error taxonomy** (`Connection`, `Protocol`, `Tool` errors) so
  the agent can tell "R worker isn't running" from "your input was bad."
- **Localhost-only binding.** Plumber binds to `127.0.0.1:8787`. No auth, no
  TLS, no network exposure by default.

## Downsampling policy (the one tricky bit)

Uniform downsampling is only safe when the output is itself a summary
of distributional or spectral structure. Index-returning tools (changepoint),
row-aligned tools (MRCD), contiguous-bar tools (MFI), and cyclical-window
tools (TSrepr) reject oversized inputs rather than silently alias:

| Tool | Max input | Oversized behavior |
|---|---|---|
| `describe_data` | 5,000 kept / unbounded in | Uniform downsample |
| `catch22_features` | 5,000 kept / unbounded in | Uniform downsample |
| `detect_changepoints` | 10,000 | Reject (indices would desync) |
| `mrcd_outlier_detection` | 10,000 | Reject (row flags would desync) |
| `money_flow_index` | 10,000 | Reject (breaks rolling window) |
| `tsrepr_features` | 1,024 | Reject (aliases cycle phase) |
| `bayesian_nowcast` | 1,000 historical | Reject |
| `plot_series` | 10,000 | Reject |

## The 8 tools

| Tool | Layer | Purpose |
|---|---|---|
| `describe_data` | Discovery | Peek at NAs, range, skew before heavier tools |
| `catch22_features` | Analysis | 22 canonical time-series features (Rcatch22) |
| `detect_changepoints` | Analysis | Bayesian online changepoint detection (ocp) |
| `mrcd_outlier_detection` | Analysis | Robust regression + Cook's distance |
| `money_flow_index` | Analysis | Volume-weighted momentum oscillator |
| `tsrepr_features` | Analysis | 8 shape features for cyclical windows |
| `plot_series` | Visualization | ASCII-rendered ggplot (line / histogram / scatter) |
| `bayesian_nowcast` | Synthesis | Sequential Normal-Normal posterior updating |

## Honest limitations

- **R dependency is the barrier.** If you don't already have R installed with
  `Rcatch22`, `ocp`, `TSrepr`, `plumber`, this is a lot of friction for seven
  tools. That's by design — porting every method to Python would have
  doubled the code and lost fidelity with the upstream packages.
- **Data must flow through the chat.** Tools accept inline `list[float]`, not
  file paths. Fine for 100–10,000 points; not viable for a 4,500-ticker
  universe. A future file-based adapter would fix this.
- **Tool set is deliberately eclectic.** MFI next to Bayesian nowcast reads
  as a "junk drawer" — that's intentional. The goal is to show the *pattern*
  for wrapping heterogeneous R methods, not to ship a focused product.

## Install

**Dependencies** (either install method):

```bash
# R side — installs plumber, Rcatch22, ocp, TSrepr, ggplot2, plotcli
Rscript setup.R

# Python side
uv venv && source .venv/bin/activate   # or: python -m venv .venv
pip install -e ".[dev]"
```

### As a Claude Code Plugin (recommended)

This repo ships as a Claude Code plugin — `.claude-plugin/plugin.json`, `.mcp.json`,
`hooks/hooks.json`, and `skills/stats-oracle/SKILL.md` are all wired up.

**Local / for testing:**

```bash
claude --plugin-dir /absolute/path/to/mcp-stats-oracle
```

Inside the session, `/mcp` shows `stats-oracle` with 8 tools; `/plugin` lists the
plugin. Hooks manage the R Plumber worker automatically (start on
`SessionStart`, log + self-heal on `PreToolUse`, stop on `Stop`).

**Globally installed:** drop the repo into `~/.claude/plugins/` or publish it
to a marketplace and install via `claude plugin install stats-oracle@marketplace`.

### As a bare MCP server (Claude Desktop or other MCP clients)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "stats-oracle": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-stats-oracle/server.py"]
    }
  }
}
```

You'll have to launch Plumber yourself:

```bash
Rscript -e "plumber::pr_run(plumber::pr('r_scripts/plumber_server.R'), port=8787)"
```

### Without any LLM — just try the tools

```bash
# Terminal 1
Rscript -e "plumber::pr_run(plumber::pr('r_scripts/plumber_server.R'), port=8787)"
# Terminal 2
python demo/run_demo.py
```

## Test

```bash
# R-side unit tests (no HTTP needed)
Rscript tests/test_r_scripts.R

# Full integration (requires Plumber server running on :8787)
pytest tests/
```

## Demo

`demo/with_tools.md` vs `demo/without_tools.md` — same question, same model,
toggle the tools. With stats-oracle, Claude answers *"regime shift at index
168, confidence ~80%"*; without, it offers generic advice and lists the
techniques it wishes it could run.

## License

MIT

---

Built by Travis Jakel as a reference for MCP tool design in agent-driven
statistical analysis.

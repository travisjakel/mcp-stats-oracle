# Claude Code hooks for mcp-stats-oracle

Three hooks that auto-manage the R Plumber worker so you never have to
`Rscript -e "plumber::pr_run(...)"` by hand.

| Event | Script | What it does |
|---|---|---|
| `SessionStart` | `session_start.py` | Launch Plumber in the background if not already running |
| `PreToolUse` | `pre_tool_use.py` | Log every `mcp__stats-oracle__*` call + self-heal a dead worker |
| `Stop` | `stop.py` | Terminate the Plumber PID we spawned |

All three hooks share `plumber_manager.py`, which writes to
`hooks/plumber.log` (timestamped, UTC). PID tracking lives in
`hooks/.plumber.pid`.

## Install

1. Copy the `hooks` block from `hooks/settings.json` into your project-level
   `.claude/settings.json` (merge with any existing hooks).
2. Replace `ABSOLUTE_PATH/mcp-stats-oracle` with the real path to this repo.
3. Install the Python deps (`httpx` is the only one the hooks use beyond the
   standard library — already a dependency of `server.py`).
4. Restart Claude Code so it picks up the new hooks.

## Example session

```
$ claude
[SessionStart hook → launches Rscript in background, logs "start: launched PID 24136"]

> analyze the last 250 closes in sample_data/aapl_2020.csv for regime shifts

[Claude reads the CSV, calls stats-oracle tools]
[PreToolUse hook logs each call:
   pre_tool: describe_data(data=[250 values])
   pre_tool: catch22_features(data=[250 values])
   pre_tool: detect_changepoints(data=[250 values], hazard_rate=100)
   pre_tool: plot_series(plot_type=line, data=[250 values], title=sample close)]

[Claude answers: "Regime shift at index 168, confidence ~80% — see plot."]

> /exit
[Stop hook → terminates the Plumber PID, logs "stop: terminated PID 24136"]
```

## Why this matters

The honest critique of this repo (see the project README) was that managing
the R worker yourself is friction. These hooks eliminate that friction for
anyone willing to wire them up. The pattern generalizes: any MCP server that
needs a persistent backing process (GPU inference, a database, a long-running
worker) can borrow this layout.

## Debugging

Tail `hooks/plumber.log` to see exactly what each hook did and when. If
Plumber isn't starting, run the command manually to see stderr:

```
Rscript -e "plumber::pr_run(plumber::pr('r_scripts/plumber_server.R'), port=8787)"
```

If you want to keep Plumber warm across sessions (maybe you're bouncing in
and out of Claude frequently), remove the `Stop` entry from `settings.json`.

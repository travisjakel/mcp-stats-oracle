"""PreToolUse hook: logs every stats-oracle tool call and self-heals Plumber.

Claude Code sends a JSON envelope on stdin:

    {
      "hook_event_name": "PreToolUse",
      "tool_name": "mcp__stats-oracle__plot_series",
      "tool_input": { ... },
      ...
    }

We log `tool_name` + a truncated view of `tool_input`, then verify Plumber is
healthy (restarting it silently if not). Exits 0 always — this hook is
observational and self-healing, never blocking.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plumber_manager import check, log

STATS_ORACLE_PREFIX = "mcp__stats-oracle__"


def summarize_input(tool_input: dict) -> str:
    """Compact one-line summary of tool_input for the log."""
    parts = []
    for k, v in tool_input.items():
        if isinstance(v, list):
            parts.append(f"{k}=[{len(v)} values]")
        elif isinstance(v, dict):
            parts.append(f"{k}={{{len(v)} keys}}")
        elif isinstance(v, str) and len(v) > 40:
            parts.append(f"{k}={v[:37]}...")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    tool_name = payload.get("tool_name", "")
    if not tool_name.startswith(STATS_ORACLE_PREFIX):
        return 0  # not our tool — say nothing

    short = tool_name[len(STATS_ORACLE_PREFIX):]
    tool_input = payload.get("tool_input", {}) or {}
    log(f"pre_tool: {short}({summarize_input(tool_input)})")

    check()  # idempotent — no-op if already healthy
    return 0


if __name__ == "__main__":
    sys.exit(main())

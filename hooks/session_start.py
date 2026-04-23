"""SessionStart hook: ensure Plumber is running when the Claude session opens.

Claude Code invokes hooks with JSON on stdin describing the event. This hook
doesn't need to parse it — it just starts the R worker. Exits 0 regardless so
the session doesn't fail even if Plumber can't come up (the tool will return
a clean `RBridgeConnectionError` message instead).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plumber_manager import LOG_FILE, is_healthy, log, start


def main() -> int:
    # Drain stdin (Claude Code sends JSON context, we don't need it here)
    try:
        _ = sys.stdin.read()
    except Exception:  # noqa: BLE001
        pass

    if is_healthy():
        log("session_start: Plumber already healthy")
        return 0

    rc = start()
    log(f"session_start: start returned {rc}")
    return 0  # never block the session


if __name__ == "__main__":
    sys.exit(main())

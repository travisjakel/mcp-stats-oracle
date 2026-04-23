"""Stop hook: terminate Plumber when Claude finishes.

Runs on the `Stop` event (Claude's turn ended). Shuts down the background
R worker so you don't leave orphans between sessions. If you'd rather keep
Plumber warm across sessions, wire this hook to `SessionEnd` instead, or
drop it entirely.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plumber_manager import log, stop


def main() -> int:
    try:
        _ = sys.stdin.read()
    except Exception:  # noqa: BLE001
        pass
    rc = stop()
    log(f"stop: returned {rc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

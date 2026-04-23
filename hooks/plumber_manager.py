"""Plumber lifecycle manager — shared by all three hooks.

A small CLI wrapping the three lifecycle ops the hooks need:

    python hooks/plumber_manager.py start    # SessionStart
    python hooks/plumber_manager.py check    # PreToolUse (verify health)
    python hooks/plumber_manager.py stop     # Stop / SessionEnd

Stores the background process PID in `hooks/.plumber.pid` so `stop` can find
and terminate it. `start` is idempotent — if the server is already responsive,
it logs and exits 0.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print(json.dumps({"error": "httpx not installed"}), file=sys.stderr)
    sys.exit(1)

# Plugin-aware paths:
#   CLAUDE_PLUGIN_ROOT → plugin code dir (where r_scripts/ lives)
#   CLAUDE_PLUGIN_DATA → plugin persistent data dir (survives plugin updates)
# Outside plugin context, we derive the repo root from __file__ for local dev.
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
PLUGIN_DATA = os.environ.get("CLAUDE_PLUGIN_DATA")
ROOT = Path(PLUGIN_ROOT) if PLUGIN_ROOT else Path(__file__).resolve().parent.parent
DATA_DIR = Path(PLUGIN_DATA) if PLUGIN_DATA else (ROOT / "hooks")
DATA_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = DATA_DIR / ".plumber.pid"
LOG_FILE = DATA_DIR / "plumber.log"
HEALTH_URL = os.environ.get("STATS_ORACLE_R_URL", "http://127.0.0.1:8787") + "/health"
PORT = int(os.environ.get("STATS_ORACLE_R_PORT", "8787"))
STARTUP_TIMEOUT_S = 20.0


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()}  {msg}\n")


def is_healthy(timeout: float = 1.5) -> bool:
    try:
        r = httpx.get(HEALTH_URL, timeout=timeout)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except httpx.HTTPError:
        return False


def read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def start() -> int:
    if is_healthy():
        log("start: server already healthy — no-op")
        return 0

    cmd = [
        "Rscript",
        "-e",
        f"plumber::pr_run(plumber::pr('r_scripts/plumber_server.R'), port={PORT})",
    ]
    log(f"start: launching {' '.join(cmd)}")
    # Detach: new session on POSIX, DETACHED_PROCESS on Windows
    kwargs: dict = {
        "cwd": str(ROOT),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    PID_FILE.write_text(str(proc.pid))
    log(f"start: launched PID {proc.pid}")

    deadline = time.time() + STARTUP_TIMEOUT_S
    while time.time() < deadline:
        if is_healthy():
            log(f"start: healthy after {time.time() - (deadline - STARTUP_TIMEOUT_S):.1f}s")
            return 0
        time.sleep(0.5)

    log("start: FAILED to become healthy in time")
    return 1


def check() -> int:
    if is_healthy():
        return 0
    log("check: unhealthy — attempting restart")
    return start()


def stop() -> int:
    pid = read_pid()
    if pid is None:
        log("stop: no PID file — nothing to stop")
        return 0
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
        else:
            os.kill(pid, signal.SIGTERM)
        log(f"stop: terminated PID {pid}")
    except (ProcessLookupError, PermissionError) as e:
        log(f"stop: couldn't kill PID {pid}: {e}")
    finally:
        PID_FILE.unlink(missing_ok=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "check", "stop"])
    args = parser.parse_args()
    return {"start": start, "check": check, "stop": stop}[args.action]()


if __name__ == "__main__":
    sys.exit(main())

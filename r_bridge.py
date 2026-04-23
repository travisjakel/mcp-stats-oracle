"""HTTP client for the persistent R Plumber worker.

Each MCP tool call translates to one POST against a local Plumber server,
eliminating R interpreter startup overhead (0.1–0.3s per call).

Error taxonomy
--------------
- `RBridgeConnectionError` — the R worker isn't running or is unreachable.
  Almost always means you forgot to start Plumber on :8787.
- `RBridgeToolError` — R worker responded, but the tool returned a structured
  error (e.g. `{"error": "Need at least 30 points"}`). Preserves the R message.
- `RBridgeProtocolError` — R worker responded with a non-JSON body or an
  unexpected HTTP status. Usually a 500 from an uncaught R exception.

All three subclass `RBridgeError` for callers that just want one except clause.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("STATS_ORACLE_R_URL", "http://127.0.0.1:8787")
DEFAULT_TIMEOUT = float(os.environ.get("STATS_ORACLE_TIMEOUT", "30"))


class RBridgeError(RuntimeError):
    """Base class for all bridge errors."""


class RBridgeConnectionError(RBridgeError):
    """R worker is unreachable (not running, wrong port, network blocked)."""


class RBridgeToolError(RBridgeError):
    """R tool returned a structured error message."""


class RBridgeProtocolError(RBridgeError):
    """R worker returned an HTTP/JSON response we can't parse."""


class RBridge:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def health(self) -> dict[str, Any]:
        try:
            r = self._client.get("/health")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            raise RBridgeConnectionError(
                f"R worker unreachable at {self.base_url}/health: {exc}. "
                f"Is Plumber running? Launch with: "
                f"Rscript -e \"plumber::pr_run(plumber::pr('r_scripts/plumber_server.R'), port=8787)\""
            ) from exc

    def call(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = "/" + endpoint.lstrip("/")
        try:
            r = self._client.post(endpoint, json=payload)
        except httpx.ConnectError as exc:
            raise RBridgeConnectionError(
                f"R worker unreachable at {self.base_url}{endpoint}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RBridgeConnectionError(
                f"R worker timed out on {endpoint} after {self._client.timeout.read}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise RBridgeProtocolError(f"HTTP error on {endpoint}: {exc}") from exc

        if r.status_code >= 500:
            raise RBridgeProtocolError(
                f"R worker returned HTTP {r.status_code} on {endpoint} — "
                f"likely an uncaught R exception. Body: {r.text[:400]}"
            )
        if r.status_code >= 400:
            raise RBridgeProtocolError(
                f"R worker returned HTTP {r.status_code} on {endpoint}: {r.text[:400]}"
            )

        try:
            data = r.json()
        except json.JSONDecodeError as exc:
            raise RBridgeProtocolError(
                f"Non-JSON response from {endpoint}: {r.text[:400]}"
            ) from exc

        if isinstance(data, dict) and "error" in data:
            raise RBridgeToolError(f"{endpoint}: {data['error']}")
        return data

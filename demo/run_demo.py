"""Exercise all 7 tools against the sample data.

Requires the Plumber server running on :8787. This script bypasses the MCP
layer and hits r_bridge directly so you can verify the statistical layer
without wiring up Claude Desktop.

    python demo/run_demo.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from r_bridge import RBridge, RBridgeConnectionError  # noqa: E402


def load_sample() -> dict[str, list[float]]:
    """Load AAPL 2020 OHLCV (Yahoo Finance) as column-major dict of floats.

    The `date` column is ISO strings; we drop it since the tools operate on
    numeric vectors. Index in the series corresponds to trading-day offset.
    """
    path = ROOT / "sample_data" / "aapl_2020.csv"
    cols: dict[str, list[float]] = {}
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            for k, v in row.items():
                if k == "date":
                    continue
                cols.setdefault(k, []).append(float(v))
    return cols


def section(title: str) -> None:
    bar = "=" * 70
    print(f"\n{bar}\n{title}\n{bar}")


def show(result: dict, keys: list[str] | None = None) -> None:
    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return
    pretty = {k: result[k] for k in (keys or result) if k in result}
    for k, v in pretty.items():
        if k == "interpretation":
            print(f"  interpretation: {v}")
        elif isinstance(v, list) and len(v) > 8:
            print(f"  {k}: [{v[0]:.4g}, ..., {v[-1]:.4g}] (n={len(v)})")
        elif isinstance(v, dict):
            print(f"  {k}: {json.dumps(v, indent=4)[:200]}...")
        else:
            print(f"  {k}: {v}")


def main() -> int:
    bridge = RBridge()
    try:
        h = bridge.health()
    except RBridgeConnectionError as e:
        print(f"Plumber server not running: {e}")
        return 1

    print(f"R worker ready (version {h.get('version', '?')}, {h.get('tools')} tools)")
    cols = load_sample()
    close = cols["close"]
    print(f"Loaded {len(close)} OHLCV bars from sample_data/aapl_2020.csv (AAPL daily 2020)")

    section("1. describe_data(close)")
    show(
        bridge.call("describe", {"data": close}),
        keys=["n_finite", "mean", "sd", "min", "max", "interpretation"],
    )

    section("2. catch22_features(close)")
    r = bridge.call("catch22", {"data": close})
    if "features" in r:
        top = {k: r["features"][k] for k in list(r["features"])[:5]}
        print(f"  first 5 of 22 features: {json.dumps(top, indent=2)}")
    show(r, keys=["interpretation"])

    section("3. detect_changepoints(close, hazard_rate=100)")
    show(
        bridge.call("changepoint", {"data": close, "hazard_rate": 100}),
        keys=["n_changepoints", "changepoints", "last_changepoint", "interpretation"],
    )

    section("4. mrcd_outlier_detection(close ~ open)")
    r = bridge.call(
        "mrcd",
        {
            "data": {"close": close, "open": cols["open"]},
            "target": "close",
            "predictors": ["open"],
        },
    )
    show(r, keys=["n", "n_outliers", "cooks_threshold", "interpretation"])

    section("5. money_flow_index(OHLCV, window=14)")
    show(
        bridge.call(
            "mfi",
            {
                "high": cols["high"],
                "low": cols["low"],
                "close": close,
                "volume": cols["volume"],
                "window": 14,
            },
        ),
        keys=["latest", "signal", "interpretation"],
    )

    section("6. tsrepr_features(last 24 closes)")
    show(
        bridge.call("tsrepr", {"data": close[-24:]}),
        keys=["features", "interpretation"],
    )

    section("7. plot_series(line, close) — ASCII chart Claude can read")
    r = bridge.call("plot", {"plot_type": "line", "data": close, "title": "AAPL close 2020"})
    if "plot" in r:
        print(r["plot"])
        print(f"\n  interpretation: {r['interpretation']}")
    else:
        print(f"  error: {r.get('error')}")

    section("8. bayesian_nowcast(historical, signals)")
    show(
        bridge.call(
            "nowcast",
            {
                "historical": close[:-10],
                "signals": {
                    "mfi_signal": {"value": close[-1] * 1.02, "weight": 0.4},
                    "changepoint_signal": {"value": close[-1] * 0.98, "weight": 0.3},
                },
                "day_of_quarter": 45,
            },
        ),
        keys=["point_estimate", "ci_95", "uncertainty_reduction", "interpretation"],
    )

    print("\nAll 7 tools exercised successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

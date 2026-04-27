"""MCP-Stats-Oracle: 7 statistical analysis tools Claude can use directly.

Discovery  → describe_data
Analysis   → catch22_features, detect_changepoints, mrcd_outlier_detection,
             money_flow_index, tsrepr_features
Synthesis  → bayesian_nowcast

Each tool returns raw numeric results alongside a natural-language
`interpretation` string so Claude can reason without burning context on
22 raw floats. All computation runs in a persistent R Plumber worker.

Downsampling policy
-------------------
Uniform downsampling is only applied for tools where it preserves the output:
`describe_data` and `catch22_features` (both summarize distributional / spectral
structure that is robust to representative sampling). All other tools
(`detect_changepoints`, `mrcd_outlier_detection`, `money_flow_index`,
`tsrepr_features`, `bayesian_nowcast`) reject oversized inputs rather than
silently alias them — downsampling a cyclical window destroys the very
pattern `tsrepr` is extracting; downsampling OHLCV desyncs the bars; and a
changepoint index returned against a downsampled series doesn't map back to
the original timeline.

Launch
------
    # Terminal 1
    Rscript -e "plumber::pr_run(plumber::pr('r_scripts/plumber_server.R'), port=8787)"
    # Terminal 2
    python server.py
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

from r_bridge import (
    RBridge,
    RBridgeConnectionError,
    RBridgeError,
    RBridgeProtocolError,
    RBridgeToolError,
)

SAFE_DOWNSAMPLE_MAX = 5000
STRICT_MAX = 10000

mcp = FastMCP(
    "stats-oracle",
    instructions="Time series & robust regression tools backed by a persistent R worker."
)
bridge = RBridge()


def _downsample_uniform(x: list[float], cap: int = SAFE_DOWNSAMPLE_MAX) -> list[float]:
    """Uniform representative sampling. Only safe for summary tools."""
    if len(x) <= cap:
        return x
    step = len(x) / cap
    return [x[int(i * step)] for i in range(cap)]


def _ensure_len(name: str, x: list[float], hard_max: int = STRICT_MAX) -> list[float]:
    """Reject oversized inputs for tools where downsampling would corrupt output."""
    if len(x) > hard_max:
        raise ValueError(
            f"{name}: input has {len(x)} points; max is {hard_max}. "
            f"Downsampling would alias this tool's output, so the server refuses "
            f"rather than silently returning wrong numbers. Pre-aggregate your data."
        )
    return x


def _num_list(name: str, x: list[float]) -> list[float]:
    try:
        return [float(v) for v in x]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: expected a numeric list, got {type(x).__name__}: {exc}") from exc


def _fmt_error(tool: str, exc: Exception) -> dict[str, Any]:
    return {"error": f"{tool}: {exc}"}


class SeriesInput(BaseModel):
    data: list[float] = Field(..., min_length=4)

    @field_validator("data")
    @classmethod
    def _coerce(cls, v: list[float]) -> list[float]:
        return [float(x) for x in v]


@mcp.tool()
def describe_data(data: list[float]) -> dict[str, Any]:
    """Quick descriptive stats for a numeric series. Call this first.

    Use before running heavier tools to check whether the series has enough
    finite points to be worth analyzing. Long series are uniformly downsampled
    to 5,000 points — safe here because we only report summary stats.

    Returns mean, sd, quantiles, NA count, skewness, and an interpretation.
    """
    try:
        parsed = SeriesInput(data=data)
        payload = _downsample_uniform(parsed.data)
        return bridge.call("describe", {"data": payload})
    except (RBridgeError, ValueError) as e:
        return _fmt_error("describe_data", e)


@mcp.tool()
def catch22_features(data: list[float]) -> dict[str, Any]:
    """Compute the 22 canonical time series features (Rcatch22).

    Captures distribution, autocorrelation, nonlinear dynamics, and spectral
    properties. Good first pass when you need to characterize an unknown series.
    Series > 5,000 points are uniformly downsampled — acceptable because
    catch22 features are distributional/spectral, not index-dependent.

    Returns raw features + interpretation describing the dominant regime.
    """
    try:
        parsed = SeriesInput(data=data)
        payload = _downsample_uniform(parsed.data)
        return bridge.call("catch22", {"data": payload})
    except (RBridgeError, ValueError) as e:
        return _fmt_error("catch22_features", e)


@mcp.tool()
def detect_changepoints(data: list[float], hazard_rate: int = 250) -> dict[str, Any]:
    """Bayesian online changepoint detection (ocp).

    Identifies structural shifts in a univariate series. Returns changepoint
    indices — these map back to the *input* array, so the server refuses to
    downsample (changepoint at "index 168" is meaningless if you've already
    thrown away 50% of the points). Max length 10,000.

    Args:
        data: numeric series (>= 30 points, <= 10,000)
        hazard_rate: expected run length between changepoints (default 250)
    """
    try:
        parsed = SeriesInput(data=data)
        payload = _ensure_len("detect_changepoints", parsed.data)
        return bridge.call("changepoint", {"data": payload, "hazard_rate": int(hazard_rate)})
    except (RBridgeError, ValueError) as e:
        return _fmt_error("detect_changepoints", e)


@mcp.tool()
def mrcd_outlier_detection(
    data: dict[str, list[float]],
    target: str,
    predictors: list[str],
) -> dict[str, Any]:
    """Robust regression + Cook's distance outlier flagging.

    Fits target ~ predictors, computes Cook's distance, flags rows above the
    4/n threshold. Returns per-row outlier_flags aligned with the input, so
    downsampling is disallowed (would desync rows and mis-flag observations).

    Args:
        data: dict mapping column name -> numeric vector (all same length)
        target: name of response column
        predictors: list of predictor column names
    """
    try:
        if not isinstance(data, dict) or not data:
            raise ValueError("data must be a non-empty dict of {name: [values]}")
        lens = {k: len(v) for k, v in data.items()}
        if len(set(lens.values())) != 1:
            raise ValueError(f"all columns must have same length; got {lens}")
        n = next(iter(lens.values()))
        if n > STRICT_MAX:
            raise ValueError(
                f"mrcd_outlier_detection: {n} rows exceeds max {STRICT_MAX}. "
                f"Pre-filter your data; row-level outlier flags can't be downsampled."
            )
        if target not in data:
            raise ValueError(f"target '{target}' not in data columns {list(data)}")
        missing = [p for p in predictors if p not in data]
        if missing:
            raise ValueError(f"missing predictors: {missing}")
        coerced = {k: _num_list(k, v) for k, v in data.items()}
        return bridge.call("mrcd", {"data": coerced, "target": target, "predictors": predictors})
    except (RBridgeError, ValueError) as e:
        return _fmt_error("mrcd_outlier_detection", e)


@mcp.tool()
def money_flow_index(
    high: list[float],
    low: list[float],
    close: list[float],
    volume: list[float],
    window: int = 14,
) -> dict[str, Any]:
    """Money Flow Index — volume-weighted momentum oscillator (0–100).

    >80 overbought, <20 oversold. Requires contiguous OHLCV bars — the server
    refuses to downsample (would break the rolling-window semantics). Max
    length 10,000 per series.
    """
    try:
        lengths = {k: len(v) for k, v in zip(("high", "low", "close", "volume"),
                                              (high, low, close, volume))}
        if len(set(lengths.values())) != 1:
            raise ValueError(f"high/low/close/volume must be same length; got {lengths}")
        n = next(iter(lengths.values()))
        if n < window + 2:
            raise ValueError(f"need at least {window + 2} bars, got {n}")
        if n > STRICT_MAX:
            raise ValueError(f"money_flow_index: {n} bars exceeds max {STRICT_MAX}")
        return bridge.call(
            "mfi",
            {
                "high": _num_list("high", high),
                "low": _num_list("low", low),
                "close": _num_list("close", close),
                "volume": _num_list("volume", volume),
                "window": int(window),
            },
        )
    except (RBridgeError, ValueError) as e:
        return _fmt_error("money_flow_index", e)


@mcp.tool()
def tsrepr_features(data: list[float]) -> dict[str, Any]:
    """Compress a cyclical window (e.g. 24 hourly obs) into 8 shape features.

    Returns: max_1, sum_1, max_0, cross, f_0, l_0, f_1, l_1 — feature-clipping
    representation of the above/below-mean run structure. Designed for short
    cyclical windows (4–256 points); downsampling destroys the cycle phase,
    so the server rejects oversized inputs.
    """
    try:
        parsed = SeriesInput(data=data)
        if len(parsed.data) > 1024:
            raise ValueError(
                f"tsrepr_features: {len(parsed.data)} points. This tool is "
                f"designed for short cyclical windows (typically ≤ 256 points). "
                f"Downsampling would alias the cycle; aggregate or segment first."
            )
        return bridge.call("tsrepr", {"data": parsed.data})
    except (RBridgeError, ValueError) as e:
        return _fmt_error("tsrepr_features", e)


@mcp.tool()
def bayesian_nowcast(
    historical: list[float],
    signals: dict[str, dict[str, float]],
    day_of_quarter: int | None = None,
) -> dict[str, Any]:
    """Sequentially update a Normal-Normal posterior forecast as signals arrive.

    Args:
        historical: past quarterly outcomes (defines prior, 4–1000 points)
        signals: dict of {name: {"value": float, "weight": float in (0,1]}}
            Weight reflects how informative the signal is relative to prior.
        day_of_quarter: optional, for uncertainty-reduction reporting
    """
    try:
        if len(historical) < 4 or len(historical) > 1000:
            raise ValueError(f"historical must have 4–1000 points, got {len(historical)}")
        if not isinstance(signals, dict):
            raise ValueError("signals must be a dict of {name: {value, weight}}")
        for nm, s in signals.items():
            if not isinstance(s, dict) or "value" not in s or "weight" not in s:
                raise ValueError(f"signal '{nm}' must have 'value' and 'weight' keys")
        payload: dict[str, Any] = {
            "historical": _num_list("historical", historical),
            "signals": signals,
        }
        if day_of_quarter is not None:
            payload["day_of_quarter"] = int(day_of_quarter)
        return bridge.call("nowcast", payload)
    except (RBridgeError, ValueError) as e:
        return _fmt_error("bayesian_nowcast", e)


@mcp.tool()
def plot_series(
    plot_type: Literal["line", "histogram", "scatter"] = "line",
    data: list[float] | None = None,
    x: list[float] | None = None,
    y: list[float] | None = None,
    title: str = "",
    bins: int = 30,
    width: int = 70,
    height: int = 16,
) -> dict[str, Any]:
    """Render a ggplot2 chart as ASCII text Claude can read directly.

    Three modes:
      - `line`: time series of `data` (x-axis is index). Use after
        `catch22_features` / `detect_changepoints` to visualize the series
        you just characterized.
      - `histogram`: distribution of `data` with `bins` buckets. Pair with
        `describe_data` to inspect skew/outliers visually.
      - `scatter`: scatter of `(x, y)`. Pair with `mrcd_outlier_detection`
        to see flagged outliers in context.

    Returns a text `plot` field (ASCII, ~1-2 KB) plus a short
    `interpretation` summarizing what was plotted.
    """
    try:
        payload: dict[str, Any] = {
            "plot_type": plot_type,
            "title": title,
            "bins": int(bins),
            "width": int(width),
            "height": int(height),
        }
        if plot_type in ("line", "histogram"):
            if data is None:
                raise ValueError(f"{plot_type}: 'data' is required")
            payload["data"] = _ensure_len(f"plot_series({plot_type})", _num_list("data", data))
        elif plot_type == "scatter":
            if x is None or y is None:
                raise ValueError("scatter: both 'x' and 'y' are required")
            if len(x) != len(y):
                raise ValueError(f"scatter: x and y must have same length ({len(x)} vs {len(y)})")
            payload["x"] = _ensure_len("plot_series(scatter).x", _num_list("x", x))
            payload["y"] = _ensure_len("plot_series(scatter).y", _num_list("y", y))
        return bridge.call("plot", payload)
    except (RBridgeError, ValueError) as e:
        return _fmt_error("plot_series", e)


if __name__ == "__main__":
    mcp.run(transport="stdio")

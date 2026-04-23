"""Integration tests. Requires Plumber server running on :8787."""

from __future__ import annotations

import math
import random

import httpx
import pytest

BASE = "http://127.0.0.1:8787"


def _server_up() -> bool:
    try:
        return httpx.get(f"{BASE}/health", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _server_up(), reason="Plumber server not running on :8787")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


def _sine(n=200, noise=0.1, seed=1):
    random.seed(seed)
    return [math.sin(i / 10) + random.gauss(0, noise) for i in range(n)]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["tools"] == 8


def test_describe(client):
    r = client.post("/describe", json={"data": _sine()})
    j = r.json()
    assert j["n_finite"] == 200
    assert "interpretation" in j


def test_catch22(client):
    r = client.post("/catch22", json={"data": _sine()})
    j = r.json()
    assert "features" in j
    assert len(j["features"]) == 22
    assert "interpretation" in j


def test_changepoint(client):
    # series with a clear mean shift
    a = [random.gauss(0, 1) for _ in range(100)]
    b = [random.gauss(5, 1) for _ in range(100)]
    r = client.post("/changepoint", json={"data": a + b, "hazard_rate": 100})
    j = r.json()
    assert "n_changepoints" in j
    assert "interpretation" in j


def test_mrcd(client):
    random.seed(42)
    x1 = [random.gauss(0, 1) for _ in range(100)]
    x2 = [random.gauss(0, 1) for _ in range(100)]
    y = [2 * a + 3 * b + random.gauss(0, 0.5) for a, b in zip(x1, x2)]
    y[50] = 100.0
    payload = {
        "data": {"y": y, "x1": x1, "x2": x2},
        "target": "y",
        "predictors": ["x1", "x2"],
    }
    j = client.post("/mrcd", json=payload).json()
    assert j["n"] == 100
    assert j["outlier_flags"][50] == 1


def test_mfi(client):
    random.seed(0)
    close = [100 + random.gauss(0, 2) for _ in range(50)]
    high = [c + abs(random.gauss(0, 1)) for c in close]
    low = [c - abs(random.gauss(0, 1)) for c in close]
    volume = [1_000_000 + random.gauss(0, 100_000) for _ in range(50)]
    j = client.post(
        "/mfi",
        json={"high": high, "low": low, "close": close, "volume": volume, "window": 14},
    ).json()
    assert 0 <= j["latest"] <= 100
    assert j["signal"] in {"overbought", "oversold", "neutral", "insufficient data"}


def test_tsrepr(client):
    j = client.post("/tsrepr", json={"data": [1, 2, 3, 4, 5, 4, 3, 2, 1] * 3}).json()
    assert "features" in j
    assert set(j["features"].keys()) == {
        "max_1", "sum_1", "max_0", "cross", "f_0", "l_0", "f_1", "l_1"
    }


def test_plot_line(client):
    j = client.post("/plot", json={"plot_type": "line", "data": _sine(), "title": "sine"}).json()
    assert "plot" in j and len(j["plot"]) > 100
    assert "interpretation" in j


def test_plot_histogram(client):
    j = client.post(
        "/plot",
        json={"plot_type": "histogram", "data": _sine(300), "bins": 25},
    ).json()
    assert "plot" in j and len(j["plot"]) > 100


def test_plot_scatter(client):
    import random as _r
    _r.seed(0)
    xs = [_r.gauss(0, 1) for _ in range(50)]
    ys = [2 * a + _r.gauss(0, 0.5) for a in xs]
    j = client.post("/plot", json={"plot_type": "scatter", "x": xs, "y": ys}).json()
    assert "plot" in j and len(j["plot"]) > 100


def test_nowcast(client):
    j = client.post(
        "/nowcast",
        json={
            "historical": [100, 105, 110, 102, 108, 111, 104, 106],
            "signals": {
                "google_trends": {"value": 115, "weight": 0.4},
                "web_signal": {"value": 112, "weight": 0.3},
            },
            "day_of_quarter": 45,
        },
    ).json()
    assert "point_estimate" in j
    assert len(j["ci_95"]) == 2
    assert j["n_signals"] == 2

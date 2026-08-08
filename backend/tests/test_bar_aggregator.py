from __future__ import annotations

from app.services.bar_aggregator import BarAggregator


def test_bar_aggregator_uses_delta_volume() -> None:
    aggregator = BarAggregator()
    first = {
        "symbol": "SH.600519",
        "price": 10.0,
        "volume": 1000,
        "turnover": 10000,
        "timestamp": 1786032000000,
    }
    second = {
        "symbol": "SH.600519",
        "price": 11.0,
        "volume": 1015,
        "turnover": 10180,
        "timestamp": 1786032060000,
    }
    aggregator.update(first, periods=("1m",))
    updates = aggregator.update(second, periods=("1m",))
    bar = updates[0]["data"]
    assert bar["open"] == 11.0
    assert bar["volume"] == 15.0
    assert bar["turnover"] == 180.0


def test_bar_aggregator_ignores_negative_delta() -> None:
    aggregator = BarAggregator()
    aggregator.update({"symbol": "SH.600519", "price": 10.0, "volume": 1000, "turnover": 10000, "timestamp": 1786032000000})
    updates = aggregator.update(
        {"symbol": "SH.600519", "price": 11.0, "volume": 10, "turnover": 100, "timestamp": 1786032001000},
        periods=("1m",),
    )
    assert updates[0]["data"]["volume"] == 0.0

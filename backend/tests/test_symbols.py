from __future__ import annotations

from app.utils.symbols import canonical_symbol, normalize_period


def test_canonical_symbol() -> None:
    assert canonical_symbol("600519") == "SH.600519"
    assert canonical_symbol("000001") == "SZ.000001"
    assert canonical_symbol("sz.300750") == "SZ.300750"


def test_normalize_period_month_vs_minute() -> None:
    assert normalize_period("1m") == "1m"
    assert normalize_period("1M") == "1M"
    assert normalize_period("monthly") == "1M"

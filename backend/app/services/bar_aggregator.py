from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.utils.time import SH_TZ, to_timestamp_ms


@dataclass(slots=True)
class BarState:
    period: str
    bucket_start: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    turnover: float = 0.0


class BarAggregator:
    def __init__(self):
        self._bars: dict[tuple[str, str], BarState] = {}
        self._last_snapshot: dict[str, dict[str, Any]] = {}

    def update(self, quote: dict[str, Any], periods: tuple[str, ...] = ("1m", "5m", "15m", "30m", "60m", "1d")) -> list[dict[str, Any]]:
        symbol = quote["symbol"]
        price = float(quote.get("price") or 0)
        if price <= 0:
            return []
        timestamp_ms = int(quote.get("timestamp") or to_timestamp_ms(datetime.now(tz=SH_TZ)))
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=SH_TZ)
        delta_volume, delta_turnover = self._delta(symbol, quote)
        updates = []
        for period in periods:
            bucket = self._bucket_start(dt, period)
            key = (symbol, period)
            state = self._bars.get(key)
            if state is None or state.bucket_start != bucket:
                state = BarState(period=period, bucket_start=bucket, open=price, high=price, low=price, close=price)
                self._bars[key] = state
            else:
                state.high = max(state.high, price)
                state.low = min(state.low, price)
                state.close = price
            state.volume += max(delta_volume, 0.0)
            state.turnover += max(delta_turnover, 0.0)
            updates.append(
                {
                    "type": "bar",
                    "symbol": symbol,
                    "period": period,
                    "data": {
                        "timestamp": to_timestamp_ms(state.bucket_start),
                        "open": state.open,
                        "high": state.high,
                        "low": state.low,
                        "close": state.close,
                        "volume": state.volume,
                        "turnover": state.turnover,
                    },
                }
            )
        return updates

    def _delta(self, symbol: str, quote: dict[str, Any]) -> tuple[float, float]:
        current_volume = float(quote.get("volume") or 0)
        current_turnover = float(quote.get("turnover") or 0)
        previous = self._last_snapshot.get(symbol)
        self._last_snapshot[symbol] = {"volume": current_volume, "turnover": current_turnover, "timestamp": quote.get("timestamp")}
        if not previous:
            return 0.0, 0.0
        delta_volume = current_volume - float(previous.get("volume") or 0)
        delta_turnover = current_turnover - float(previous.get("turnover") or 0)
        if delta_volume < 0 or delta_turnover < 0:
            return 0.0, 0.0
        return delta_volume, delta_turnover

    @staticmethod
    def _bucket_start(dt: datetime, period: str) -> datetime:
        dt = dt.astimezone(SH_TZ).replace(second=0, microsecond=0)
        if period == "1d":
            return dt.replace(hour=0, minute=0)
        minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60}[period]
        total = dt.hour * 60 + dt.minute
        bucket_minutes = total - total % minutes
        return dt.replace(hour=0, minute=0) + timedelta(minutes=bucket_minutes)

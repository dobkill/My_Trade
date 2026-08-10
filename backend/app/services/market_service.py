from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd

from app.market_data.manager import MarketDataManager
from app.storage.parquet_store import ParquetStore
from app.utils.symbols import canonical_symbol, normalize_adjust, normalize_period
from app.utils.time import parse_datetime, to_timestamp_ms

logger = logging.getLogger(__name__)


class MarketService:
    def __init__(self, manager: MarketDataManager, store: ParquetStore):
        self.manager = manager
        self.store = store

    async def health(self) -> dict[str, Any]:
        return await self.manager.health()

    async def search_symbols(self, q: str) -> list[dict[str, Any]]:
        return await self.manager.search_symbols(q)

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        return await self.manager.get_quote(symbol)

    async def get_order_book(self, symbol: str) -> dict[str, Any]:
        return await self.manager.get_order_book(symbol)

    async def get_ticks(self, symbol: str) -> list[dict[str, Any]]:
        return await self.manager.get_ticks(symbol)

    async def get_klines(
        self,
        symbol: str,
        period: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "none",
    ) -> pd.DataFrame:
        started = time.perf_counter()
        canonical = canonical_symbol(symbol)
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
        start_ms = to_timestamp_ms(start_dt) if start_dt else None
        end_ms = to_timestamp_ms(end_dt) if end_dt else None
        cached = self.store.read(canonical, norm_period, norm_adjust, start_ms=start_ms, end_ms=end_ms)
        if self._cache_covers(cached, start_ms, end_ms):
            logger.info(
                "market_data provider=parquet symbol=%s period=%s cache=hit duration=%.3f",
                canonical,
                norm_period,
                time.perf_counter() - started,
            )
            return cached
        logger.info("market_data symbol=%s period=%s cache=miss", canonical, norm_period)
        frame = await self.manager.get_history(canonical, norm_period, start=start_dt, end=end_dt, adjust=norm_adjust)
        if not frame.empty:
            self.store.upsert(frame)
        logger.info(
            "market_data symbol=%s period=%s rows=%s duration=%.3f",
            canonical,
            norm_period,
            len(frame),
            time.perf_counter() - started,
        )
        return frame

    def kline_response(self, symbol: str, period: str, adjust: str, frame: pd.DataFrame) -> dict[str, Any]:
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        source = "cache" if frame.empty or "source" not in frame.columns else str(frame.iloc[-1]["source"])
        rows = [
            {
                "timestamp": int(row.timestamp),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
                "turnover": float(row.turnover),
            }
            for row in frame.itertuples(index=False)
        ]
        return {"symbol": canonical_symbol(symbol), "period": norm_period, "adjust": norm_adjust, "source": source, "data": rows}

    @staticmethod
    def _cache_covers(frame: pd.DataFrame, start_ms: int | None, end_ms: int | None) -> bool:
        if frame.empty:
            return False
        # Minute public histories are limited; local data is authoritative once present for unbounded UI requests.
        if start_ms is None and end_ms is None:
            return True
        min_ts = int(frame["timestamp"].min())
        max_ts = int(frame["timestamp"].max())
        return (start_ms is None or min_ts <= start_ms) and (end_ms is None or max_ts >= end_ms)

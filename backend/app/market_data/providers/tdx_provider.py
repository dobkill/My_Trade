from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.market_data.base import MarketDataError, MarketDataProvider, ProviderStatus
from app.utils.symbols import canonical_symbol, normalize_adjust, normalize_period, symbol_to_tdx, tdx_to_symbol
from app.utils.time import SH_TZ, market_status, to_timestamp_ms

logger = logging.getLogger(__name__)


class TdxProvider(MarketDataProvider):
    name = "tdx"

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self._client: Any | None = None
        self._lock = asyncio.Lock()
        self._symbols_cache: tuple[float, list[dict[str, Any]]] | None = None

    async def health_check(self) -> ProviderStatus:
        try:
            pong = await asyncio.to_thread(self._ping)
            return ProviderStatus(provider=self.name, available=pong == "pong", message=str(pong))
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus(provider=self.name, available=False, message=str(exc))

    async def search_symbols(self, keyword: str) -> list[dict[str, Any]]:
        symbols = await self._load_symbols()
        q = keyword.strip().upper()
        if not q:
            return symbols[:50]
        return [item for item in symbols if q in item["symbol"] or q in item["code"] or q in item["name"].upper()][:50]

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        return await self.get_realtime_quote(symbol)

    async def get_realtime_quote(self, symbol: str) -> dict[str, Any]:
        canonical = canonical_symbol(symbol)
        try:
            quote = await asyncio.to_thread(self._get_quote_sync, canonical)
            name = await self._lookup_name(canonical)
            return self._quote_to_dict(quote, canonical, name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider=tdx symbol=%s action=quote error=%s", canonical, exc)
            raise MarketDataError(str(exc), self.name) from exc

    async def get_history(
        self,
        symbol: str,
        period: str,
        start: datetime | None = None,
        end: datetime | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        canonical = canonical_symbol(symbol)
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        try:
            frame = await asyncio.to_thread(self._get_history_sync, canonical, norm_period, norm_adjust)
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider=tdx symbol=%s period=%s action=history error=%s", canonical, norm_period, exc)
            raise MarketDataError(str(exc), self.name) from exc
        if frame.empty:
            raise MarketDataError("TDX returned empty kline data", self.name)
        if start is not None:
            start_dt = start if start.tzinfo else start.replace(tzinfo=SH_TZ)
            frame = frame[frame["datetime"] >= start_dt]
        if end is not None:
            end_dt = end if end.tzinfo else end.replace(tzinfo=SH_TZ)
            frame = frame[frame["datetime"] <= end_dt]
        return frame.reset_index(drop=True)

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                await asyncio.to_thread(self._client.close)
                self._client = None

    def _ping(self) -> str:
        client = self._client_sync()
        return client.ping()

    def _client_sync(self):
        if self._client is None:
            from eltdx import TdxClient

            self._client = TdxClient(timeout=4.0, pool_size=1, probe_hosts=True, probe_timeout=1.0, heartbeat_interval=30.0)
            self._client.connect()
        return self._client

    async def _load_symbols(self) -> list[dict[str, Any]]:
        now = asyncio.get_running_loop().time()
        if self._symbols_cache and now - self._symbols_cache[0] < 24 * 3600:
            return self._symbols_cache[1]
        symbols = await asyncio.to_thread(self._load_symbols_sync)
        self._symbols_cache = (now, symbols)
        return symbols

    def _load_symbols_sync(self) -> list[dict[str, Any]]:
        client = self._client_sync()
        rows: list[dict[str, Any]] = []
        for exchange in ("sh", "sz", "bj"):
            for item in client.get_codes_all(exchange):
                if getattr(item, "category", "") != "a_share":
                    continue
                symbol = tdx_to_symbol(item.exchange, item.code)
                rows.append(
                    {
                        "symbol": symbol,
                        "code": item.code,
                        "name": item.name.strip(),
                        "market": item.exchange.upper(),
                        "source": self.name,
                    }
                )
        rows.sort(key=lambda item: item["symbol"])
        return rows

    async def _lookup_name(self, symbol: str) -> str | None:
        symbols = await self._load_symbols()
        return next((item["name"] for item in symbols if item["symbol"] == symbol), None)

    def _get_quote_sync(self, symbol: str):
        client = self._client_sync()
        quotes = client.get_quote(symbol_to_tdx(symbol))
        if not quotes:
            raise RuntimeError(f"empty quote for {symbol}")
        return quotes[0]

    def _get_history_sync(self, symbol: str, period: str, adjust: str) -> pd.DataFrame:
        client = self._client_sync()
        tdx_period = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "60m": "60m",
            "1d": "day",
            "1w": "week",
            "1M": "month",
        }[period]
        tdx_adjust = None if adjust == "none" else adjust
        code = symbol_to_tdx(symbol)
        if period in {"1d", "1w", "1M"}:
            series = client.get_kline_all(tdx_period, code, adjust=tdx_adjust, page_size=800, max_pages=30)
        else:
            # Free TDX minute bars are limited by the public server; do not synthesize missing history.
            series = client.get_kline(tdx_period, code, adjust=tdx_adjust, count=800)
        rows = []
        for bar in series.bars:
            dt = bar.time if bar.time.tzinfo else bar.time.replace(tzinfo=SH_TZ)
            rows.append(
                {
                    "symbol": symbol,
                    "datetime": dt,
                    "timestamp": to_timestamp_ms(dt),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": float(bar.volume_lots),
                    "turnover": float(bar.amount),
                    "period": period,
                    "adjust": adjust,
                    "source": self.name,
                }
            )
        return pd.DataFrame(rows)

    def _quote_to_dict(self, quote: Any, symbol: str, name: str | None) -> dict[str, Any]:
        now = datetime.now(tz=SH_TZ)
        price = float(getattr(quote, "last_price", 0) or 0)
        pre_close = float(getattr(quote, "pre_close_price", 0) or 0)
        change = price - pre_close if pre_close else None
        change_pct = change / pre_close * 100 if change is not None and pre_close else None
        return {
            "symbol": symbol,
            "name": name,
            "price": price,
            "open": float(getattr(quote, "open_price", 0) or 0),
            "high": float(getattr(quote, "high_price", 0) or 0),
            "low": float(getattr(quote, "low_price", 0) or 0),
            "pre_close": pre_close,
            "change": change,
            "change_pct": change_pct,
            "volume": float(getattr(quote, "total_hand", 0) or 0),
            "turnover": float(getattr(quote, "amount", 0) or 0),
            "timestamp": to_timestamp_ms(now),
            "source": self.name,
            "market_status": market_status(now),
        }

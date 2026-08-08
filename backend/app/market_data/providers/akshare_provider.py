from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.market_data.base import MarketDataError, MarketDataProvider, ProviderStatus
from app.utils.symbols import canonical_symbol, code_to_symbol, normalize_adjust, normalize_period, symbol_to_code
from app.utils.time import SH_TZ, market_status, to_timestamp_ms

logger = logging.getLogger(__name__)


class AKShareProvider(MarketDataProvider):
    name = "akshare"

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.symbol_cache_file = self.cache_dir / "akshare_symbols.parquet"
        self._symbols_cache: tuple[float, pd.DataFrame] | None = None
        self._quote_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    async def health_check(self) -> ProviderStatus:
        try:
            symbols = await self._load_symbols()
            return ProviderStatus(provider=self.name, available=not symbols.empty, message=f"symbols={len(symbols)}")
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus(provider=self.name, available=False, message=str(exc))

    async def search_symbols(self, keyword: str) -> list[dict[str, Any]]:
        df = await self._load_symbols()
        q = keyword.strip().upper()
        if q:
            mask = df["symbol"].str.contains(q, case=False, na=False) | df["code"].str.contains(q, na=False) | df[
                "name"
            ].str.contains(keyword.strip(), case=False, na=False)
            df = df[mask]
        return df.head(50).to_dict("records")

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        return await self.get_realtime_quote(symbol)

    async def get_realtime_quote(self, symbol: str) -> dict[str, Any]:
        canonical = canonical_symbol(symbol)
        now = asyncio.get_running_loop().time()
        cached = self._quote_cache.get(canonical)
        if cached and now - cached[0] < 2.0:
            return cached[1]
        try:
            quote = await asyncio.to_thread(self._get_quote_sync, canonical)
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider=akshare symbol=%s action=quote error=%s", canonical, exc)
            raise MarketDataError(str(exc), self.name) from exc
        self._quote_cache[canonical] = (now, quote)
        return quote

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
        start_dt = start or datetime(1990, 1, 1, tzinfo=SH_TZ)
        end_dt = end or datetime.now(tz=SH_TZ)
        try:
            frame = await asyncio.to_thread(self._get_history_sync, canonical, norm_period, start_dt, end_dt, norm_adjust)
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider=akshare symbol=%s period=%s action=history error=%s", canonical, norm_period, exc)
            raise MarketDataError(str(exc), self.name) from exc
        if frame.empty:
            raise MarketDataError("AKShare returned empty kline data", self.name)
        return frame

    async def _load_symbols(self) -> pd.DataFrame:
        now = asyncio.get_running_loop().time()
        if self._symbols_cache and now - self._symbols_cache[0] < 12 * 3600:
            return self._symbols_cache[1]
        if self.symbol_cache_file.exists():
            mtime_age = datetime.now().timestamp() - self.symbol_cache_file.stat().st_mtime
            if mtime_age < 24 * 3600:
                df = pd.read_parquet(self.symbol_cache_file)
                self._symbols_cache = (now, df)
                return df
        df = await asyncio.to_thread(self._fetch_symbols_sync)
        self._symbols_cache = (now, df)
        return df

    def _fetch_symbols_sync(self) -> pd.DataFrame:
        import akshare as ak

        df = ak.stock_info_a_code_name()
        if df.empty or not {"code", "name"}.issubset(df.columns):
            raise RuntimeError("unexpected AKShare symbol table schema")
        result = df[["code", "name"]].copy()
        result["code"] = result["code"].astype(str).str.zfill(6)
        result["symbol"] = result["code"].map(code_to_symbol)
        result["market"] = result["symbol"].str.split(".").str[0]
        result["source"] = self.name
        result = result[["symbol", "code", "name", "market", "source"]].sort_values("symbol").reset_index(drop=True)
        result.to_parquet(self.symbol_cache_file, index=False)
        return result

    def _get_quote_sync(self, symbol: str) -> dict[str, Any]:
        import akshare as ak

        code = symbol_to_code(symbol)
        spot = ak.stock_zh_a_spot_em()
        if spot.empty:
            raise RuntimeError("empty AKShare realtime spot table")
        code_col = _pick_col(spot, ["代码", "code"])
        row_df = spot[spot[code_col].astype(str).str.zfill(6) == code]
        if row_df.empty:
            raise RuntimeError(f"quote not found for {symbol}")
        row = row_df.iloc[0]
        price = _num(row, ["最新价", "最新", "price"])
        pre_close = _num(row, ["昨收", "pre_close"])
        change = _num(row, ["涨跌额", "change"])
        pct = _num(row, ["涨跌幅", "change_pct"])
        if change is None and price is not None and pre_close:
            change = price - pre_close
        if pct is not None:
            pct = pct if abs(pct) > 1 else pct * 100
        now = datetime.now(tz=SH_TZ)
        return {
            "symbol": symbol,
            "name": str(row.get("名称", "")) or None,
            "price": price,
            "open": _num(row, ["今开", "open"]),
            "high": _num(row, ["最高", "high"]),
            "low": _num(row, ["最低", "low"]),
            "pre_close": pre_close,
            "change": change,
            "change_pct": pct,
            "volume": _num(row, ["成交量", "volume"]),
            "turnover": _num(row, ["成交额", "turnover"]),
            "timestamp": to_timestamp_ms(now),
            "source": self.name,
            "market_status": market_status(now),
        }

    def _get_history_sync(
        self,
        symbol: str,
        period: str,
        start: datetime,
        end: datetime,
        adjust: str,
    ) -> pd.DataFrame:
        import akshare as ak

        code = symbol_to_code(symbol)
        ak_adjust = "" if adjust == "none" else adjust
        if period in {"1d", "1w", "1M"}:
            ak_period = {"1d": "daily", "1w": "weekly", "1M": "monthly"}[period]
            df = ak.stock_zh_a_hist(
                symbol=code,
                period=ak_period,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust=ak_adjust,
                timeout=15,
            )
        else:
            ak_period = period.replace("m", "")
            df = ak.stock_zh_a_hist_min_em(
                symbol=code,
                period=ak_period,
                start_date=start.strftime("%Y-%m-%d %H:%M:%S"),
                end_date=end.strftime("%Y-%m-%d %H:%M:%S"),
                adjust=ak_adjust,
            )
        return _normalize_ak_history(df, symbol, period, adjust, self.name)


def _normalize_ak_history(df: pd.DataFrame, symbol: str, period: str, adjust: str, source: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    time_col = _pick_col(df, ["日期", "时间", "datetime", "date"])
    rows = []
    for _, row in df.iterrows():
        dt = pd.to_datetime(row[time_col]).to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SH_TZ)
        rows.append(
            {
                "symbol": symbol,
                "datetime": dt,
                "timestamp": to_timestamp_ms(dt),
                "open": float(_num(row, ["开盘", "open"]) or 0),
                "high": float(_num(row, ["最高", "high"]) or 0),
                "low": float(_num(row, ["最低", "low"]) or 0),
                "close": float(_num(row, ["收盘", "close"]) or 0),
                "volume": float(_num(row, ["成交量", "volume"]) or 0),
                "turnover": float(_num(row, ["成交额", "turnover"]) or 0),
                "period": period,
                "adjust": adjust,
                "source": source,
            }
        )
    return pd.DataFrame(rows).sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str:
    for col in candidates:
        if col in df.columns:
            return col
    raise RuntimeError(f"missing expected columns {candidates}; got {list(df.columns)}")


def _num(row: Any, candidates: list[str]) -> float | None:
    for col in candidates:
        if col in row.index:
            value = row[col]
            if pd.isna(value) or value == "-":
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None

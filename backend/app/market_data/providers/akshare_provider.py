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

    async def get_order_book(self, symbol: str) -> dict[str, Any]:
        canonical = canonical_symbol(symbol)
        try:
            return await asyncio.to_thread(self._get_order_book_sync, canonical)
        except NotImplementedError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider=akshare symbol=%s action=order_book error=%s", canonical, exc)
            raise MarketDataError(str(exc), self.name) from exc

    def _get_order_book_sync(self, symbol: str) -> dict[str, Any]:
        import akshare as ak

        code = symbol_to_code(symbol)
        func = getattr(ak, "stock_bid_ask_em", None)
        if func is None:
            raise NotImplementedError("akshare.stock_bid_ask_em not available")
        df = func(symbol=code)
        if df is None or df.empty:
            raise RuntimeError(f"empty AKShare order book for {symbol}")
        return _parse_ak_order_book(df, symbol, self.name)

    async def get_ticks(self, symbol: str) -> list[dict[str, Any]]:
        canonical = canonical_symbol(symbol)
        try:
            return await asyncio.to_thread(self._get_ticks_sync, canonical)
        except NotImplementedError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider=akshare symbol=%s action=ticks error=%s", canonical, exc)
            raise MarketDataError(str(exc), self.name) from exc

    def _get_ticks_sync(self, symbol: str) -> list[dict[str, Any]]:
        import akshare as ak

        code = symbol_to_code(symbol)
        func = getattr(ak, "stock_zh_a_tick_tx_js", None)
        if func is None:
            raise NotImplementedError("akshare.stock_zh_a_tick_tx_js not available")
        df = func(symbol=code)
        if df is None or getattr(df, "empty", True):
            return []
        return _parse_ak_ticks(df, symbol, self.name)

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


def _parse_ak_order_book(df: pd.DataFrame, symbol: str, source: str) -> dict[str, Any]:
    """
    解析 akshare stock_bid_ask_em 返回的长表为五档结构。
    返回示例列：item（"买一价"等）、value。这里做容错匹配，兼容中英文表头。
    """
    item_col = _pick_col(df, ["item", "项目", "名称"])
    value_col = _pick_col(df, ["value", "数值", "值"])

    mapping = {
        "买1价": "bid1_price", "买1量": "bid1_volume",
        "买2价": "bid2_price", "买2量": "bid2_volume",
        "买3价": "bid3_price", "买3量": "bid3_volume",
        "买4价": "bid4_price", "买4量": "bid4_volume",
        "买5价": "bid5_price", "买5量": "bid5_volume",
        "卖1价": "ask1_price", "卖1量": "ask1_volume",
        "卖2价": "ask2_price", "卖2量": "ask2_volume",
        "卖3价": "ask3_price", "卖3量": "ask3_volume",
        "卖4价": "ask4_price", "卖4量": "ask4_volume",
        "卖5价": "ask5_price", "卖5量": "ask5_volume",
        "买一价": "bid1_price", "买一量": "bid1_volume",
        "买二价": "bid2_price", "买二量": "bid2_volume",
        "买三价": "bid3_price", "买三量": "bid3_volume",
        "买四价": "bid4_price", "买四量": "bid4_volume",
        "买五价": "bid5_price", "买五量": "bid5_volume",
        "卖一价": "ask1_price", "卖一量": "ask1_volume",
        "卖二价": "ask2_price", "卖二量": "ask2_volume",
        "卖三价": "ask3_price", "卖三量": "ask3_volume",
        "卖四价": "ask4_price", "卖四量": "ask4_volume",
        "卖五价": "ask5_price", "卖五量": "ask5_volume",
    }

    data: dict[str, float] = {}
    if item_col and value_col:
        for _, row in df.iterrows():
            key = str(row[item_col]).strip()
            field = mapping.get(key)
            if not field:
                continue
            try:
                data[field] = float(row[value_col])
            except (TypeError, ValueError):
                continue
    else:
        for col in df.columns:
            field = mapping.get(str(col).strip())
            if field:
                try:
                    data[field] = float(df.iloc[0][col])
                except (TypeError, ValueError):
                    continue

    bids = []
    asks = []
    for i in range(1, 6):
        bids.append({"price": data.get(f"bid{i}_price"), "volume": data.get(f"bid{i}_volume")})
        asks.append({"price": data.get(f"ask{i}_price"), "volume": data.get(f"ask{i}_volume")})

    now = datetime.now(tz=SH_TZ)
    return {
        "symbol": symbol,
        "bids": bids,
        "asks": asks,
        "timestamp": to_timestamp_ms(now),
        "source": source,
    }


def _parse_ak_ticks(df: pd.DataFrame, symbol: str, source: str) -> list[dict[str, Any]]:
    """解析 akshare 当日逐笔成交表为标准 tick 列表。"""
    if df is None or df.empty:
        return []
    time_col = _pick_col(df, ["成交时间", "时间", "datetime", "time"])
    price_col = _pick_col(df, ["成交价", "price"])
    vol_col = _pick_col(df, ["成交量", "volume", "手数"])
    amount_col_candidates = ["成交额", "amount"]
    amount_col = next((c for c in amount_col_candidates if c in df.columns), None)
    type_col_candidates = ["性质", "买卖盘性质", "type"]
    type_col = next((c for c in type_col_candidates if c in df.columns), None)

    today = datetime.now(tz=SH_TZ).date()
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        try:
            raw_time = row[time_col]
            dt = pd.to_datetime(raw_time).to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=SH_TZ)
            if dt.date() != today:
                continue
            tick_type = str(row[type_col]).strip() if type_col else ""
            rows.append(
                {
                    "timestamp": to_timestamp_ms(dt),
                    "price": float(row[price_col]),
                    "volume": float(row[vol_col]) if vol_col else None,
                    "amount": float(row[amount_col]) if amount_col else None,
                    "type": tick_type,
                }
            )
        except (TypeError, ValueError, KeyError):
            continue
    rows.sort(key=lambda item: item["timestamp"])
    # 限制最多 1000 条，避免响应过大
    return rows[-1000:]

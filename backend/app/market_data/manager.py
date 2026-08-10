from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.market_data.base import MarketDataError, MarketDataProvider, ProviderStatus
from app.market_data.providers.akshare_provider import AKShareProvider
from app.market_data.providers.tdx_provider import TdxProvider
from app.utils.symbols import canonical_symbol

logger = logging.getLogger(__name__)


class MarketDataManager:
    def __init__(self, cache_dir: Path, mode: str = "auto"):
        self.akshare = AKShareProvider(cache_dir)
        self.tdx = TdxProvider(cache_dir)
        self.mode = mode.lower()
        self._last_status: dict[str, ProviderStatus] = {}

    @property
    def providers(self) -> list[MarketDataProvider]:
        if self.mode == "akshare":
            return [self.akshare]
        if self.mode == "tdx":
            return [self.tdx]
        return [self.tdx, self.akshare]

    async def health(self) -> dict[str, Any]:
        statuses = []
        for provider in self.providers:
            status = await provider.health_check()
            self._last_status[provider.name] = status
            statuses.append(asdict(status))
        active = next((item["provider"] for item in statuses if item["available"]), None)
        return {"active_provider": active, "providers": statuses}

    async def search_symbols(self, keyword: str) -> list[dict[str, Any]]:
        errors: list[str] = []
        for provider in self.providers:
            try:
                rows = await provider.search_symbols(keyword)
                if rows:
                    return rows
                errors.append(f"{provider.name}: empty result")
            except Exception as exc:  # noqa: BLE001
                logger.warning("provider=%s action=search error=%s", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")
        raise MarketDataError("; ".join(errors) or "symbol search unavailable", "manager")

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        canonical = canonical_symbol(symbol)
        errors: list[str] = []
        for provider in self.providers:
            try:
                quote = await provider.get_quote(canonical)
                quote["source"] = provider.name
                return quote
            except Exception as exc:  # noqa: BLE001
                logger.warning("provider=%s symbol=%s action=quote fallback=true error=%s", provider.name, canonical, exc)
                errors.append(f"{provider.name}: {exc}")
        raise MarketDataError("; ".join(errors) or "quote unavailable", "manager")

    async def get_realtime_quote(self, symbol: str) -> dict[str, Any]:
        return await self.get_quote(symbol)

    async def get_order_book(self, symbol: str) -> dict[str, Any]:
        canonical = canonical_symbol(symbol)
        errors: list[str] = []
        for provider in self.providers:
            try:
                book = await provider.get_order_book(canonical)
                book["source"] = provider.name
                return book
            except NotImplementedError:
                errors.append(f"{provider.name}: unsupported")
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("provider=%s symbol=%s action=order_book fallback=true error=%s", provider.name, canonical, exc)
                errors.append(f"{provider.name}: {exc}")
        raise MarketDataError("; ".join(errors) or "order book unavailable", "manager")

    async def get_ticks(self, symbol: str) -> list[dict[str, Any]]:
        canonical = canonical_symbol(symbol)
        errors: list[str] = []
        for provider in self.providers:
            try:
                ticks = await provider.get_ticks(canonical)
                for item in ticks:
                    item["source"] = provider.name
                return ticks
            except NotImplementedError:
                errors.append(f"{provider.name}: unsupported")
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("provider=%s symbol=%s action=ticks fallback=true error=%s", provider.name, canonical, exc)
                errors.append(f"{provider.name}: {exc}")
        raise MarketDataError("; ".join(errors) or "ticks unavailable", "manager")

    async def get_history(
        self,
        symbol: str,
        period: str,
        start: datetime | None = None,
        end: datetime | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        canonical = canonical_symbol(symbol)
        errors: list[str] = []
        for provider in self.providers:
            try:
                frame = await provider.get_history(canonical, period, start=start, end=end, adjust=adjust)
                if not frame.empty:
                    return frame
                errors.append(f"{provider.name}: empty frame")
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "provider=%s symbol=%s period=%s action=history fallback=true error=%s",
                    provider.name,
                    canonical,
                    period,
                    exc,
                )
                errors.append(f"{provider.name}: {exc}")
        raise MarketDataError("; ".join(errors) or "history unavailable", "manager")

    async def close(self) -> None:
        await self.tdx.close()

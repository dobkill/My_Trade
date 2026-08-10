from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


class MarketDataError(RuntimeError):
    def __init__(self, message: str, provider: str, code: str = "MARKET_DATA_UNAVAILABLE"):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.code = code


@dataclass(slots=True)
class ProviderStatus:
    provider: str
    available: bool
    message: str = ""


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    async def search_symbols(self, keyword: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_quote(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        period: str,
        start: datetime | None = None,
        end: datetime | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    async def get_realtime_quote(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_order_book(self, symbol: str) -> dict[str, Any]:
        """五档买卖盘。默认未实现，由支持的 provider 覆写。"""
        raise NotImplementedError

    async def get_ticks(self, symbol: str) -> list[dict[str, Any]]:
        """当日逐笔成交明细。默认未实现，由支持的 provider 覆写。"""
        raise NotImplementedError

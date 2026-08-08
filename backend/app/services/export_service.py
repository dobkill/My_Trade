from __future__ import annotations

from pathlib import Path

from app.services.market_service import MarketService
from app.storage.parquet_store import ParquetStore
from app.utils.symbols import normalize_adjust, normalize_period


class ExportService:
    def __init__(self, market_service: MarketService, store: ParquetStore):
        self.market_service = market_service
        self.store = store

    async def export(
        self,
        symbol: str,
        period: str,
        file_format: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "none",
    ) -> Path:
        frame = await self.market_service.get_klines(symbol, period, start=start, end=end, adjust=adjust)
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        if file_format == "csv":
            return self.store.export_csv(frame, symbol, norm_period, norm_adjust)
        if file_format == "parquet":
            return self.store.export_parquet(frame, symbol, norm_period, norm_adjust)
        raise ValueError("format must be csv or parquet")

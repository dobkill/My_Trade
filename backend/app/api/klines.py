from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_market_service
from app.services.market_service import MarketService

router = APIRouter(prefix="/stocks", tags=["klines"])


@router.get("/{symbol}/klines")
async def get_klines(
    symbol: str,
    period: str = Query(default="1d"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    adjust: str = Query(default="none"),
    service: MarketService = Depends(get_market_service),
):
    frame = await service.get_klines(symbol, period, start=start, end=end, adjust=adjust)
    return service.kline_response(symbol, period, adjust, frame)

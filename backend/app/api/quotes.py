from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_market_service
from app.services.market_service import MarketService

router = APIRouter(prefix="/stocks", tags=["quotes"])


@router.get("/{symbol}/quote")
async def get_quote(symbol: str, service: MarketService = Depends(get_market_service)):
    return await service.get_quote(symbol)


@router.get("/{symbol}/order_book")
async def get_order_book(symbol: str, service: MarketService = Depends(get_market_service)):
    """五档买卖盘。"""
    return await service.get_order_book(symbol)


@router.get("/{symbol}/ticks")
async def get_ticks(symbol: str, service: MarketService = Depends(get_market_service)):
    """当日逐笔成交明细。"""
    ticks = await service.get_ticks(symbol)
    return {"symbol": symbol, "data": ticks}

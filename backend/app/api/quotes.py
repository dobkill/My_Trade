from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_market_service
from app.services.market_service import MarketService

router = APIRouter(prefix="/stocks", tags=["quotes"])


@router.get("/{symbol}/quote")
async def get_quote(symbol: str, service: MarketService = Depends(get_market_service)):
    return await service.get_quote(symbol)

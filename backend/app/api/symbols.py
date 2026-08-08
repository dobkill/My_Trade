from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_market_service
from app.services.market_service import MarketService

router = APIRouter(prefix="/symbols", tags=["symbols"])


@router.get("/search")
async def search_symbols(q: str = Query(default="", max_length=64), service: MarketService = Depends(get_market_service)):
    return {"data": await service.search_symbols(q)}

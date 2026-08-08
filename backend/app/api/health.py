from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_market_service
from app.services.market_service import MarketService

router = APIRouter()


@router.get("/health")
async def health(service: MarketService = Depends(get_market_service)):
    provider_health = await service.health()
    return {"status": "ok", **provider_health}

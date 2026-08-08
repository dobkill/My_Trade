from __future__ import annotations

from fastapi import Request

from app.services.export_service import ExportService
from app.services.market_service import MarketService
from app.services.realtime_service import RealtimeService


def get_market_service(request: Request) -> MarketService:
    return request.app.state.market_service


def get_export_service(request: Request) -> ExportService:
    return request.app.state.export_service


def get_realtime_service(request: Request) -> RealtimeService:
    return request.app.state.realtime_service

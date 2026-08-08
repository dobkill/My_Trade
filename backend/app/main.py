from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import export, health, klines, quotes, symbols, websocket
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.market_data.base import MarketDataError
from app.market_data.manager import MarketDataManager
from app.services.export_service import ExportService
from app.services.market_service import MarketService
from app.services.realtime_service import RealtimeService
from app.storage.parquet_store import ParquetStore

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    data_dir = settings.resolved_data_dir
    (data_dir / "cache").mkdir(parents=True, exist_ok=True)
    manager = MarketDataManager(data_dir / "cache", mode=settings.market_data_provider)
    store = ParquetStore(data_dir)
    market_service = MarketService(manager, store)
    app.state.market_manager = manager
    app.state.parquet_store = store
    app.state.market_service = market_service
    app.state.export_service = ExportService(market_service, store)
    app.state.realtime_service = RealtimeService(manager, poll_seconds=settings.realtime_poll_seconds)
    try:
        yield
    finally:
        await app.state.realtime_service.shutdown()
        await app.state.market_manager.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="A-Trade A股行情研究终端", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(symbols.router, prefix="/api")
    app.include_router(quotes.router, prefix="/api")
    app.include_router(klines.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(websocket.router)

    @app.exception_handler(MarketDataError)
    async def market_data_error_handler(_: Request, exc: MarketDataError):
        return JSONResponse(
            status_code=503,
            content={"detail": {"code": exc.code, "message": exc.message, "provider": exc.provider}},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": {"code": "BAD_REQUEST", "message": str(exc)}})

    return app


app = create_app()

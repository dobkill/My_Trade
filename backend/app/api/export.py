from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.api.deps import get_export_service
from app.services.export_service import ExportService
from app.utils.symbols import canonical_symbol, normalize_adjust, normalize_period

router = APIRouter(prefix="/stocks", tags=["export"])


@router.get("/{symbol}/export")
async def export_history(
    symbol: str,
    period: str = Query(default="1d"),
    format: str = Query(default="csv", pattern="^(csv|parquet)$"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    adjust: str = Query(default="none"),
    service: ExportService = Depends(get_export_service),
):
    path = await service.export(symbol, period, format, start=start, end=end, adjust=adjust)
    canonical = canonical_symbol(symbol)
    norm_period = normalize_period(period)
    norm_adjust = normalize_adjust(adjust)
    media_type = "text/csv" if format == "csv" else "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=f"{canonical}_{norm_period}_{norm_adjust}.{format}")

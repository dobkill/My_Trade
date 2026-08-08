from __future__ import annotations

from pydantic import BaseModel


class KLine(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float


class KLineResponse(BaseModel):
    symbol: str
    period: str
    adjust: str
    source: str
    data: list[KLine]

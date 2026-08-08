from __future__ import annotations

from pydantic import BaseModel



class Quote(BaseModel):
    symbol: str
    name: str | None = None
    price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    pre_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    turnover: float | None = None
    timestamp: int
    source: str
    market_status: str

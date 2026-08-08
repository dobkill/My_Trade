from __future__ import annotations

from pydantic import BaseModel


class StockSymbol(BaseModel):
    symbol: str
    code: str
    name: str
    market: str
    source: str

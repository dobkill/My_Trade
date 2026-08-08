from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


SH_TZ = ZoneInfo("Asia/Shanghai")


def ensure_shanghai(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=SH_TZ)
    return dt.astimezone(SH_TZ)


def to_timestamp_ms(dt: datetime) -> int:
    return int(ensure_shanghai(dt).timestamp() * 1000)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d").replace(tzinfo=SH_TZ)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return ensure_shanghai(parsed)


def market_status(now: datetime | None = None) -> str:
    current = ensure_shanghai(now or datetime.now(tz=SH_TZ))
    if current.weekday() >= 5:
        return "closed"
    morning = time(9, 30) <= current.time() <= time(11, 30)
    afternoon = time(13, 0) <= current.time() <= time(15, 0)
    return "open" if morning or afternoon else "closed"

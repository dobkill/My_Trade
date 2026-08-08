from __future__ import annotations

import re


def normalize_adjust(adjust: str | None) -> str:
    value = (adjust or "").lower().strip()
    if value in {"", "none", "no", "0"}:
        return "none"
    if value in {"qfq", "front"}:
        return "qfq"
    if value in {"hfq", "back"}:
        return "hfq"
    raise ValueError(f"unsupported adjust: {adjust}")


def normalize_period(period: str) -> str:
    raw = period.strip()
    lower = raw.lower()
    if raw == "1M" or lower in {"1mo", "1mon", "month", "monthly"}:
        return "1M"
    mapping = {
        "1": "1m",
        "1min": "1m",
        "1m": "1m",
        "5": "5m",
        "5min": "5m",
        "5m": "5m",
        "15": "15m",
        "15min": "15m",
        "15m": "15m",
        "30": "30m",
        "30min": "30m",
        "30m": "30m",
        "60": "60m",
        "60min": "60m",
        "60m": "60m",
        "1h": "60m",
        "day": "1d",
        "daily": "1d",
        "1d": "1d",
        "d": "1d",
        "week": "1w",
        "weekly": "1w",
        "1w": "1w",
        "w": "1w",
        "1mo": "1M",
        "1mth": "1M",
    }
    if raw in mapping:
        return mapping[raw]
    if lower in mapping:
        return mapping[lower]
    raise ValueError(f"unsupported period: {period}")


def canonical_symbol(symbol: str) -> str:
    raw = symbol.strip().upper().replace("_", ".").replace("-", ".")
    if re.fullmatch(r"(SH|SZ|BJ)\.\d{6}", raw):
        return raw
    compact = raw.replace(".", "")
    match = re.fullmatch(r"(SH|SZ|BJ)?(\d{6})", compact)
    if not match:
        raise ValueError(f"invalid A-share symbol: {symbol}")
    prefix, code = match.groups()
    if prefix:
        return f"{prefix}.{code}"
    if code.startswith(("6", "9")):
        return f"SH.{code}"
    if code.startswith(("0", "2", "3")):
        return f"SZ.{code}"
    if code.startswith(("4", "8")):
        return f"BJ.{code}"
    return f"SZ.{code}"


def symbol_to_code(symbol: str) -> str:
    return canonical_symbol(symbol).split(".", 1)[1]


def symbol_to_tdx(symbol: str) -> str:
    market, code = canonical_symbol(symbol).split(".", 1)
    return f"{market.lower()}{code}"


def tdx_to_symbol(exchange: str, code: str) -> str:
    return f"{exchange.upper()}.{code}"


def code_to_symbol(code: str) -> str:
    return canonical_symbol(code)

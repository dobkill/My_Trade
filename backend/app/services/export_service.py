from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.services.market_service import MarketService
from app.storage.parquet_store import ParquetStore
from app.utils.symbols import normalize_adjust, normalize_period
from app.utils.time import SH_TZ, parse_datetime


AI_EXPORT_SCHEMA_VERSION = "ai-bars-v1"
AI_FEATURE_COLUMNS = [
    "feature_return_1",
    "feature_gap_ratio",
    "feature_oc_ratio",
    "feature_hl_ratio",
    "feature_intrabar_position",
    "feature_volume_change_ratio_1",
    "feature_turnover_change_ratio_1",
    "feature_close_ma5_ratio",
    "feature_close_ma20_ratio",
    "feature_volume_z20",
    "feature_volatility_20",
    "feature_day_of_week",
    "feature_month",
]
AI_TARGET_COLUMNS = [
    "target_return_1",
    "target_direction_1",
    "target_return_5",
    "target_direction_5",
]


class ExportService:
    def __init__(self, market_service: MarketService, store: ParquetStore):
        self.market_service = market_service
        self.store = store

    async def export(
        self,
        symbol: str,
        period: str,
        file_format: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "none",
        profile: str = "raw",
    ) -> Path:
        frame = await self.market_service.get_klines(symbol, period, start=start, end=end, adjust=adjust)
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        norm_profile = normalize_export_profile(profile)
        start_label, end_label = _range_labels(frame, start, end)
        if norm_profile == "ai":
            if file_format != "csv":
                raise ValueError("AI export currently supports csv only")
            ai_frame = self.build_ai_frame(frame)
            return self.store.export_csv(
                ai_frame,
                symbol,
                norm_period,
                norm_adjust,
                profile=norm_profile,
                start_label=start_label,
                end_label=end_label,
                clean=False,
            )
        if file_format == "csv":
            return self.store.export_csv(
                frame,
                symbol,
                norm_period,
                norm_adjust,
                profile=norm_profile,
                start_label=start_label,
                end_label=end_label,
            )
        if file_format == "parquet":
            return self.store.export_parquet(
                frame,
                symbol,
                norm_period,
                norm_adjust,
                profile=norm_profile,
                start_label=start_label,
                end_label=end_label,
            )
        raise ValueError("format must be csv or parquet")

    def build_ai_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        frame = self.store.clean_bars(df)
        if frame.empty:
            return pd.DataFrame(columns=_ai_export_columns())

        result = frame.copy()
        result["bar_index"] = range(len(result))
        close = result["close"].astype("float64")
        open_ = result["open"].astype("float64")
        high = result["high"].astype("float64")
        low = result["low"].astype("float64")
        volume = result["volume"].astype("float64")
        turnover = result["turnover"].astype("float64")
        prev_close = close.shift(1)

        result["schema_version"] = AI_EXPORT_SCHEMA_VERSION
        result["feature_return_1"] = _safe_ratio(close - prev_close, prev_close)
        result["feature_gap_ratio"] = _safe_ratio(open_ - prev_close, prev_close)
        result["feature_oc_ratio"] = _safe_ratio(close - open_, open_)
        result["feature_hl_ratio"] = _safe_ratio(high - low, close)
        result["feature_intrabar_position"] = _safe_ratio(close - low, high - low, use_abs_denominator=False)
        result["feature_volume_change_ratio_1"] = _safe_ratio(volume - volume.shift(1), volume.shift(1))
        result["feature_turnover_change_ratio_1"] = _safe_ratio(turnover - turnover.shift(1), turnover.shift(1))

        ma5 = close.rolling(5, min_periods=5).mean()
        ma20 = close.rolling(20, min_periods=20).mean()
        volume_mean20 = volume.rolling(20, min_periods=20).mean()
        volume_std20 = volume.rolling(20, min_periods=20).std()
        result["feature_close_ma5_ratio"] = _safe_ratio(close - ma5, ma5)
        result["feature_close_ma20_ratio"] = _safe_ratio(close - ma20, ma20)
        result["feature_volume_z20"] = _safe_ratio(volume - volume_mean20, volume_std20, use_abs_denominator=False)
        result["feature_volatility_20"] = result["feature_return_1"].rolling(20, min_periods=20).std()

        datetimes = pd.to_datetime(result["datetime"])
        result["feature_day_of_week"] = datetimes.dt.dayofweek
        result["feature_month"] = datetimes.dt.month

        for horizon in (1, 5):
            future_close = close.shift(-horizon)
            result[f"target_return_{horizon}"] = _safe_ratio(future_close - close, close)
            result[f"target_direction_{horizon}"] = _target_direction(close, future_close)

        required_for_training = AI_FEATURE_COLUMNS + AI_TARGET_COLUMNS
        result["is_trainable"] = result[required_for_training].notna().all(axis=1).astype("int64")
        return result[_ai_export_columns()]


def normalize_export_profile(profile: str) -> str:
    text = profile.strip().lower()
    if text in {"raw", "ai"}:
        return text
    raise ValueError("profile must be raw or ai")


def _safe_ratio(
    numerator: pd.Series,
    denominator: pd.Series,
    *,
    use_abs_denominator: bool = True,
) -> pd.Series:
    denom = denominator.abs() if use_abs_denominator else denominator
    return numerator.where(denom.abs() > 1e-12) / denom.where(denom.abs() > 1e-12)


def _target_direction(close: pd.Series, future_close: pd.Series) -> pd.Series:
    direction = pd.Series(pd.NA, index=close.index, dtype="Int64")
    mask = future_close.notna()
    direction.loc[mask] = (future_close.loc[mask] > close.loc[mask]).astype("int64")
    return direction


def _range_labels(df: pd.DataFrame, start: str | None, end: str | None) -> tuple[str | None, str | None]:
    if not start and not end:
        return None, None
    return _range_label_from_request_or_frame(df, start, "start"), _range_label_from_request_or_frame(df, end, "end")


def _range_label_from_request_or_frame(df: pd.DataFrame, value: str | None, edge: str) -> str | None:
    if value:
        parsed = parse_datetime(value)
        return _datetime_label(parsed) if parsed else edge
    if df.empty or "timestamp" not in df:
        return edge
    timestamp = df["timestamp"].min() if edge == "start" else df["timestamp"].max()
    if pd.isna(timestamp):
        return edge
    dt = pd.to_datetime(int(timestamp), unit="ms", utc=True).tz_convert(SH_TZ).to_pydatetime()
    return _datetime_label(dt)


def _datetime_label(dt) -> str:
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return dt.strftime("%Y%m%d")
    if dt.hour == 23 and dt.minute == 59:
        return dt.strftime("%Y%m%d")
    return dt.strftime("%Y%m%d%H%M")


def _ai_export_columns() -> list[str]:
    return [
        "schema_version",
        "symbol",
        "datetime",
        "timestamp",
        "period",
        "adjust",
        "source",
        "bar_index",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover",
        *AI_FEATURE_COLUMNS,
        *AI_TARGET_COLUMNS,
        "is_trainable",
    ]

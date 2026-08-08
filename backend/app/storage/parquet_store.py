from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from app.utils.symbols import canonical_symbol, normalize_adjust, normalize_period

logger = logging.getLogger(__name__)


class ParquetStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.parquet_dir = data_dir / "parquet"
        self.csv_dir = data_dir / "csv"
        (self.parquet_dir / "daily").mkdir(parents=True, exist_ok=True)
        (self.parquet_dir / "minute").mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

    def upsert(self, df: pd.DataFrame) -> list[Path]:
        if df.empty:
            return []
        frame = self._clean(df)
        paths: list[Path] = []
        for path, part in self._split_by_path(frame):
            existing = pd.read_parquet(path) if path.exists() else pd.DataFrame()
            merged = pd.concat([existing, part], ignore_index=True) if not existing.empty else part.copy()
            merged = self._clean(merged)
            path.parent.mkdir(parents=True, exist_ok=True)
            merged.to_parquet(path, index=False)
            paths.append(path)
            logger.info("storage action=upsert path=%s rows=%s", path, len(merged))
        return paths

    def read(
        self,
        symbol: str,
        period: str,
        adjust: str = "none",
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> pd.DataFrame:
        canonical = canonical_symbol(symbol)
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        frames: list[pd.DataFrame] = []
        if norm_period in {"1d", "1w", "1M"}:
            path = self.parquet_dir / "daily" / f"{canonical}.parquet"
            if path.exists():
                frames.append(pd.read_parquet(path))
        else:
            root = self.parquet_dir / "minute" / canonical
            if root.exists():
                for path in sorted(root.glob("*.parquet")):
                    frames.append(pd.read_parquet(path))
        if not frames:
            return pd.DataFrame()
        frame = pd.concat(frames, ignore_index=True)
        frame = frame[(frame["symbol"] == canonical) & (frame["period"] == norm_period) & (frame["adjust"] == norm_adjust)]
        if start_ms is not None:
            frame = frame[frame["timestamp"] >= start_ms]
        if end_ms is not None:
            frame = frame[frame["timestamp"] <= end_ms]
        return self._clean(frame).reset_index(drop=True)

    def export_csv(self, df: pd.DataFrame, symbol: str, period: str, adjust: str) -> Path:
        canonical = canonical_symbol(symbol)
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        path = self.csv_dir / f"{canonical}_{norm_period}_{norm_adjust}.csv"
        self._clean(df).to_csv(path, index=False)
        return path

    def export_parquet(self, df: pd.DataFrame, symbol: str, period: str, adjust: str) -> Path:
        canonical = canonical_symbol(symbol)
        norm_period = normalize_period(period)
        norm_adjust = normalize_adjust(adjust)
        path = self.parquet_dir / f"{canonical}_{norm_period}_{norm_adjust}.parquet"
        self._clean(df).to_parquet(path, index=False)
        return path

    def _split_by_path(self, df: pd.DataFrame) -> list[tuple[Path, pd.DataFrame]]:
        result: list[tuple[Path, pd.DataFrame]] = []
        for (symbol, period), part in df.groupby(["symbol", "period"], sort=False):
            if period in {"1d", "1w", "1M"}:
                result.append((self.parquet_dir / "daily" / f"{symbol}.parquet", part.copy()))
                continue
            minute_root = self.parquet_dir / "minute" / str(symbol)
            chunk = part.copy()
            dt_series = pd.to_datetime(chunk["datetime"])
            for month, month_part in chunk.groupby(dt_series.dt.strftime("%Y-%m"), sort=False):
                result.append((minute_root / f"{month}.parquet", month_part.copy()))
        return result

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df.copy()
        columns = [
            "symbol",
            "datetime",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
            "period",
            "adjust",
            "source",
        ]
        frame = df.copy()
        for column in columns:
            if column not in frame.columns:
                frame[column] = None
        frame = frame[columns]
        frame["timestamp"] = pd.to_numeric(frame["timestamp"], errors="coerce").astype("Int64")
        frame = frame.dropna(subset=["timestamp", "open", "high", "low", "close"])
        frame["timestamp"] = frame["timestamp"].astype("int64")
        for column in ["open", "high", "low", "close", "volume", "turnover"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
        frame = frame.sort_values("timestamp").drop_duplicates(["symbol", "period", "adjust", "timestamp"], keep="last")
        return frame.reset_index(drop=True)

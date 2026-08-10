from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import pandas as pd

from app.services.export_service import ExportService
from app.storage.parquet_store import ParquetStore
from app.utils.time import SH_TZ, to_timestamp_ms


def test_ai_export_frame_adds_features_targets_and_trainable_flag(tmp_path) -> None:
    store = ParquetStore(tmp_path)
    service = ExportService(None, store)  # type: ignore[arg-type]
    start = datetime(2026, 1, 1, 15, tzinfo=SH_TZ)
    rows = []
    for index in range(30):
        dt = start + timedelta(days=index)
        close = 100.0 + index
        rows.append(
            {
                "symbol": "SH.600519",
                "datetime": dt,
                "timestamp": to_timestamp_ms(dt),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000 + index * 10,
                "turnover": 100000 + index * 1000,
                "period": "1d",
                "adjust": "none",
                "source": "test",
            }
        )
    frame = pd.DataFrame(rows)

    result = service.build_ai_frame(frame)

    assert "feature_close_ma20_ratio" in result.columns
    assert "target_return_5" in result.columns
    assert "is_trainable" in result.columns
    assert result.loc[20, "target_return_1"] == pytest.approx(1 / 120)
    assert result.loc[20, "target_direction_1"] == 1
    assert result.loc[20, "is_trainable"] == 1
    assert result.loc[29, "is_trainable"] == 0
    assert result["is_trainable"].sum() > 0

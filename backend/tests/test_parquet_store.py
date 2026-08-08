from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.storage.parquet_store import ParquetStore
from app.utils.time import SH_TZ, to_timestamp_ms


def test_parquet_upsert_deduplicates(tmp_path) -> None:
    store = ParquetStore(tmp_path)
    dt = datetime(2026, 8, 7, 15, tzinfo=SH_TZ)
    frame = pd.DataFrame(
        [
            {
                "symbol": "SH.600519",
                "datetime": dt,
                "timestamp": to_timestamp_ms(dt),
                "open": 1,
                "high": 2,
                "low": 1,
                "close": 2,
                "volume": 100,
                "turnover": 200,
                "period": "1d",
                "adjust": "qfq",
                "source": "test",
            }
        ]
    )
    store.upsert(frame)
    store.upsert(frame.assign(close=3))
    result = store.read("SH.600519", "1d", "qfq")
    assert len(result) == 1
    assert result.iloc[0]["close"] == 3

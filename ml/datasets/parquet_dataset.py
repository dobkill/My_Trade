from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    import torch
    from torch.utils.data import Dataset
except ModuleNotFoundError:  # pragma: no cover - exercised when optional torch is absent
    torch = None

    class Dataset:  # type: ignore[no-redef]
        pass


class StockSequenceDataset(Dataset):
    def __init__(self, path: str | Path, sequence_length: int = 60):
        if torch is None:
            raise RuntimeError("PyTorch is not installed. Install torch in the Trade environment to use ml/ examples.")
        self.path = Path(path)
        self.sequence_length = sequence_length
        frame = pd.read_parquet(self.path).sort_values("timestamp")
        required = ["open", "high", "low", "close", "volume"]
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"missing columns in parquet: {missing}")
        values = frame[required].astype("float32").to_numpy()
        if len(values) <= sequence_length:
            raise ValueError("not enough rows for requested sequence_length")
        self.features = values
        closes = frame["close"].astype("float32").to_numpy()
        self.returns = (closes[1:] - closes[:-1]) / np.maximum(closes[:-1], 1e-6)

    def __len__(self) -> int:
        return len(self.features) - self.sequence_length

    def __getitem__(self, index: int):
        x = self.features[index : index + self.sequence_length]
        y = self.returns[index + self.sequence_length - 1]
        return torch.from_numpy(x), torch.tensor(y, dtype=torch.float32)

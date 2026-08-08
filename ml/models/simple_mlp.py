from __future__ import annotations

try:
    import torch
    from torch import nn
except ModuleNotFoundError:  # pragma: no cover
    torch = None
    nn = None


class SimpleMLP(nn.Module if nn is not None else object):
    def __init__(self, sequence_length: int = 60, feature_count: int = 5):
        if nn is None:
            raise RuntimeError("PyTorch is not installed. Install torch in the Trade environment to use ml/ examples.")
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(sequence_length * feature_count, 128),
            nn.ReLU(),
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)

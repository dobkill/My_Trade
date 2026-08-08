from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    try:
        import torch
        from torch.utils.data import DataLoader
    except ModuleNotFoundError:
        print("PyTorch is not installed in the current Trade environment. Install torch to run this optional ML example.")
        return 0

    from datasets.parquet_dataset import StockSequenceDataset
    from models.simple_mlp import SimpleMLP

    parser = argparse.ArgumentParser(description="Train a tiny MLP on exported A-share parquet bars.")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--sequence-length", type=int, default=60)
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()

    dataset = StockSequenceDataset(args.data, sequence_length=args.sequence_length)
    loader = DataLoader(dataset, batch_size=64, shuffle=True)
    model = SimpleMLP(sequence_length=args.sequence_length)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.MSELoss()

    for epoch in range(args.epochs):
        total = 0.0
        for x, y in loader:
            pred = model(x)
            loss = loss_fn(pred, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss.detach())
        print(f"epoch={epoch + 1} loss={total / max(len(loader), 1):.8f}")
    print(f"dataset_rows={len(dataset)} input={args.data}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

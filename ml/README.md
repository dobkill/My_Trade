# ML 示例

`ml/` 与 FastAPI 和 GUI 完全解耦，只验证 Parquet 数据可以进入 PyTorch pipeline。

当前环境如果没有 PyTorch，不会影响行情终端启动。需要训练示例时，在确认 CUDA/CPU 版本后自行安装：

```bash
conda activate Trade
python -m pip install torch
```

运行：

```bash
python ml/train_example.py --data data/parquet/daily/SH.600519.parquet
```

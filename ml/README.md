# ML 示例

`ml/` 与 FastAPI 和 GUI 完全解耦，只验证 Parquet 数据可以进入 PyTorch pipeline。

GUI 里的 `AI CSV` 导出会生成面向训练/推理的表格字段，包括 `feature_*`、`target_*`、`schema_version` 和 `is_trainable`。训练时通常筛选 `is_trainable=1`；最新几行没有未来标签时会保留为 `is_trainable=0`，方便直接作为推理输入。

当前环境如果没有 PyTorch，不会影响行情终端启动。需要训练示例时，在确认 CUDA/CPU 版本后自行安装：

```bash
conda activate Trade
python -m pip install torch
```

运行：

```bash
python ml/train_example.py --data data/parquet/daily/SH.600519.parquet
```

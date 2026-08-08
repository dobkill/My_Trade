# Backend

FastAPI backend for the A-Trade A-share market research terminal.

Run from the repository root:

```bash
conda activate Trade
./scripts/start_backend.sh
```

Key endpoints:

- `GET /api/health`
- `GET /api/symbols/search?q=600519`
- `GET /api/stocks/SH.600519/quote`
- `GET /api/stocks/SH.600519/klines?period=1d&adjust=qfq`
- `GET /api/stocks/SH.600519/export?period=1d&adjust=qfq&format=csv`
- `WS /ws/stocks/SH.600519`

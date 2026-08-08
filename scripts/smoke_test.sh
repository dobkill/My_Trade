#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate Trade

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
LOG_FILE="/tmp/opencode/a_trade_smoke_backend.log"

BACKEND_PID=""
cleanup() {
  if [[ -n "$BACKEND_PID" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT

if ! python - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).read()
PY
then
  pkill -f "uvicorn app.main:app --host 127.0.0.1 --port 8000" 2>/dev/null || true
  sleep 1
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$LOG_FILE" 2>&1 &
  BACKEND_PID=$!
fi

python - <<'PY'
import asyncio
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd
import websockets

BASE = 'http://127.0.0.1:8000'


def wait_health() -> None:
    last = None
    for _ in range(40):
        try:
            payload = get_json('/api/health')
            print('health', payload['status'], payload.get('active_provider'))
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.5)
    raise RuntimeError(f'backend did not become healthy: {last}')


def get_json(path: str):
    with urllib.request.urlopen(BASE + path, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def download(path: str) -> bytes:
    with urllib.request.urlopen(BASE + path, timeout=90) as response:
        return response.read()


async def check_ws() -> None:
    async with websockets.connect('ws://127.0.0.1:8000/ws/stocks/SH.600519', open_timeout=10) as ws:
        message = await asyncio.wait_for(ws.recv(), timeout=35)
        payload = json.loads(message)
        assert payload['type'] in {'status', 'quote', 'bar', 'heartbeat'}
        print('websocket', payload['type'])


wait_health()

search = get_json('/api/symbols/search?q=600519')
assert any(item['symbol'] == 'SH.600519' for item in search['data']), search
print('search 600519 ok')

for symbol in ['SH.600519', 'SZ.000001']:
    data = get_json(f'/api/stocks/{symbol}/klines?period=1d&adjust=qfq')
    assert data['data'], data
    assert {'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'} <= set(data['data'][0])
    print('klines', symbol, len(data['data']))

csv_bytes = download('/api/stocks/SH.600519/export?period=1d&adjust=qfq&format=csv')
assert b'timestamp' in csv_bytes and b'close' in csv_bytes
print('export csv bytes', len(csv_bytes))

parquet_bytes = download('/api/stocks/SH.600519/export?period=1d&adjust=qfq&format=parquet')
assert parquet_bytes[:4] == b'PAR1'
print('export parquet bytes', len(parquet_bytes))

parquet_path = Path('data/parquet/SH.600519_1d_qfq.parquet')
assert parquet_path.exists(), parquet_path
frame = pd.read_parquet(parquet_path)
assert not frame.empty and {'open', 'high', 'low', 'close', 'volume'} <= set(frame.columns)
print('read parquet rows', len(frame))

asyncio.run(check_ws())
print('smoke test passed')
PY

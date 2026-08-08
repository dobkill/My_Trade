#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate Trade

echo "Python: $(which python)"
python --version
python -m pip --version

python -m pip install -r backend/requirements.txt

python - <<'PY'
try:
    import eltdx
    from eltdx import TdxClient

    print(f"eltdx import ok: {eltdx.__file__}")
    with TdxClient(timeout=4, pool_size=1, probe_hosts=True, probe_timeout=1.0, heartbeat_interval=None) as client:
        quote = client.get_quote(['sh600519', 'sz000001'])[0]
        print(f"tdx quote ok: {quote.full_code} price={quote.last_price}")
except Exception as exc:
    print(f"tdx unavailable, backend will fall back to AKShare where possible: {exc}")
PY

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  node --version
  npm --version
else
  echo "Node.js/npm not found. Install Node LTS in user space, then rerun bootstrap." >&2
  exit 1
fi

npm --prefix frontend install

python - <<'PY'
try:
    import torch
    print(f"torch={torch.__version__} cuda={torch.cuda.is_available()}")
except ModuleNotFoundError:
    print("torch not installed; ML example remains optional")
PY

echo "Bootstrap complete."

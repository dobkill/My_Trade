#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT="${APP_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-8}"

declare -a PIDS=()

add_pid() {
  local pid="$1"

  [[ "$pid" =~ ^[0-9]+$ ]] || return 0
  [[ "$pid" == "$$" ]] && return 0

  for existing in "${PIDS[@]}"; do
    [[ "$existing" == "$pid" ]] && return 0
  done

  PIDS+=("$pid")
}

add_port_pids() {
  local label="$1"
  local port="$2"
  local pids=()

  if command -v lsof >/dev/null 2>&1; then
    mapfile -t pids < <(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  elif command -v ss >/dev/null 2>&1; then
    mapfile -t pids < <(ss -ltnp "sport = :$port" 2>/dev/null | sed -nE 's/.*pid=([0-9]+).*/\1/p' | sort -u)
  fi

  if ((${#pids[@]} == 0)); then
    echo "$label: no listener on port $port"
    return 0
  fi

  echo "$label: found listener on port $port"
  for pid in "${pids[@]}"; do
    add_pid "$pid"
  done
}

add_pattern_pids() {
  local label="$1"
  local pattern="$2"
  local pids=()

  command -v pgrep >/dev/null 2>&1 || return 0
  mapfile -t pids < <(pgrep -f "$pattern" 2>/dev/null || true)

  if ((${#pids[@]} == 0)); then
    return 0
  fi

  echo "$label: found matching process"
  for pid in "${pids[@]}"; do
    add_pid "$pid"
  done
}

is_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

describe_pid() {
  local pid="$1"
  ps -p "$pid" -o pid=,comm=,args= 2>/dev/null | sed 's/^[[:space:]]*//'
}

add_port_pids "Backend" "$BACKEND_PORT"
add_port_pids "Frontend" "$FRONTEND_PORT"
add_pattern_pids "Dev launcher" "scripts/dev\\.sh"
add_pattern_pids "Backend command" "uvicorn app\\.main:app .*--port ${BACKEND_PORT}"

if ((${#PIDS[@]} == 0)); then
  echo "No frontend/backend dev processes found."
  exit 0
fi

echo
echo "Stopping ${#PIDS[@]} process(es):"
for pid in "${PIDS[@]}"; do
  describe_pid "$pid" || true
done

for pid in "${PIDS[@]}"; do
  kill -TERM "$pid" 2>/dev/null || true
done

deadline=$((SECONDS + STOP_TIMEOUT_SECONDS))
while ((SECONDS < deadline)); do
  still_running=0
  for pid in "${PIDS[@]}"; do
    if is_running "$pid"; then
      still_running=1
      break
    fi
  done

  ((still_running == 0)) && break
  sleep 1
done

declare -a REMAINING=()
for pid in "${PIDS[@]}"; do
  if is_running "$pid"; then
    REMAINING+=("$pid")
  fi
done

if ((${#REMAINING[@]} > 0)); then
  echo
  echo "Force stopping ${#REMAINING[@]} process(es):"
  for pid in "${REMAINING[@]}"; do
    describe_pid "$pid" || true
    kill -KILL "$pid" 2>/dev/null || true
  done
fi

echo
echo "Frontend/backend dev processes stopped."

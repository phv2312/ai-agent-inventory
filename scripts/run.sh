#!/usr/bin/env bash

set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
requested_api_port="${AGENT_API_PORT-}"
requested_frontend_port="${FRONTEND_PORT-}"
requested_data_dir="${AGENT_API_DATA_DIR-}"
requested_sdk_tracing="${OPENAI_AGENTS_DISABLE_TRACING-}"
requested_phoenix_tracing="${PHOENIX_TRACING_ENABLED-}"
api_only=false

if [[ "${1:-}" == "--api-only" ]]; then
  api_only=true
fi

if [[ -f "$root_dir/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$root_dir/.env"
  set +a
fi

[[ -n "$requested_api_port" ]] && export AGENT_API_PORT="$requested_api_port"
[[ -n "$requested_frontend_port" ]] && export FRONTEND_PORT="$requested_frontend_port"
[[ -n "$requested_data_dir" ]] && export AGENT_API_DATA_DIR="$requested_data_dir"
[[ -n "$requested_sdk_tracing" ]] && export OPENAI_AGENTS_DISABLE_TRACING="$requested_sdk_tracing"
[[ -n "$requested_phoenix_tracing" ]] && export PHOENIX_TRACING_ENABLED="$requested_phoenix_tracing"

api_port="${AGENT_API_PORT:-8080}"
frontend_port="${FRONTEND_PORT:-5173}"

api_pid=""
frontend_pid=""

cleanup() {
  [[ -n "$api_pid" ]] && kill "$api_pid" 2>/dev/null || true
  [[ -n "$frontend_pid" ]] && kill "$frontend_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

cd "$root_dir"
uv run uvicorn agent.backend.api.main:app --host 127.0.0.1 --port "$api_port" &
api_pid="$!"

if [[ "$api_only" == true ]]; then
  wait "$api_pid"
  exit 0
fi

(
  cd frontend
  VITE_API_PROXY_TARGET="http://127.0.0.1:$api_port" \
    npm run dev -- --host 127.0.0.1 --port "$frontend_port"
) &
frontend_pid="$!"

wait "$api_pid" "$frontend_pid"

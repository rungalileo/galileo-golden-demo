#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

brew_shellenv
configure_docker_host

[ "${1:-}" = "--no-fix" ] && shift
[ "$#" -eq 0 ] || die "Usage: $0 [--no-fix]"

RUNTIME_ROOT="$HOME/Library/Application Support/GalileoGoldenDemo"
STACK_ENV="$RUNTIME_ROOT/stack.env"
[ -f "$STACK_ENV" ] || die "Stack configuration is missing. Run install.sh first."
# shellcheck disable=SC1090
. "$STACK_ENV"

FAILURES=0

check() {
  local description="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf '\033[1;32mPASS\033[0m  %s\n' "$description"
  else
    printf '\033[1;31mFAIL\033[0m  %s\n' "$description"
    FAILURES=$((FAILURES + 1))
  fi
}

check_http() {
  curl --silent --show-error --fail --max-time 5 "$1"
}

check_mode_600() {
  local mode
  mode="$(stat -f '%Lp' "$1" 2>/dev/null || true)"
  [ "$mode" = "600" ]
}

check_cloud_secrets() {
  "$REPO_DIR/.venv/bin/python" - "$REPO_DIR/.streamlit/secrets.toml" <<'PY'
import sys
import toml

secrets = toml.load(sys.argv[1])
required = ("galileo_api_key", "galileo_console_url", "openai_api_key")
raise SystemExit(0 if all(str(secrets.get(key, "")).strip() for key in required) else 1)
PY
}

check_pgvector() {
  docker exec golden-demo-postgres psql -U postgres -d vectordb -Atc \
    "SELECT 1 FROM pg_extension WHERE extname='vector'" | grep -q '^1$'
}

printf 'Galileo Golden Demo health report\n\n'
check "App virtualenv" test -x "$REPO_DIR/.venv/bin/python"
check "Private Streamlit secrets (0600)" check_mode_600 "$REPO_DIR/.streamlit/secrets.toml"
check "Private dotenv secrets (0600)" check_mode_600 "$REPO_DIR/.env"
check "Private runtime database env (0600)" check_mode_600 "$RUNTIME_ROOT/postgres.env"
check "Python dependencies" env UV_CACHE_DIR="$RUNTIME_ROOT/uv-cache" \
  uv pip check --python "$REPO_DIR/.venv/bin/python"
check "Docker runtime" docker info
check "PostgreSQL container" docker_container_running golden-demo-postgres
check "pgvector extension" check_pgvector
if [ "${LOCAL_ONLY:-0}" != "1" ]; then
  check "Galileo and OpenAI credentials configured" check_cloud_secrets
fi
check "Galileo app HTTP health" check_http "http://127.0.0.1:$APP_PORT/_stcore/health"

if [ "$SKIP_OPEN_WEBUI" != "1" ]; then
  check "Open WebUI container" docker_container_running galileo-open-webui
  check "Open WebUI HTTP health" check_http "http://127.0.0.1:$OPEN_WEBUI_PORT/health"
fi

if [ "$OPENAI_ONLY" != "1" ]; then
  check "MLX-LM HTTP health" check_http "http://127.0.0.1:$MLX_PORT/v1/models"
fi

printf '\n'
if [ "$FAILURES" -gt 0 ]; then
  die "$FAILURES health check(s) failed. See $HOME/Library/Logs/GalileoGoldenDemo for service logs."
fi
success "All health checks passed"

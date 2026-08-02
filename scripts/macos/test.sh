#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0
FAIL=0
SKIP=0

passed() {
  PASS=$((PASS + 1))
  printf 'PASS  %s\n' "$1"
}

failed() {
  FAIL=$((FAIL + 1))
  printf 'FAIL  %s\n' "$1" >&2
}

skipped() {
  SKIP=$((SKIP + 1))
  printf 'SKIP  %s\n' "$1"
}

run_test() {
  local name="$1"
  shift
  if "$@"; then
    passed "$name"
  else
    failed "$name"
  fi
}

test_syntax() {
  local script
  while IFS= read -r script; do
    bash -n "$script" || return 1
  done < <(find "$SCRIPT_DIR" -type f -name '*.sh' -print)
}

test_model_policy() {
  (
    # shellcheck source=lib/common.sh
    . "$SCRIPT_DIR/lib/common.sh"
    [ "$(model_for_hardware 16 balanced)" = "mlx-community/gemma-4-e4b-it-4bit" ]
    [ "$(model_for_hardware 24 balanced)" = "mlx-community/gemma-4-26b-a4b-it-4bit" ]
    [ "$(model_for_hardware 64 balanced)" = "mlx-community/gemma-4-26b-a4b-it-4bit" ]
    [ "$(model_for_hardware 64 quality)" = "mlx-community/gemma-4-31b-it-4bit" ]
  )
}

test_colima_socket_fallback() {
  grep -q 'configure_docker_host' "$SCRIPT_DIR/install.sh"
  grep -q 'configure_docker_host' "$SCRIPT_DIR/run.sh"
  grep -q 'configure_docker_host' "$SCRIPT_DIR/doctor.sh"
}

test_required_domains() {
  grep -q 'INDEX_DOMAINS="bank healthcare insurance restaurant"' "$SCRIPT_DIR/install.sh"
  # shellcheck disable=SC2016
  grep -q 'setup_vectordb.py "$index_domain"' "$SCRIPT_DIR/install.sh"
}

test_locked_requirements() {
  [ -s "$SCRIPT_DIR/../../requirements-macos.lock" ]
  grep -q 'APP_REQUIREMENTS=.*requirements-macos.lock' "$SCRIPT_DIR/install.sh"
}

test_secret_renderer() {
  local temp_dir="$1"
  local sentinel="$temp_dir/should-not-exist"
  local input="$temp_dir/input.env"
  # shellcheck disable=SC2016
  printf '%s\n' \
    'OPENAI_API_KEY=$(touch /tmp/galileo-renderer-must-not-execute)' \
    'GALILEO_API_KEY=galileo-test' \
    'GALILEO_CONSOLE_URL=https://console.demo-v2.galileocloud.io/' \
    'POSTGRES_PASSWORD=' > "$input"

  python3 "$SCRIPT_DIR/render_secrets.py" \
    --input "$input" \
    --toml-output "$temp_dir/secrets.toml" \
    --dotenv-output "$temp_dir/.env" \
    --runtime-env-output "$temp_dir/postgres.env" \
    --webui-env-output "$temp_dir/webui.env" \
    --mlx-model mlx-community/gemma-4-e4b-it-4bit \
    --mlx-port 8088 \
    --postgres-port 5440 >/dev/null

  [ ! -e "$sentinel" ]
  [ ! -e /tmp/galileo-renderer-must-not-execute ]
  [ "$(stat -f '%Lp' "$temp_dir/secrets.toml")" = "600" ]
  [ "$(stat -f '%Lp' "$temp_dir/.env")" = "600" ]
  grep -q 'mlx_base_url = "http://127.0.0.1:8088/v1"' "$temp_dir/secrets.toml"
  grep -q 'POSTGRES_PORT=5440' "$temp_dir/.env"
  grep -q 'host.docker.internal:8088/v1' "$temp_dir/webui.env"
  if grep -q "OPENAI_API_BASE_URLS='" "$temp_dir/webui.env"; then
    return 1
  fi
  grep -Eq '^POSTGRES_PASSWORD=.{20,}$' "$temp_dir/postgres.env"
}

test_secret_allowlist() {
  local temp_dir="$1"
  printf 'NOT_A_SUPPORTED_KEY=value\n' > "$temp_dir/bad.env"
  ! python3 "$SCRIPT_DIR/render_secrets.py" \
    --input "$temp_dir/bad.env" \
    --toml-output "$temp_dir/bad.toml" \
    --dotenv-output "$temp_dir/bad-output.env" \
    --runtime-env-output "$temp_dir/bad-runtime.env" \
    --webui-env-output "$temp_dir/bad-webui.env" \
    --mlx-model test/model \
    --mlx-port 8080 \
    --postgres-port 5432 >/dev/null 2>&1
}

test_secret_exporter() {
  local temp_dir="$1"
  printf '%s\n' \
    'galileo_api_key = "galileo-test"' \
    'galileo_console_url = "https://console.demo-v2.galileocloud.io/"' \
    'openai_api_key = "openai-test"' \
    'postgres_password = "postgres-test"' > "$temp_dir/source.toml"
  python3 "$SCRIPT_DIR/export_secrets.py" \
    --input "$temp_dir/source.toml" --output "$temp_dir/exported.env" >/dev/null
  [ "$(stat -f '%Lp' "$temp_dir/exported.env")" = "600" ]
  grep -q '^OPENAI_API_KEY=openai-test$' "$temp_dir/exported.env"
  grep -q '^GALILEO_API_KEY=galileo-test$' "$temp_dir/exported.env"
  grep -Eq '^OPEN_WEBUI_SECRET_KEY=.{32,}$' "$temp_dir/exported.env"
}

test_canonical_op_item_resolver() {
  local temp_dir="$1"
  python3 - "$temp_dir/op-item.json" <<'PY'
import json
import sys

values = {
    "CONFIG_SCHEMA_VERSION": "1",
    "CONFIG_ENVIRONMENT": "test",
    "OPENAI_API_KEY": "openai-test",
    "OPENAI_DEFAULT_CHAT_MODEL": "gpt-test",
    "OPENAI_EMBEDDING_MODEL": "embedding-test",
    "OPENAI_EMBEDDING_DIMENSIONS": "768",
    "GALILEO_API_KEY": "galileo-test",
    "GALILEO_CONSOLE_URL": "https://console.example.test/",
    "GALILEO_API_URL": "https://api.example.test/",
    "GALILEO_DOMAIN": "healthcare",
    "GALILEO_PROJECT": "test-project",
    "GALILEO_PROJECT_ID": "project-id",
    "GALILEO_PROJECT_URL": "https://console.example.test/project/project-id",
    "GALILEO_LOG_STREAM": "healthcare",
    "GALILEO_LOG_STREAM_ID": "stream-id",
    "GALILEO_LOG_STREAM_URL": "https://console.example.test/project/project-id/log-streams/stream-id",
    "AGENT_CONTROL_URL": "https://agent.example.test/",
    "AGENT_CONTROL_AGENT_NAME": "test-agent",
    "AGENT_CONTROL_RUNTIME_AUTH_MODE": "jwt",
    "AGENT_CONTROL_API_KEY_HEADER": "Galileo-API-Key",
    "AGENT_CONTROL_TARGET_TYPE": "log_stream",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres-test",
    "POSTGRES_DB": "vectordb",
    "OPEN_WEBUI_SECRET_KEY": "webui-secret-test",
}
item = {
    "title": "Test canonical item",
    "fields": [
        {"id": key.lower(), "label": key, "type": "CONCEALED", "value": value}
        for key, value in values.items()
    ],
}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(item, handle)
PY
  python3 "$SCRIPT_DIR/resolve_op_item.py" --output "$temp_dir/op.env" \
    < "$temp_dir/op-item.json" >/dev/null
  [ "$(stat -f '%Lp' "$temp_dir/op.env")" = "600" ]
  grep -q '^GALILEO_PROJECT_ID=project-id$' "$temp_dir/op.env"
  grep -q '^OPENAI_API_KEY=openai-test$' "$temp_dir/op.env"
  printf 'POSTGRES_USER=postgres\nPOSTGRES_PASSWORD=old-password\nPOSTGRES_DB=vectordb\n' \
    > "$temp_dir/previous.env"
  if python3 "$SCRIPT_DIR/resolve_op_item.py" --output "$temp_dir/rejected.env" \
    --previous-dotenv "$temp_dir/previous.env" < "$temp_dir/op-item.json" >/dev/null 2>&1; then
    return 1
  fi
  [ ! -e "$temp_dir/rejected.env" ]
}

test_op_refresh_wiring() {
  grep -q -- '--op-item' "$SCRIPT_DIR/install.sh"
  grep -q -- '--refresh-config' "$SCRIPT_DIR/install.sh"
  grep -q -- '--team-config' "$SCRIPT_DIR/install.sh"
  grep -q 'op signin --account' "$SCRIPT_DIR/install.sh"
  grep -q 'REFRESH_CONFIG.*RECREATE_SERVICES' "$SCRIPT_DIR/install.sh" || \
    grep -q 'RECREATE_SERVICES.*REFRESH_CONFIG' "$SCRIPT_DIR/install.sh"
  if sed -n '/ensure_postgres()/,/ensure_open_webui()/p' "$SCRIPT_DIR/install.sh" | \
      grep -q 'REFRESH_CONFIG'; then
    return 1
  fi
  sed -n '/ensure_open_webui()/,/write_stack_env()/p' "$SCRIPT_DIR/install.sh" | \
    grep -q 'REFRESH_CONFIG'
  "$SCRIPT_DIR/refresh-config.sh" --help >/dev/null
}

test_service_readiness_wiring() {
  grep -q 'restart_launch_agent' "$SCRIPT_DIR/install.sh"
  grep -q 'attempt.*-lt 10' "$SCRIPT_DIR/install.sh"
  grep -q 'wait_for_http.*APP_PORT.*/_stcore/health' "$SCRIPT_DIR/install.sh"
  grep -q 'wait_for_http.*OPEN_WEBUI_PORT.*/health' "$SCRIPT_DIR/install.sh"
  grep -q 'wait_for_http.*MLX_PORT.*/v1/models' "$SCRIPT_DIR/install.sh"
}

test_dry_run() {
  local temp_dir="$1"
  printf '%s\n' \
    'OPENAI_API_KEY=test-openai' \
    'GALILEO_API_KEY=test-galileo' \
    'GALILEO_CONSOLE_URL=https://console.demo-v2.galileocloud.io/' > "$temp_dir/dry.env"
  "$SCRIPT_DIR/install.sh" \
    --dry-run \
    --no-start \
    --skip-indexes \
    --config-file "$temp_dir/dry.env" >/dev/null
}

test_age_roundtrip() {
  local temp_dir="$1"
  command -v age >/dev/null 2>&1 || return 77
  command -v age-keygen >/dev/null 2>&1 || return 77
  printf 'OPENAI_API_KEY=roundtrip-test\n' > "$temp_dir/plain.env"
  age-keygen -o "$temp_dir/key.txt" >/dev/null 2>&1
  local recipient
  recipient="$(age-keygen -y "$temp_dir/key.txt")"
  "$SCRIPT_DIR/encrypt-secrets.sh" \
    --input "$temp_dir/plain.env" \
    --output "$temp_dir/plain.env.age" \
    --recipient "$recipient" >/dev/null
  "$SCRIPT_DIR/decrypt-secrets.sh" \
    --input "$temp_dir/plain.env.age" \
    --output "$temp_dir/decrypted.env" \
    --identity "$temp_dir/key.txt" >/dev/null
  cmp -s "$temp_dir/plain.env" "$temp_dir/decrypted.env"
}

TEMP_DIR="$(mktemp -d -t galileo-macos-tests.XXXXXX)"
trap 'rm -rf "$TEMP_DIR"; rm -f /tmp/galileo-renderer-must-not-execute' EXIT

run_test "shell syntax" test_syntax
run_test "hardware model policy" test_model_policy
run_test "Colima Docker socket fallback is wired" test_colima_socket_fallback
run_test "all four demo domains are indexed" test_required_domains
run_test "tested macOS dependency lock is used" test_locked_requirements
run_test "safe secret rendering and file modes" test_secret_renderer "$TEMP_DIR"
run_test "secret key allow-list rejection" test_secret_allowlist "$TEMP_DIR"
run_test "private TOML transfer exporter" test_secret_exporter "$TEMP_DIR"
run_test "canonical 1Password item resolver" test_canonical_op_item_resolver "$TEMP_DIR"
run_test "forced 1Password refresh wiring" test_op_refresh_wiring
run_test "managed HTTP readiness waits" test_service_readiness_wiring
run_test "complete installer dry-run" test_dry_run "$TEMP_DIR"

set +e
test_age_roundtrip "$TEMP_DIR"
AGE_STATUS=$?
set -e
if [ "$AGE_STATUS" -eq 0 ]; then
  passed "age encrypted-file round trip"
elif [ "$AGE_STATUS" -eq 77 ]; then
  skipped "age encrypted-file round trip (age not installed)"
else
  failed "age encrypted-file round trip"
fi

if command -v shellcheck >/dev/null 2>&1; then
  if shellcheck -x -P "$SCRIPT_DIR" "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR/lib"/*.sh; then
    passed "ShellCheck"
  else
    failed "ShellCheck"
  fi
else
  skipped "ShellCheck (not installed)"
fi

printf '\nResult: %s passed, %s failed, %s skipped\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ]

#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"
# shellcheck source=versions.env
. "$SCRIPT_DIR/versions.env"

CONFIG_FILE=""
OP_TEMPLATE=""
OP_ITEM=""
OP_VAULT=""
OP_ACCOUNT=""
REFRESH_CONFIG=0
TEAM_CONFIG=0
WITH_GITHUB_LOGIN=0
WITH_1PASSWORD=0
OPENAI_ONLY=0
LOCAL_ONLY=0
SKIP_OPEN_WEBUI=0
SKIP_INDEXES=0
INDEX_DOMAINS="bank healthcare insurance restaurant"
NO_START=0
RECREATE_SERVICES=0
DRY_RUN=0
MODEL_OVERRIDE="auto"
MODEL_PROFILE="balanced"
POSTGRES_PORT="auto"
OPEN_WEBUI_PORT="auto"
APP_PORT="auto"
MLX_PORT="auto"
TEMP_FILES=""

usage() {
  cat <<'USAGE'
Usage: scripts/macos/install.sh [options]

Install and configure the complete Galileo Golden Demo stack on macOS.

Secrets (choose one for the complete cloud-connected setup):
  --config-file PATH       Read secrets from a local dotenv file.
  --op-template PATH       Resolve op:// references with 1Password Desktop/CLI.
  --op-item ITEM           Resolve the canonical deployment item by name, ID, or URL.
  --op-vault VAULT         Optional vault name/ID for --op-item.
  --op-account ACCOUNT     Optional 1Password account shorthand/domain.
  --team-config            Use this repo's canonical Cisco 1Password item.
  --refresh-config         Pull --op-item again and replace generated local config.
  --force-config           Alias for --refresh-config.
  --with-1password         Install 1Password Desktop and CLI, then authorize CLI.
  --local-only             Allow installation without OpenAI and Galileo secrets.

Optional integrations:
  --github-login           Opt in to interactive `gh auth login --web`.

Model and service options:
  --model MODEL_ID         Override automatic MLX model selection.
  --model-profile NAME     balanced (default) or quality.
  --openai-only            Skip MLX (required for Intel Macs).
  --postgres-port PORT     Default: first free port from 5432.
  --mlx-port PORT          Default: first free port from 8080.
  --open-webui-port PORT   Default: first free port from 3000.
  --app-port PORT          Default: first free port from 8501.
  --skip-open-webui        Do not install the Open WebUI container.
  --skip-indexes           Do not build pgvector indexes.
  --domains "NAMES"        Space/comma-separated domains to index (default: all four demo domains).
  --no-start               Install/configure without launching the stack.
  --recreate-services      Recreate only this app's existing Docker containers.
  --dry-run                Print mutating commands without running them.
  -h, --help               Show this help.

The script is safe to rerun. It never removes an existing container unless
--recreate-services is explicitly supplied.
USAGE
}

cleanup() {
  local item
  for item in $TEMP_FILES; do
    [ ! -e "$item" ] || rm -f "$item"
  done
}
trap cleanup EXIT
trap 'die "Installation stopped at line $LINENO. Fix the reported error and rerun the same command."' ERR

while [ "$#" -gt 0 ]; do
  case "$1" in
    --config-file) [ "$#" -ge 2 ] || die "--config-file needs a path"; CONFIG_FILE="$2"; shift 2 ;;
    --op-template) [ "$#" -ge 2 ] || die "--op-template needs a path"; OP_TEMPLATE="$2"; WITH_1PASSWORD=1; shift 2 ;;
    --op-item) [ "$#" -ge 2 ] || die "--op-item needs a name, ID, or URL"; OP_ITEM="$2"; WITH_1PASSWORD=1; shift 2 ;;
    --op-vault) [ "$#" -ge 2 ] || die "--op-vault needs a value"; OP_VAULT="$2"; shift 2 ;;
    --op-account) [ "$#" -ge 2 ] || die "--op-account needs a value"; OP_ACCOUNT="$2"; shift 2 ;;
    --team-config) TEAM_CONFIG=1; WITH_1PASSWORD=1; shift ;;
    --refresh-config|--force-config) REFRESH_CONFIG=1; shift ;;
    --with-1password) WITH_1PASSWORD=1; shift ;;
    --github-login) WITH_GITHUB_LOGIN=1; shift ;;
    --openai-only) OPENAI_ONLY=1; shift ;;
    --local-only) LOCAL_ONLY=1; shift ;;
    --model) [ "$#" -ge 2 ] || die "--model needs a model ID"; MODEL_OVERRIDE="$2"; shift 2 ;;
    --model-profile) [ "$#" -ge 2 ] || die "--model-profile needs balanced or quality"; MODEL_PROFILE="$2"; shift 2 ;;
    --postgres-port) [ "$#" -ge 2 ] || die "--postgres-port needs a value"; POSTGRES_PORT="$2"; shift 2 ;;
    --mlx-port) [ "$#" -ge 2 ] || die "--mlx-port needs a value"; MLX_PORT="$2"; shift 2 ;;
    --open-webui-port) [ "$#" -ge 2 ] || die "--open-webui-port needs a value"; OPEN_WEBUI_PORT="$2"; shift 2 ;;
    --app-port) [ "$#" -ge 2 ] || die "--app-port needs a value"; APP_PORT="$2"; shift 2 ;;
    --skip-open-webui) SKIP_OPEN_WEBUI=1; shift ;;
    --skip-indexes) SKIP_INDEXES=1; shift ;;
    --domains) [ "$#" -ge 2 ] || die "--domains needs a value"; INDEX_DOMAINS="$(printf '%s' "$2" | tr ',' ' ')"; shift 2 ;;
    --no-start) NO_START=1; shift ;;
    --recreate-services) RECREATE_SERVICES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (use --help)" ;;
  esac
done

if [ "$TEAM_CONFIG" = "1" ]; then
  [ -n "$OP_ITEM" ] || OP_ITEM="$TEAM_OP_ITEM"
  [ -n "$OP_VAULT" ] || OP_VAULT="$TEAM_OP_VAULT"
  [ -n "$OP_ACCOUNT" ] || OP_ACCOUNT="$TEAM_OP_ACCOUNT"
fi

SECRET_SOURCE_COUNT=0
[ -z "$CONFIG_FILE" ] || SECRET_SOURCE_COUNT=$((SECRET_SOURCE_COUNT + 1))
[ -z "$OP_TEMPLATE" ] || SECRET_SOURCE_COUNT=$((SECRET_SOURCE_COUNT + 1))
[ -z "$OP_ITEM" ] || SECRET_SOURCE_COUNT=$((SECRET_SOURCE_COUNT + 1))
[ "$SECRET_SOURCE_COUNT" -le 1 ] || die "Use only one of --config-file, --op-template, or --op-item."
[ "$REFRESH_CONFIG" != "1" ] || [ -n "$OP_ITEM" ] || die "--refresh-config requires --op-item."
[ "$MODEL_PROFILE" = "balanced" ] || [ "$MODEL_PROFILE" = "quality" ] || die "--model-profile must be balanced or quality."
for index_domain in $INDEX_DOMAINS; do
  case "$index_domain" in
    ''|*[!A-Za-z0-9_-]*) die "Invalid domain name: $index_domain" ;;
  esac
done

require_macos
ARCH="$(machine_arch)"
MEMORY_GIB="$(memory_gib)"
CPU_COUNT="$(sysctl -n hw.logicalcpu 2>/dev/null || printf '4')"

if [ "$OPENAI_ONLY" != "1" ] && [ "$ARCH" != "arm64" ]; then
  die "MLX requires Apple Silicon. Rerun with --openai-only on this $ARCH Mac."
fi

if [ "$MODEL_OVERRIDE" = "auto" ]; then
  MLX_MODEL="$(model_for_hardware "$MEMORY_GIB" "$MODEL_PROFILE")"
else
  MLX_MODEL="$MODEL_OVERRIDE"
fi

if [ "$OPENAI_ONLY" != "1" ]; then
  REQUIRED_DISK_GIB="$(minimum_disk_gib_for_model "$MLX_MODEL")"
  AVAILABLE_DISK_GIB="$(free_disk_gib "$REPO_DIR")"
  [ "$AVAILABLE_DISK_GIB" -ge "$REQUIRED_DISK_GIB" ] || die \
    "$MLX_MODEL needs at least ${REQUIRED_DISK_GIB} GiB free; only ${AVAILABLE_DISK_GIB} GiB is available."
fi

log "Preflight: macOS $ARCH, ${MEMORY_GIB} GiB RAM, ${CPU_COUNT} logical CPUs"
if [ "$OPENAI_ONLY" = "1" ]; then
  log "Inference: OpenAI only (MLX disabled)"
else
  log "Inference: $MLX_MODEL ($MODEL_PROFILE profile)"
fi

install_homebrew() {
  brew_shellenv
  if command_exists brew; then
    return 0
  fi
  log "Installing Homebrew"
  run /bin/bash -c 'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  brew_shellenv
  if [ "$DRY_RUN" != "1" ]; then
    command_exists brew || die "Homebrew installation did not put brew on PATH. Open a new Terminal and rerun."
  fi
}

install_command_line_tools() {
  if xcode-select -p >/dev/null 2>&1; then
    return 0
  fi
  if [ "$DRY_RUN" = "1" ]; then
    print_command xcode-select --install
    return 0
  fi
  xcode-select --install >/dev/null 2>&1 || true
  die "Apple Command Line Tools installation was opened. Finish it, then rerun this installer."
}

brew_install_formulae() {
  local packages="git gh $PYTHON_FORMULA uv colima docker docker-compose age jq"
  local package
  for package in $packages; do
    if [ "$DRY_RUN" = "1" ] || ! brew list --formula "$package" >/dev/null 2>&1; then
      log "Installing Homebrew formula: $package"
      run brew install "$package"
    fi
  done
}

install_1password() {
  [ "$WITH_1PASSWORD" = "1" ] || return 0
  local cask
  for cask in 1password 1password-cli; do
    if [ "$DRY_RUN" = "1" ] || ! brew list --cask "$cask" >/dev/null 2>&1; then
      log "Installing Homebrew cask: $cask"
      run brew install --cask "$cask"
    fi
  done
  if [ "$DRY_RUN" = "1" ]; then
    print_command op account list
    return 0
  fi
  command_exists op || die "1Password CLI was installed but the op command is unavailable."
  if ! op account list >/dev/null 2>&1; then
    die "Open and unlock 1Password, enable Settings > Developer > Integrate with 1Password CLI, then rerun."
  fi
  if [ -n "$OP_ACCOUNT" ]; then
    op signin --account "$OP_ACCOUNT" >/dev/null
  else
    op signin >/dev/null
  fi
  success "1Password CLI authorized through the desktop app"
}

github_login() {
  [ "$WITH_GITHUB_LOGIN" = "1" ] || return 0
  if [ "$DRY_RUN" = "1" ]; then
    print_command gh auth login --web --git-protocol https
    return 0
  fi
  if gh auth status >/dev/null 2>&1; then
    success "GitHub CLI is already authenticated"
  else
    gh auth login --web --git-protocol https
  fi
}

install_command_line_tools
install_homebrew
if [ "$DRY_RUN" = "1" ] && ! command_exists brew; then
  warn "Dry-run is continuing with an assumed Homebrew installation."
else
  brew_install_formulae
  install_1password
  github_login
fi

if [ "$DRY_RUN" = "1" ] && ! command_exists brew; then
  PYTHON_BIN="/opt/homebrew/opt/$PYTHON_FORMULA/bin/python3.12"
else
  PYTHON_BIN="$(brew --prefix "$PYTHON_FORMULA")/bin/python3.12"
fi

RUNTIME_ROOT="$HOME/Library/Application Support/GalileoGoldenDemo"
LOG_ROOT="$HOME/Library/Logs/GalileoGoldenDemo"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
APP_VENV="$REPO_DIR/.venv"
APP_REQUIREMENTS="$REPO_DIR/requirements-macos.lock"
if [ "$ARCH" != "arm64" ] || [ ! -f "$APP_REQUIREMENTS" ]; then
  APP_REQUIREMENTS="$REPO_DIR/requirements.txt"
fi
MLX_VENV="$RUNTIME_ROOT/mlx-venv"
RUNTIME_ENV="$RUNTIME_ROOT/postgres.env"
WEBUI_ENV="$RUNTIME_ROOT/open-webui.env"
STACK_ENV="$RUNTIME_ROOT/stack.env"

ensure_directory "$RUNTIME_ROOT"
ensure_directory "$LOG_ROOT"
ensure_directory "$LAUNCH_AGENTS"
ensure_directory "$REPO_DIR/.streamlit"
configure_docker_host

existing_port() {
  local container="$1"
  local container_port="$2"
  docker port "$container" "$container_port/tcp" 2>/dev/null | tail -n 1 | awk -F: '{print $NF}'
}

if [ "$POSTGRES_PORT" = "auto" ]; then
  if command_exists docker && docker_container_exists golden-demo-postgres; then
    POSTGRES_PORT="$(existing_port golden-demo-postgres 5432)"
  fi
  [ -n "$POSTGRES_PORT" ] && [ "$POSTGRES_PORT" != "auto" ] || POSTGRES_PORT="$(find_free_port 5432)"
fi
if [ "$OPEN_WEBUI_PORT" = "auto" ]; then
  if command_exists docker && docker_container_exists galileo-open-webui; then
    OPEN_WEBUI_PORT="$(existing_port galileo-open-webui 8080)"
  fi
  [ -n "$OPEN_WEBUI_PORT" ] && [ "$OPEN_WEBUI_PORT" != "auto" ] || OPEN_WEBUI_PORT="$(find_free_port 3000)"
fi
if [ "$APP_PORT" = "auto" ]; then
  if [ -f "$STACK_ENV" ]; then
    APP_PORT="$(awk -F= '$1 == "APP_PORT" {print $2}' "$STACK_ENV" | tail -n 1)"
  fi
fi
if [ "$APP_PORT" = "auto" ] || [ -z "$APP_PORT" ]; then
  APP_PORT="$(find_free_port 8501)"
fi
if [ "$MLX_PORT" = "auto" ]; then
  if [ -f "$STACK_ENV" ]; then
    MLX_PORT="$(awk -F= '$1 == "MLX_PORT" {print $2}' "$STACK_ENV" | tail -n 1)"
  fi
  [ -n "$MLX_PORT" ] && [ "$MLX_PORT" != "auto" ] || MLX_PORT="$(find_free_port 8080)"
fi

for numeric_port in "$POSTGRES_PORT" "$OPEN_WEBUI_PORT" "$APP_PORT" "$MLX_PORT"; do
  case "$numeric_port" in
    ''|*[!0-9]*) die "Invalid service port: $numeric_port" ;;
  esac
  [ "$numeric_port" -ge 1024 ] && [ "$numeric_port" -le 65535 ] || die "Port out of range: $numeric_port"
done

log "Ports: app=$APP_PORT, Open WebUI=$OPEN_WEBUI_PORT, PostgreSQL=$POSTGRES_PORT, MLX=$MLX_PORT"

if [ "$DRY_RUN" = "1" ]; then
  print_command uv venv --python "$PYTHON_BIN" "$APP_VENV"
  print_command uv pip install --python "$APP_VENV/bin/python" -r "$APP_REQUIREMENTS"
else
  if [ ! -x "$APP_VENV/bin/python" ]; then
    uv venv --python "$PYTHON_BIN" "$APP_VENV"
  fi
  uv pip install --python "$APP_VENV/bin/python" -r "$APP_REQUIREMENTS"
  uv pip check --python "$APP_VENV/bin/python"
fi

RESOLVED_CONFIG="$CONFIG_FILE"
PREVIOUS_OP_ITEM=""
if [ -f "$STACK_ENV" ]; then
  PREVIOUS_OP_ITEM="$(/bin/bash -c '. "$1"; printf "%s" "${OP_ITEM:-}"' _ "$STACK_ENV")"
fi
if [ -n "$OP_ITEM" ]; then
  if [ "$REFRESH_CONFIG" != "1" ] && [ -f "$REPO_DIR/.env" ] && [ "$PREVIOUS_OP_ITEM" = "$OP_ITEM" ]; then
    RESOLVED_CONFIG="$REPO_DIR/.env"
    log "Using cached 1Password configuration; pass --refresh-config to pull updates."
  else
    RESOLVED_CONFIG="$(mktemp -t galileo-op-item.XXXXXX)"
    TEMP_FILES="$TEMP_FILES $RESOLVED_CONFIG"
    OP_GET_ARGS=(item get "$OP_ITEM" --format json)
    [ -z "$OP_VAULT" ] || OP_GET_ARGS+=(--vault "$OP_VAULT")
    [ -z "$OP_ACCOUNT" ] || OP_GET_ARGS+=(--account "$OP_ACCOUNT")
    if [ "$DRY_RUN" = "1" ]; then
      print_command op "${OP_GET_ARGS[@]}"
      print_command "$PYTHON_BIN" "$SCRIPT_DIR/resolve_op_item.py" --output "$RESOLVED_CONFIG"
    else
      RESOLVER_ARGS=(--output "$RESOLVED_CONFIG")
      if [ "$REFRESH_CONFIG" = "1" ] && [ -f "$REPO_DIR/.env" ]; then
        RESOLVER_ARGS+=(--previous-dotenv "$REPO_DIR/.env")
      fi
      op "${OP_GET_ARGS[@]}" | "$APP_VENV/bin/python" \
        "$SCRIPT_DIR/resolve_op_item.py" "${RESOLVER_ARGS[@]}"
    fi
  fi
elif [ -n "$OP_TEMPLATE" ]; then
  [ -f "$OP_TEMPLATE" ] || die "1Password template not found: $OP_TEMPLATE"
  RESOLVED_CONFIG="$(mktemp -t galileo-secrets.XXXXXX)"
  TEMP_FILES="$TEMP_FILES $RESOLVED_CONFIG"
  run op inject --in-file "$OP_TEMPLATE" --out-file "$RESOLVED_CONFIG" --force
elif [ -n "$CONFIG_FILE" ]; then
  [ -f "$CONFIG_FILE" ] || die "Secrets file not found: $CONFIG_FILE"
elif [ -f "$REPO_DIR/.env" ]; then
  RESOLVED_CONFIG="$REPO_DIR/.env"
else
  RESOLVED_CONFIG="$(mktemp -t galileo-empty.XXXXXX)"
  TEMP_FILES="$TEMP_FILES $RESOLVED_CONFIG"
fi

RENDER_ARGS=(
  --input "$RESOLVED_CONFIG"
  --toml-output "$REPO_DIR/.streamlit/secrets.toml"
  --dotenv-output "$REPO_DIR/.env"
  --runtime-env-output "$RUNTIME_ENV"
  --webui-env-output "$WEBUI_ENV"
  --mlx-model "$MLX_MODEL"
  --mlx-port "$MLX_PORT"
  --postgres-port "$POSTGRES_PORT"
)
if [ "$OPENAI_ONLY" = "1" ]; then
  RENDER_ARGS+=(--openai-only)
fi
if [ "$DRY_RUN" = "1" ]; then
  print_command "$PYTHON_BIN" "$SCRIPT_DIR/render_secrets.py" "${RENDER_ARGS[@]}"
else
  "$APP_VENV/bin/python" "$SCRIPT_DIR/render_secrets.py" "${RENDER_ARGS[@]}"
fi

if [ "$DRY_RUN" != "1" ] && [ "$LOCAL_ONLY" != "1" ]; then
  "$APP_VENV/bin/python" - "$REPO_DIR/.env" <<'PY'
import sys
from pathlib import Path

required = {"GALILEO_API_KEY", "OPENAI_API_KEY"}
present = set()
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if "=" not in line or line.lstrip().startswith("#"):
        continue
    key, raw = line.split("=", 1)
    if key in required and raw.strip().strip("'\""):
        present.add(key)
missing = sorted(required - present)
if missing:
    raise SystemExit(
        "Missing cloud secrets: " + ", ".join(missing) +
        ". Supply --config-file/--op-template or use --local-only."
    )
PY
fi

if [ "$OPENAI_ONLY" != "1" ]; then
  if [ "$DRY_RUN" = "1" ]; then
    print_command uv venv --python "$PYTHON_BIN" "$MLX_VENV"
    print_command uv pip install --python "$MLX_VENV/bin/python" "mlx-lm==$MLX_LM_VERSION"
    print_command "$MLX_VENV/bin/python" -c "from huggingface_hub import snapshot_download; snapshot_download('$MLX_MODEL')"
  else
    if [ ! -x "$MLX_VENV/bin/python" ]; then
      uv venv --python "$PYTHON_BIN" "$MLX_VENV"
    fi
    uv pip install --python "$MLX_VENV/bin/python" "mlx-lm==$MLX_LM_VERSION"
    HF_HUB_DISABLE_XET=1 "$MLX_VENV/bin/python" - "$MLX_MODEL" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1])
PY
  fi
fi

start_docker_runtime() {
  configure_docker_host
  if docker info >/dev/null 2>&1; then
    success "Docker runtime is already available"
    return 0
  fi
  local colima_memory=4
  [ "$MEMORY_GIB" -lt 24 ] || colima_memory=6
  [ "$MEMORY_GIB" -lt 48 ] || colima_memory=8
  local colima_cpu=4
  [ "$CPU_COUNT" -lt "$colima_cpu" ] && colima_cpu="$CPU_COUNT"
  run colima start --cpu "$colima_cpu" --memory "$colima_memory" --disk 60
  if [ "$DRY_RUN" != "1" ]; then
    export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
    wait_for_command 30 docker info || die "Docker did not become ready after starting Colima."
  fi
}

ensure_postgres() {
  if docker_container_exists golden-demo-postgres; then
    if [ "$RECREATE_SERVICES" = "1" ]; then
      run docker rm -f golden-demo-postgres
    else
      if ! docker_container_running golden-demo-postgres; then
        run docker start golden-demo-postgres
      fi
      return 0
    fi
  fi
  run docker volume create golden-demo-postgres-data
  run docker run -d \
    --name golden-demo-postgres \
    --restart unless-stopped \
    --env-file "$RUNTIME_ENV" \
    -p "127.0.0.1:$POSTGRES_PORT:5432" \
    -v golden-demo-postgres-data:/var/lib/postgresql/data \
    "$POSTGRES_IMAGE"
}

ensure_open_webui() {
  [ "$SKIP_OPEN_WEBUI" != "1" ] || return 0
  if docker_container_exists galileo-open-webui; then
    if [ "$RECREATE_SERVICES" = "1" ] || [ "$REFRESH_CONFIG" = "1" ]; then
      run docker rm -f galileo-open-webui
    else
      if ! docker_container_running galileo-open-webui; then
        run docker start galileo-open-webui
      fi
      return 0
    fi
  fi
  run docker volume create galileo-open-webui-data
  run docker run -d \
    --name galileo-open-webui \
    --restart unless-stopped \
    --env-file "$WEBUI_ENV" \
    --add-host host.docker.internal:host-gateway \
    -p "127.0.0.1:$OPEN_WEBUI_PORT:8080" \
    -v galileo-open-webui-data:/app/backend/data \
    "$OPEN_WEBUI_IMAGE"
}

write_stack_env() {
  if [ "$DRY_RUN" = "1" ]; then
    log "Would write $STACK_ENV"
    return 0
  fi
  umask 077
  {
    printf 'REPO_DIR=%q\n' "$REPO_DIR"
    printf 'MLX_MODEL=%q\n' "$MLX_MODEL"
    printf 'MLX_PORT=%q\n' "$MLX_PORT"
    printf 'POSTGRES_PORT=%q\n' "$POSTGRES_PORT"
    printf 'OPEN_WEBUI_PORT=%q\n' "$OPEN_WEBUI_PORT"
    printf 'APP_PORT=%q\n' "$APP_PORT"
    printf 'OPENAI_ONLY=%q\n' "$OPENAI_ONLY"
    printf 'LOCAL_ONLY=%q\n' "$LOCAL_ONLY"
    printf 'SKIP_OPEN_WEBUI=%q\n' "$SKIP_OPEN_WEBUI"
    printf 'OP_ITEM=%q\n' "$OP_ITEM"
    printf 'OP_VAULT=%q\n' "$OP_VAULT"
    printf 'OP_ACCOUNT=%q\n' "$OP_ACCOUNT"
  } > "$STACK_ENV"
}

restart_launch_agent() {
  local domain="$1"
  local label="$2"
  local plist="$3"
  local attempt=0

  launchctl bootout "$domain/$label" >/dev/null 2>&1 || true
  while [ "$attempt" -lt 10 ]; do
    if launchctl bootstrap "$domain" "$plist" >/dev/null 2>&1; then
      launchctl kickstart -k "$domain/$label"
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done
  launchctl bootstrap "$domain" "$plist"
}

install_launch_agents() {
  local domain
  domain="$(launchctl_domain)"
  if [ "$OPENAI_ONLY" != "1" ]; then
    local mlx_plist="$LAUNCH_AGENTS/$MLX_LABEL.plist"
    run "$APP_VENV/bin/python" "$SCRIPT_DIR/write_launchd.py" \
      --output "$mlx_plist" \
      --label "$MLX_LABEL" \
      --cwd "$REPO_DIR" \
      --stdout "$LOG_ROOT/mlx.log" \
      --stderr "$LOG_ROOT/mlx.error.log" \
      --env HF_HUB_DISABLE_XET=1 \
      --env NO_PROXY=127.0.0.1,localhost \
      --start-interval 10 \
      -- "$MLX_VENV/bin/mlx_lm.server" \
      --model "$MLX_MODEL" --host 127.0.0.1 --port "$MLX_PORT" \
      --max-tokens 2048 --prompt-cache-size 1
    if [ "$DRY_RUN" != "1" ] && [ "$NO_START" != "1" ]; then
      restart_launch_agent "$domain" "$MLX_LABEL" "$mlx_plist"
    fi
  fi

  local app_plist="$LAUNCH_AGENTS/$STREAMLIT_LABEL.plist"
  run "$APP_VENV/bin/python" "$SCRIPT_DIR/write_launchd.py" \
    --output "$app_plist" \
    --label "$STREAMLIT_LABEL" \
    --cwd "$REPO_DIR" \
    --stdout "$LOG_ROOT/streamlit.log" \
    --stderr "$LOG_ROOT/streamlit.error.log" \
    --env NO_PROXY=127.0.0.1,localhost \
    --start-interval 10 \
    -- "$APP_VENV/bin/streamlit" run "$REPO_DIR/app.py" \
    --server.address 127.0.0.1 --server.port "$APP_PORT" --server.headless true
  if [ "$DRY_RUN" != "1" ] && [ "$NO_START" != "1" ]; then
    restart_launch_agent "$domain" "$STREAMLIT_LABEL" "$app_plist"
  fi
}

write_stack_env

if [ "$DRY_RUN" = "1" ] && ! command_exists docker; then
  print_command colima start --cpu 4 --memory 6 --disk 60
  print_command docker run -d --name golden-demo-postgres "$POSTGRES_IMAGE"
  [ "$SKIP_OPEN_WEBUI" = "1" ] || print_command docker run -d --name galileo-open-webui "$OPEN_WEBUI_IMAGE"
else
  start_docker_runtime
  ensure_postgres
  ensure_open_webui
  if [ "$DRY_RUN" != "1" ]; then
    wait_for_command 60 docker exec golden-demo-postgres pg_isready -U postgres -d vectordb || die "PostgreSQL did not become ready."
    docker exec golden-demo-postgres psql -U postgres -d vectordb -v ON_ERROR_STOP=1 \
      -c "CREATE EXTENSION IF NOT EXISTS vector;"
  fi
fi

install_launch_agents

if [ "$DRY_RUN" != "1" ] && [ "$SKIP_INDEXES" != "1" ]; then
  log "Building vector indexes for configured providers"
  for index_domain in $INDEX_DOMAINS; do
    log "Indexing domain: $index_domain"
    (cd "$REPO_DIR" && "$APP_VENV/bin/python" helpers/setup_vectordb.py "$index_domain")
  done
fi

if [ "$NO_START" = "1" ]; then
  if [ "$DRY_RUN" != "1" ]; then
    [ "$SKIP_OPEN_WEBUI" = "1" ] || docker stop galileo-open-webui >/dev/null 2>&1 || true
    docker stop golden-demo-postgres >/dev/null 2>&1 || true
  fi
  success "Installation complete; services were left stopped (--no-start)."
  printf 'Start later with: %s/scripts/macos/run.sh\n' "$REPO_DIR"
  exit 0
fi

if [ "$DRY_RUN" != "1" ]; then
  log "Waiting for managed HTTP services to become ready"
  wait_for_http "http://127.0.0.1:$APP_PORT/_stcore/health" 90 2 || \
    die "Galileo app did not become healthy within 3 minutes. See $LOG_ROOT/streamlit.error.log."
  if [ "$SKIP_OPEN_WEBUI" != "1" ]; then
    wait_for_http "http://127.0.0.1:$OPEN_WEBUI_PORT/health" 90 2 || \
      die "Open WebUI did not become healthy within 3 minutes. Check docker logs galileo-open-webui."
  fi
  if [ "$OPENAI_ONLY" != "1" ]; then
    wait_for_http "http://127.0.0.1:$MLX_PORT/v1/models" 90 2 || \
      die "MLX-LM did not become healthy within 3 minutes. See $LOG_ROOT/mlx.error.log."
  fi
  "$SCRIPT_DIR/doctor.sh" --no-fix
fi

success "Full stack installation complete"
printf 'Galileo app: http://127.0.0.1:%s\n' "$APP_PORT"
[ "$SKIP_OPEN_WEBUI" = "1" ] || printf 'Open WebUI:  http://127.0.0.1:%s\n' "$OPEN_WEBUI_PORT"
printf 'Run/repair:  %s/scripts/macos/run.sh\n' "$REPO_DIR"

#!/bin/bash

# Shared helpers for the macOS installer. Keep this file compatible with the
# system Bash shipped by macOS so bootstrap works before Homebrew is present.

set -Eeuo pipefail

# These constants are consumed by scripts that source this library.
# shellcheck disable=SC2034
readonly APP_SLUG="galileo-golden-demo"
# shellcheck disable=SC2034
readonly MLX_LABEL="com.galileo.golden-demo.mlx"
# shellcheck disable=SC2034
readonly STREAMLIT_LABEL="com.galileo.golden-demo.streamlit"

log() {
  printf '\033[1;34m[galileo]\033[0m %s\n' "$*"
}

success() {
  printf '\033[1;32m[galileo]\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33m[galileo]\033[0m %s\n' "$*" >&2
}

die() {
  printf '\033[1;31m[galileo] ERROR:\033[0m %s\n' "$*" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

shell_quote() {
  printf '%q' "$1"
}

print_command() {
  local arg
  printf '  +'
  for arg in "$@"; do
    printf ' '
    shell_quote "$arg"
  done
  printf '\n'
}

run() {
  if [ "${DRY_RUN:-0}" = "1" ]; then
    print_command "$@"
    return 0
  fi
  "$@"
}

require_macos() {
  [ "$(uname -s)" = "Darwin" ] || die "This installer supports macOS only."
}

machine_arch() {
  uname -m
}

memory_gib() {
  local bytes
  bytes="$(sysctl -n hw.memsize 2>/dev/null || printf '0')"
  printf '%s\n' "$((bytes / 1024 / 1024 / 1024))"
}

free_disk_gib() {
  local path="${1:-.}"
  df -Pk "$path" | awk 'NR == 2 {printf "%d\n", $4 / 1024 / 1024}'
}

model_for_hardware() {
  local memory="$1"
  local profile="${2:-balanced}"

  if [ "$memory" -lt 20 ]; then
    printf '%s\n' "mlx-community/gemma-4-e4b-it-4bit"
  elif [ "$profile" = "quality" ] && [ "$memory" -ge 48 ]; then
    printf '%s\n' "mlx-community/gemma-4-31b-it-4bit"
  else
    # Gemma 4 26B A4B activates only about 3.8B parameters per token and is the
    # most reliable quality/speed default for an executive workstation.
    printf '%s\n' "mlx-community/gemma-4-26b-a4b-it-4bit"
  fi
}

minimum_disk_gib_for_model() {
  case "$1" in
    *31b*) printf '%s\n' 45 ;;
    *26b*) printf '%s\n' 35 ;;
    *) printf '%s\n' 20 ;;
  esac
}

port_is_free() {
  local port="$1"
  ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

find_free_port() {
  local port="$1"
  local limit="${2:-100}"
  local checked=0
  while [ "$checked" -lt "$limit" ]; do
    if port_is_free "$port"; then
      printf '%s\n' "$port"
      return 0
    fi
    port=$((port + 1))
    checked=$((checked + 1))
  done
  return 1
}

wait_for_http() {
  local url="$1"
  local attempts="${2:-60}"
  local delay="${3:-2}"
  local count=0
  while [ "$count" -lt "$attempts" ]; do
    if curl --silent --show-error --fail --max-time 5 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
    count=$((count + 1))
  done
  return 1
}

wait_for_command() {
  local attempts="$1"
  shift
  local count=0
  while [ "$count" -lt "$attempts" ]; do
    if "$@" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    count=$((count + 1))
  done
  return 1
}

ensure_directory() {
  local directory="$1"
  if [ ! -d "$directory" ]; then
    run mkdir -p "$directory"
  fi
}

ensure_mode_600() {
  local file="$1"
  [ -e "$file" ] && run chmod 600 "$file"
}

brew_shellenv() {
  if command_exists brew; then
    return 0
  fi
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

configure_docker_host() {
  if command_exists docker && docker info >/dev/null 2>&1; then
    return 0
  fi
  local colima_socket="$HOME/.colima/default/docker.sock"
  if command_exists colima && colima status >/dev/null 2>&1 && [ -S "$colima_socket" ]; then
    export DOCKER_HOST="unix://$colima_socket"
  fi
}

launchctl_domain() {
  printf 'gui/%s\n' "$(id -u)"
}

plist_escape() {
  printf '%s' "$1" | sed \
    -e 's/&/\&amp;/g' \
    -e 's/</\&lt;/g' \
    -e 's/>/\&gt;/g' \
    -e 's/"/\&quot;/g' \
    -e "s/'/\&apos;/g"
}

docker_container_exists() {
  docker container inspect "$1" >/dev/null 2>&1
}

docker_container_running() {
  [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null || true)" = "true" ]
}

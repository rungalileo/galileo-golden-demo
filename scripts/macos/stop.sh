#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

STOP_COLIMA=0
if [ "${1:-}" = "--colima" ]; then
  STOP_COLIMA=1
  shift
fi
[ "$#" -eq 0 ] || die "Usage: $0 [--colima]"

DOMAIN="$(launchctl_domain)"
for label in "$STREAMLIT_LABEL" "$MLX_LABEL"; do
  launchctl bootout "$DOMAIN/$label" >/dev/null 2>&1 || true
done

configure_docker_host
if command_exists docker && docker info >/dev/null 2>&1; then
  for container in galileo-open-webui golden-demo-postgres; do
    if docker_container_running "$container"; then
      docker stop "$container" >/dev/null
    fi
  done
fi

if [ "$STOP_COLIMA" = "1" ] && command_exists colima; then
  colima stop
fi

success "Galileo services stopped; volumes and configuration were preserved"

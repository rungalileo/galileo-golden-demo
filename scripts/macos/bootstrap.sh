#!/bin/bash

# Standalone entrypoint for a new Mac. Send this script alongside the encrypted
# secrets note, or place it in a trusted internal download location.

set -Eeuo pipefail

REPO_URL=""
REPO_DIR="$HOME/Developer/galileo-golden-demo"
BRANCH="main"
WITH_GITHUB_LOGIN=0
INSTALL_ARGS=()

usage() {
  cat <<'USAGE'
Usage: bootstrap.sh --repo-url URL [options] [-- installer-options]

  --repo-url URL       GitHub repository URL or OWNER/REPO (required)
  --repo-dir PATH      Clone destination (default: ~/Developer/galileo-golden-demo)
  --branch NAME        Branch to check out (default: main)
  --github-login       Opt in to GitHub browser login before cloning
  --                    Pass remaining options to scripts/macos/install.sh

Example:
  ./bootstrap.sh --repo-url COMPANY/galileo-golden-demo --github-login -- \
    --config-file ~/Downloads/executive-secrets.env
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo-url) [ "$#" -ge 2 ] || die "--repo-url needs a value"; REPO_URL="$2"; shift 2 ;;
    --repo-dir) [ "$#" -ge 2 ] || die "--repo-dir needs a value"; REPO_DIR="$2"; shift 2 ;;
    --branch) [ "$#" -ge 2 ] || die "--branch needs a value"; BRANCH="$2"; shift 2 ;;
    --github-login) WITH_GITHUB_LOGIN=1; INSTALL_ARGS+=(--github-login); shift ;;
    --) shift; while [ "$#" -gt 0 ]; do INSTALL_ARGS+=("$1"); shift; done ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown bootstrap option: $1 (installer options belong after --)" ;;
  esac
done

[ -n "$REPO_URL" ] || die "--repo-url is required"
[ "$(uname -s)" = "Darwin" ] || die "This bootstrap supports macOS only."

if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install >/dev/null 2>&1 || true
  die "Finish installing Apple Command Line Tools, then rerun bootstrap.sh."
fi

if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c 'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
fi
if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -x /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi
command -v brew >/dev/null 2>&1 || die "Homebrew is unavailable after installation."

brew list --formula git >/dev/null 2>&1 || brew install git
brew list --formula gh >/dev/null 2>&1 || brew install gh

if [ "$WITH_GITHUB_LOGIN" = "1" ]; then
  gh auth status >/dev/null 2>&1 || gh auth login --web --git-protocol https
  gh auth setup-git
fi

if [ -e "$REPO_DIR" ] && [ ! -d "$REPO_DIR/.git" ]; then
  die "$REPO_DIR already exists but is not a Git repository. Choose another --repo-dir."
fi

if [ ! -d "$REPO_DIR/.git" ]; then
  mkdir -p "$(dirname "$REPO_DIR")"
  if [ "$WITH_GITHUB_LOGIN" = "1" ]; then
    gh repo clone "$REPO_URL" "$REPO_DIR" -- --branch "$BRANCH"
  else
    git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
  fi
else
  printf 'Using existing repository: %s\n' "$REPO_DIR"
  current_branch="$(git -C "$REPO_DIR" branch --show-current)"
  [ "$current_branch" = "$BRANCH" ] || die \
    "$REPO_DIR is on branch $current_branch, expected $BRANCH. Switch it explicitly, then rerun."
fi

exec "$REPO_DIR/scripts/macos/install.sh" "${INSTALL_ARGS[@]}"

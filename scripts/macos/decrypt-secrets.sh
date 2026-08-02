#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

INPUT=""
OUTPUT=""
IDENTITY=""
PASSPHRASE=0
FORCE=0

usage() {
  cat <<'USAGE'
Usage: decrypt-secrets.sh --input FILE.age --output FILE.env [options]

  --identity PATH   age identity file (omit for SSH agent/default identities)
  --passphrase      Interactively decrypt a passphrase-protected file
  --force           Replace an existing plaintext output
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --input) [ "$#" -ge 2 ] || die "--input needs a path"; INPUT="$2"; shift 2 ;;
    --output) [ "$#" -ge 2 ] || die "--output needs a path"; OUTPUT="$2"; shift 2 ;;
    --identity) [ "$#" -ge 2 ] || die "--identity needs a path"; IDENTITY="$2"; shift 2 ;;
    --passphrase) PASSPHRASE=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

[ -n "$INPUT" ] && [ -n "$OUTPUT" ] || die "--input and --output are required."
[ -f "$INPUT" ] || die "Encrypted file not found: $INPUT"
[ ! -e "$OUTPUT" ] || [ "$FORCE" = "1" ] || die "$OUTPUT exists; use --force to replace it."
[ "$PASSPHRASE" != "1" ] || [ -z "$IDENTITY" ] || die "Use --identity or --passphrase, not both."
command_exists age || die "age is not installed. Run: brew install age"

ensure_directory "$(dirname "$OUTPUT")"
TEMP_OUTPUT="$(mktemp "$(dirname "$OUTPUT")/.decrypted-secrets.XXXXXX")"
trap 'rm -f "$TEMP_OUTPUT"' EXIT

if [ -n "$IDENTITY" ]; then
  age -d -i "$IDENTITY" "$INPUT" > "$TEMP_OUTPUT"
else
  # Passphrase files prompt automatically. Recipient-encrypted files use the
  # default age/SSH agent identity discovery when available.
  age -d "$INPUT" > "$TEMP_OUTPUT"
fi

chmod 600 "$TEMP_OUTPUT"
mv -f "$TEMP_OUTPUT" "$OUTPUT"
trap - EXIT
success "Decrypted secrets written to $OUTPUT with mode 0600"
